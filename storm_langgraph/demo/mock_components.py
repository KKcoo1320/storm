from __future__ import annotations

from dataclasses import dataclass

from storm_langgraph.types import Information


@dataclass
class MockPersonaGenerator:
    def generate_personas(self, topic: str, max_num_persona: int) -> list[str]:
        personas = [
            f"Background analyst: Focus on the basic facts of {topic}.",
            f"Timeline analyst: Focus on key milestones and evolution of {topic}.",
            f"Impact analyst: Focus on applications, risks, and influence of {topic}.",
        ]
        return personas[:max_num_persona]


@dataclass
class MockQuestionAsker:
    def ask(self, topic: str, persona: str, dialogue_history: list[dict]) -> str:
        turn = len(dialogue_history)
        prompts = [
            f"What are the core ideas behind {topic}?",
            f"What are the important milestones or representative systems in {topic}?",
            f"What are the main strengths, limits, and practical impacts of {topic}?",
        ]
        return prompts[turn] if turn < len(prompts) else "Thank you so much for your help!"


@dataclass
class MockQueryGenerator:
    def generate_queries(self, topic: str, question: str, max_queries: int) -> list[str]:
        seeds = [
            f"{topic} overview",
            f"{topic} milestones",
            f"{topic} applications limitations",
        ]
        return seeds[:max_queries]


class MockRetriever:
    def __init__(self):
        self.corpus = [
            Information(
                url="doc://storm-overview",
                title="STORM Overview",
                description="Overview of STORM style research-and-writing pipelines.",
                snippets=[
                    "STORM-style systems separate research, outline generation, section writing, and polishing into distinct stages.",
                    "The research stage focuses on collecting grounded evidence before long-form generation begins.",
                ],
            ),
            Information(
                url="doc://storm-research",
                title="Research Loop",
                description="Multi-perspective research loop.",
                snippets=[
                    "A persona-guided conversation can expand topic coverage by encouraging different lines of questioning.",
                    "Iterative retrieval and answer synthesis create a richer information table than one-shot search.",
                ],
            ),
            Information(
                url="doc://storm-writing",
                title="Section Writing",
                description="Section-wise article generation.",
                snippets=[
                    "Section-specific retrieval keeps each section focused and reduces repetition in long-form writing.",
                    "A final polishing stage can add a lead section and optionally remove duplicated content.",
                ],
            ),
        ]

    def retrieve(self, queries: list[str], exclude_urls: list[str] | None = None) -> list[Information]:
        exclude_urls = set(exclude_urls or [])
        results = []
        for info in self.corpus:
            if info.url in exclude_urls:
                continue
            results.append(info)
        return results


@dataclass
class MockAnswerSynthesizer:
    def answer(self, topic: str, question: str, gathered_info: list[Information]) -> str:
        evidence = []
        for info in gathered_info[:2]:
            evidence.extend(info.snippets[:1])
        joined = " ".join(evidence)
        return f"For '{question}', the collected evidence suggests: {joined}".strip()


@dataclass
class MockOutlineGenerator:
    def generate_direct_outline(self, topic: str) -> str:
        return "\n".join(
            [
                "# Background",
                "# Research Workflow",
                "# Applications and Limits",
            ]
        )

    def refine_outline(self, topic: str, conversation_text: str, draft_outline: str) -> str:
        return "\n".join(
            [
                "# Background",
                "## Core Ideas",
                "# Research Workflow",
                "## Persona-guided Research",
                "## Evidence Collection",
                "# Applications and Limits",
                "## Strengths",
                "## Limitations",
            ]
        )


@dataclass
class MockSectionWriter:
    def write_section(
        self,
        topic: str,
        section_name: str,
        section_outline: str,
        collected_info: list[Information],
    ) -> str:
        sentences = []
        citation_idx = 1
        for info in collected_info[:2]:
            for snippet in info.snippets[:1]:
                sentences.append(f"{snippet}[{citation_idx}]")
                citation_idx += 1
        body = " ".join(sentences) or f"This section summarizes {section_name.lower()} for {topic}."
        return f"# {section_name}\n{body}"


@dataclass
class MockArticlePolisher:
    def write_lead(self, topic: str, draft_article: str) -> str:
        return (
            f"{topic} can be understood as a staged research-and-writing workflow "
            f"that benefits from evidence gathering, outline control, and section-wise synthesis."
        )

    def deduplicate(self, draft_article: str) -> str:
        seen = set()
        kept = []
        for line in draft_article.splitlines():
            normalized = line.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                kept.append(line)
        return "\n".join(kept)

