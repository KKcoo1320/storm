from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI

from storm_langgraph.text_splitter import split_text
from storm_langgraph.types import Information


def _normalize_topic_name(topic: str) -> str:
    return topic.replace(" ", "_").replace("/", "_")


def _extract_json_payload(text: str) -> str:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        return match.group(1)
    return text


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output


def _clean_heading_title(line: str) -> str:
    return re.sub(r"^\d+(\.\d+)*\s*", "", line.lstrip("#").strip()).strip()


def _extract_toc_from_article_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line.startswith("#"):
            continue
        title = _clean_heading_title(line)
        if title.lower() in {
            "references",
            "external links",
            "see also",
            "notes",
            "bibliography",
            "further reading",
            "summary",
            "appendix",
            "appendices",
        }:
            break
        level = max(1, len(line) - len(line.lstrip("#")))
        lines.append(f'{"  " * (level - 1)}{title}')
    return "\n".join(lines).strip()


def _load_topic_titles(topic_list_path: Path, current_topic: str) -> list[str]:
    if not topic_list_path.exists():
        return []
    try:
        rows = []
        for line in topic_list_path.read_text(encoding="utf-8").splitlines()[1:]:
            if not line.strip():
                continue
            topic = line.split(",", 1)[0].strip().strip('"')
            if topic and topic != current_topic:
                rows.append(topic)
        return rows
    except Exception:
        return []


class OpenAICompatLLM:
    def __init__(self, model: str | None = None):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        base_url = os.environ.get("OPENAI_API_BASE") or os.environ.get("AZURE_API_BASE")
        self.model = model or os.environ.get("STORM_LANGGRAPH_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""


@dataclass
class LLMPersonaGenerator:
    llm: OpenAICompatLLM

    def _collect_related_topic_examples(self, topic: str, max_related_topics: int = 5) -> str:
        freshwiki_dir = Path(
            os.environ.get(
                "STORM_LANGGRAPH_FRESHWIKI_DIR",
                "/Users/wangbozhi/Documents/New project/storm_upstream_naacl/FreshWiki/txt",
            )
        )
        topic_list_path = Path(
            os.environ.get(
                "STORM_LANGGRAPH_FRESHWIKI_TOPIC_LIST",
                str(freshwiki_dir.parent / "topic_list.csv"),
            )
        )
        candidates = _load_topic_titles(topic_list_path, topic)
        if not candidates:
            return "N/A"

        candidate_block = "\n".join(f"- {candidate}" for candidate in candidates[:100])
        text = self.llm.complete(
            "You choose closely related Wikipedia topics for article planning.",
            (
                f"Topic: {topic}\n"
                "Pick up to 5 topics from the candidate list that are most useful as structural inspiration.\n"
                "Prefer topics with similar type, scope, or article structure.\n"
                "Return JSON only with schema {\"related_topics\": [string, ...]}.\n"
                f"Candidate topics:\n{candidate_block}"
            ),
            temperature=0.2,
            max_tokens=220,
        )
        try:
            payload = json.loads(_extract_json_payload(text))
            related_topics = payload.get("related_topics", [])
        except Exception:
            related_topics = []

        examples: list[str] = []
        for related_topic in related_topics[:max_related_topics]:
            topic_file = freshwiki_dir / f"{_normalize_topic_name(related_topic)}.txt"
            if not topic_file.exists():
                continue
            toc = _extract_toc_from_article_text(topic_file.read_text(encoding="utf-8"))
            if toc:
                examples.append(f"Title: {related_topic}\nTable of Contents:\n{toc}")
        return "\n----------\n".join(examples) if examples else "N/A"

    def generate_personas(self, topic: str, max_num_persona: int) -> list[str]:
        examples = self._collect_related_topic_examples(topic)
        text = self.llm.complete(
            "You create research personas for a Wikipedia article planning workflow.",
            (
                f"Topic: {topic}\n"
                f"Wiki page outlines of related topics for inspiration:\n{examples}\n\n"
                f"Return JSON only with schema {{\"personas\": [string, ...]}}.\n"
                f"Generate at most {max_num_persona} personas.\n"
                "Each persona should focus on a distinct aspect that could become a substantial section or subsection in the final article.\n"
                "Prefer section-planning personas such as background and origins, chronology and turning points, products or works, people and organizations, controversies and legal issues, impact and legacy, or technical and operational details when appropriate.\n"
                "Avoid generic personas that overlap heavily with each other.\n"
                "Each persona should be a short instruction sentence starting with an action verb, for example: Cover the bank run and regulatory response."
            ),
            temperature=0.4,
            max_tokens=500,
        )
        try:
            payload = json.loads(_extract_json_payload(text))
            personas = payload.get("personas", [])
            return _dedupe_keep_order(
                [p.strip() for p in personas if isinstance(p, str) and p.strip()]
            )[:max_num_persona]
        except Exception:
            lines = [line.strip("- *\n ") for line in text.splitlines() if line.strip()]
            return _dedupe_keep_order(lines)[:max_num_persona]


@dataclass
class LLMQuestionAsker:
    llm: OpenAICompatLLM

    def ask(self, topic: str, persona: str, dialogue_history: list[dict]) -> str:
        history = json.dumps(dialogue_history, ensure_ascii=False)
        return self.llm.complete(
            "You are an experienced Wikipedia writer doing grounded research. Ask exactly one next question that covers a missing aspect of the topic. If the current persona has already covered its key angles, say exactly: Thank you so much for your help!",
            (
                f"Topic: {topic}\n"
                f"Persona: {persona}\n"
                f"Recent dialogue history: {history}\n"
                "Rules:\n"
                "- Ask one question at a time.\n"
                "- Do not repeat earlier questions.\n"
                "- Prefer specific, section-worthy questions over generic overview questions.\n"
                "- Prioritize missing names, events, dates, organizations, products, controversies, and turning points.\n"
                "- Ask questions that could plausibly become subsection titles later.\n"
                "- Use the dialogue history to decide what is still missing.\n"
                "Return only one question sentence or the exact termination phrase."
            ),
            temperature=0.5,
            max_tokens=180,
        ).strip()


@dataclass
class LLMQueryGenerator:
    llm: OpenAICompatLLM

    def _fallback_queries(self, topic: str, question: str, max_queries: int) -> list[str]:
        stripped_question = question.strip().rstrip("?")
        base_queries = [
            f"{topic} {stripped_question}",
            stripped_question,
        ]
        keywords = _dedupe_keep_order(re.findall(r"[A-Za-z0-9][A-Za-z0-9'&.-]*", stripped_question))
        if keywords:
            focus = " ".join(keywords[:6])
            base_queries.extend(
                [
                    f"{topic} {focus} timeline",
                    f"{topic} {focus} key people organizations",
                    f"{topic} {focus} impact controversy",
                ]
            )
        return _dedupe_keep_order(base_queries)[:max_queries]

    def generate_queries(self, topic: str, question: str, max_queries: int) -> list[str]:
        text = self.llm.complete(
            "You decompose a research question into high-recall search queries.",
            (
                f"Topic: {topic}\n"
                f"Question: {question}\n"
                f"Return JSON only with schema {{\"queries\": [string, ...]}} and at most {max_queries} queries.\n"
                "Use diverse phrasings that capture names, aliases, events, timelines, organizations, places, products, and topic-specific terminology.\n"
                "Prefer a mix of:\n"
                "- one broad factual query\n"
                "- one entity-focused query\n"
                "- one timeline or chronology query\n"
                "- one controversy, impact, or legacy query when relevant\n"
                "- one query that uses alternate wording or aliases"
            ),
            temperature=0.2,
            max_tokens=220,
        )
        try:
            payload = json.loads(_extract_json_payload(text))
            queries = payload.get("queries", [])
            normalized = _dedupe_keep_order(
                [q.strip() for q in queries if isinstance(q, str) and q.strip()]
            )
            if len(normalized) < max_queries:
                normalized.extend(
                    query
                    for query in self._fallback_queries(topic, question, max_queries)
                    if query.lower() not in {item.lower() for item in normalized}
                )
            return normalized[:max_queries]
        except Exception:
            return self._fallback_queries(topic, question, max_queries)


class YouRetriever:
    def __init__(self, k: int = 3):
        api_key = os.environ.get("YDC_API_KEY")
        if not api_key:
            raise RuntimeError("YDC_API_KEY is not set.")
        self.api_key = api_key
        self.k = k

    def retrieve(self, queries: list[str], exclude_urls: list[str] | None = None) -> list[Information]:
        exclude_urls = set(exclude_urls or [])
        seen_urls: set[str] = set()
        results: list[Information] = []
        headers = {"X-API-Key": self.api_key}

        for query in queries:
            items: list[dict[str, Any]] = []

            try:
                response = requests.get(
                    "https://api.ydc-index.io/v1/search",
                    headers=headers,
                    params={"query": query, "count": self.k},
                    timeout=20,
                )
                payload = response.json()
                items = (payload.get("results") or {}).get("web") or []
            except Exception:
                items = []

            if not items:
                try:
                    response = requests.get(
                        "https://api.ydc-index.io/search",
                        headers=headers,
                        params={"query": query, "num_web_results": self.k},
                        timeout=20,
                    )
                    payload = response.json()
                    items = payload.get("hits") or []
                except Exception:
                    items = []

            for item in items:
                url = item.get("url")
                if not url or url in exclude_urls or url in seen_urls:
                    continue
                seen_urls.add(url)
                snippets = list(item.get("snippets") or [])
                if not snippets and item.get("description"):
                    snippets = [item["description"]]
                results.append(
                    Information(
                        url=url,
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        snippets=snippets,
                        meta={},
                    )
                )

        return [
            item for item in results[: self.k * max(1, len(queries))]
        ]


class DuckDuckGoRetriever:
    def __init__(self, k: int = 3):
        from knowledge_storm.rm import DuckDuckGoSearchRM

        self.rm = DuckDuckGoSearchRM(k=k, safe_search="On", region="us-en")

    def retrieve(self, queries: list[str], exclude_urls: list[str] | None = None) -> list[Information]:
        results = self.rm.forward(queries, exclude_urls=exclude_urls or [])
        return [
            Information(
                url=item["url"],
                title=item.get("title", ""),
                description=item.get("description", ""),
                snippets=list(item.get("snippets", [])),
                meta={},
            )
            for item in results
        ]


class LocalTopicFileRetriever:
    def __init__(
        self,
        *,
        topic: str,
        corpus_dir: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        k: int = 3,
    ):
        self.topic = topic
        self.corpus_dir = Path(corpus_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.k = k

    def _topic_file(self) -> Path:
        topic_name = _normalize_topic_name(self.topic)
        return self.corpus_dir / f"{topic_name}.txt"

    def retrieve(self, queries: list[str], exclude_urls: list[str] | None = None) -> list[Information]:
        source_file = self._topic_file()
        if not source_file.exists():
            return []

        text = source_file.read_text(encoding="utf-8")
        chunks = split_text(text, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        if not chunks:
            return []

        normalized_queries = [query.strip() for query in queries if query.strip()]
        query_tokens = [re.findall(r"\w+", query.lower()) for query in normalized_queries]
        query_bigrams = [
            {" ".join(tokens[i : i + 2]) for i in range(len(tokens) - 1)}
            for tokens in query_tokens
        ]

        def score(chunk: str) -> float:
            chunk_lower = chunk.lower()
            chunk_tokens = re.findall(r"\w+", chunk_lower)
            chunk_token_set = set(chunk_tokens)
            heading_lines = [line.strip("# ").strip() for line in chunk.splitlines() if line.strip().startswith("#")]
            heading_text = " ".join(heading_lines).lower()
            score_value = 0.0
            for query, tokens, bigrams in zip(normalized_queries, query_tokens, query_bigrams):
                phrase = query.lower().strip()
                if phrase and phrase in chunk_lower:
                    score_value += 4.0
                if tokens:
                    overlap = sum(1 for token in tokens if token in chunk_token_set)
                    score_value += 2.0 * overlap / max(1, len(tokens))
                    title_overlap = sum(1 for token in tokens if token in heading_text)
                    score_value += 1.5 * title_overlap / max(1, len(tokens))
                if bigrams:
                    bigram_overlap = sum(1 for bigram in bigrams if bigram in chunk_lower)
                    score_value += 2.0 * bigram_overlap / max(1, len(bigrams))
            if chunk.strip().startswith("#"):
                score_value += 0.5
            return score_value

        ranked_chunks = sorted(chunks, key=score, reverse=True)
        topic_name = _normalize_topic_name(self.topic)
        return [
            Information(
                url=f"file://{source_file}",
                title=topic_name,
                description=f"Local corpus snippet from {source_file.name}",
                snippets=[chunk],
                meta={"source": "local_topic_file", "query_count": len(queries)},
            )
            for chunk in ranked_chunks[: self.k]
        ]


@dataclass
class LLMAnswerSynthesizer:
    llm: OpenAICompatLLM

    def answer(self, topic: str, question: str, gathered_info: list[Information]) -> str:
        evidence_lines: list[str] = []
        for idx, info in enumerate(gathered_info[:5], start=1):
            snippets = " ".join(info.snippets[:2])
            evidence_lines.append(f"[{idx}] {info.title} | {info.url}\n{snippets}")
        evidence = "\n\n".join(evidence_lines)
        return self.llm.complete(
            "You are a grounded topic expert. Answer only from the provided evidence. Be informative, specific, and avoid hallucination.",
            (
                f"Topic: {topic}\n"
                f"Question: {question}\n"
                f"Evidence:\n{evidence}\n\n"
                "Write a concise but information-dense answer that preserves concrete entities, dates, names, organizations, products, and events when supported by the evidence.\n"
                "When possible, mention the most important proper nouns explicitly rather than replacing them with vague descriptions."
            ),
            temperature=0.2,
            max_tokens=420,
        ).strip()


@dataclass
class LLMOutlineGenerator:
    llm: OpenAICompatLLM

    def generate_direct_outline(self, topic: str) -> str:
        return self.llm.complete(
            "You write Wikipedia-style outlines. Return markdown headings only.",
            (
                f"Topic: {topic}\n"
                "Write a strong draft outline using markdown headings only.\n"
                "Requirements:\n"
                "- Use #, ##, and ### headings.\n"
                "- Do not number headings.\n"
                "- Do not include the topic name itself as a heading.\n"
                "- Do not include References, External links, See also, Conclusion, or Summary.\n"
                "- Prefer informative, specific section titles over generic placeholders.\n"
                "- Favor canonical Wikipedia-like coverage when appropriate: background, chronology, people and organizations, products or works, controversies, impact, and legacy.\n"
                "- Avoid flat outlines made only of broad headings like History, Impact, and Reception unless they are expanded with specific subsections."
            ),
            temperature=0.3,
            max_tokens=700,
        ).strip()

    def refine_outline(self, topic: str, conversation_text: str, draft_outline: str) -> str:
        return self.llm.complete(
            "You refine a Wikipedia outline using grounded research notes. Return markdown headings only.",
            (
                f"Topic: {topic}\n"
                f"Draft outline:\n{draft_outline}\n\n"
                f"Research conversation:\n{conversation_text}\n\n"
                "Produce a better outline with clear hierarchy.\n"
                "Requirements:\n"
                "- Add missing topic-specific headings supported by the research conversation.\n"
                "- Preserve strong high-level structure from the draft, but expand with more specific subsections and subsubsections.\n"
                "- Surface important named entities, events, organizations, places, and timelines in headings when they are section-worthy.\n"
                "- Prefer headings that name concrete incidents, people, products, lawsuits, investigations, launches, disasters, mergers, or other turning points when supported.\n"
                "- Replace vague headings with more specific ones when the research conversation supports that specificity.\n"
                "- Use the candidate-entity block aggressively: if an entity, organization, regulator, product, lawsuit, acquisition, or incident can support a heading, prefer the entity-bearing title.\n"
                "- Prefer headings like 'Acquisition by First Citizens BancShares' over vague headings like 'Acquisition' when the evidence supports the more specific title.\n"
                "- Prefer headings like 'Federal Reserve Review Led by Michael Barr' over vague headings like 'Regulatory Response' when the evidence supports the more specific title.\n"
                "- If a heading can include a concrete organization, person, place, product, or event name without becoming awkward, include it.\n"
                "- Avoid generic headings such as Overview, Introduction, Impact, Background, Response, or Legacy when a more entity-specific alternative is supported.\n"
                "- Do not number headings.\n"
                "- Do not include References, External links, See also, Conclusion, or Summary.\n"
                "- Output headings only."
            ),
            temperature=0.3,
            max_tokens=1100,
        ).strip()


@dataclass
class LLMSectionWriter:
    llm: OpenAICompatLLM

    def write_section(
        self,
        topic: str,
        section_name: str,
        section_outline: str,
        collected_info: list[Information],
    ) -> str:
        info_chunks: list[str] = []
        for idx, info in enumerate(collected_info[:6], start=1):
            info_chunks.append(f"[{idx}] {info.title}\n" + "\n".join(info.snippets[:2]))
        evidence = "\n\n".join(info_chunks)
        return self.llm.complete(
            "You write one Wikipedia-style section with inline citations like [1][2]. Start with a markdown heading for the section and do not write other sections.",
            (
                f"Topic: {topic}\n"
                f"Section: {section_name}\n"
                f"Section outline:\n{section_outline}\n\n"
                f"Evidence:\n{evidence}"
            ),
            temperature=0.3,
            max_tokens=900,
        ).strip()


@dataclass
class LLMArticlePolisher:
    llm: OpenAICompatLLM

    def write_lead(self, topic: str, draft_article: str) -> str:
        return self.llm.complete(
            "You write a short encyclopedia lead summarizing the article.",
            f"Topic: {topic}\nDraft article:\n{draft_article}\n\nWrite a 2-4 sentence lead.",
            temperature=0.2,
            max_tokens=220,
        ).strip()

    def deduplicate(self, draft_article: str) -> str:
        return self.llm.complete(
            "You remove repeated content while preserving structure and citations.",
            f"Article:\n{draft_article}\n\nReturn the cleaned article only.",
            temperature=0.0,
            max_tokens=1200,
        ).strip()
