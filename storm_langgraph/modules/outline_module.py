from __future__ import annotations

import re

from ..config import StormGraphConfig
from ..interfaces import OutlineGenerator
from ..types import StormArticle


def _clean_up_outline(outline: str, topic: str = "") -> str:
    output_lines: list[str] = []
    current_level = 0

    for line in (outline or "").splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if topic and stripped_line.lower() == f"# {topic.lower()}":
            output_lines = []
            continue

        if stripped_line.startswith("#"):
            current_level = stripped_line.count("#")
            title = re.sub(r"^\d+(\.\d+)*\s*", "", stripped_line.lstrip("#").strip()).strip()
            output_lines.append("#" * current_level + " " + title)
        elif stripped_line.startswith("-"):
            title = re.sub(r"^\d+(\.\d+)*\s*", "", stripped_line[1:].strip()).strip()
            output_lines.append("#" * (current_level + 1) + " " + title)

    outline = "\n".join(output_lines)
    outline = re.sub(r"#[#]?\s*See also.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"#[#]?\s*Notes.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"#[#]?\s*References.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"#[#]?\s*External links.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"#[#]?\s*Bibliography.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"#[#]?\s*Further reading.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"#[#]?\s*Summary.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"#[#]?\s*Appendix.*?(?=##|$)", "", outline, flags=re.IGNORECASE | re.DOTALL)
    outline = re.sub(r"\[[^\]]*\]", "", outline)
    return "\n".join(line for line in outline.splitlines() if line.strip())


def _collect_entity_candidates(turns, limit: int = 30) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    stopwords = {
        "The",
        "A",
        "An",
        "And",
        "In",
        "On",
        "At",
        "For",
        "Of",
        "To",
        "By",
        "With",
        "From",
        "After",
        "Before",
        "During",
        "Overview",
        "History",
        "Impact",
        "Legacy",
        "Background",
        "Timeline",
        "References",
        "External Links",
        "See Also",
    }
    pattern = re.compile(
        r"\b(?:[A-Z][a-z]+|[A-Z]{2,}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[A-Z]{2,}(?:\s+[A-Z][a-z]+)+)\b"
    )

    def add_matches(text: str) -> None:
        for match in pattern.findall(text or ""):
            value = match.strip(" .,;:()[]{}")
            if len(value) < 3 or value in stopwords:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            candidates.append(value)
            if len(candidates) >= limit:
                return

    for turn in turns:
        add_matches(turn.user_utterance)
        add_matches(turn.agent_utterance)
        for query in turn.search_queries[:5]:
            add_matches(query)
        for info in turn.search_results[:4]:
            add_matches(info.title)
            for snippet in info.snippets[:1]:
                add_matches(snippet)
        if len(candidates) >= limit:
            break

    return candidates[:limit]


def run(
    config: StormGraphConfig,
    topic: str,
    information_table,
    outline_generator: OutlineGenerator,
) -> tuple[StormArticle, StormArticle]:
    turns = []
    for _persona, dialogue_turns in information_table.conversations:
        turns.extend(dialogue_turns)
    conversation_blocks: list[str] = []
    for turn in turns:
        source_titles = []
        for info in turn.search_results[:4]:
            title = (info.title or "").strip()
            if title and title not in source_titles:
                source_titles.append(title)
        block_lines = [
            f"Wikipedia Writer: {turn.user_utterance}",
            f"Search Queries: {', '.join(turn.search_queries[:5])}" if turn.search_queries else "",
            f"Source Titles: {', '.join(source_titles)}" if source_titles else "",
            f"Expert: {turn.agent_utterance}",
        ]
        conversation_blocks.append("\n".join(line for line in block_lines if line))
    entity_candidates = _collect_entity_candidates(turns)
    entity_block = (
        "Candidate Entities for Headings:\n- " + "\n- ".join(entity_candidates)
        if entity_candidates
        else ""
    )
    conversation_text = "\n\n".join(
        block for block in [entity_block, "\n\n".join(conversation_blocks)] if block
    )
    words = conversation_text.split()
    if len(words) > config.outline_conv_word_budget:
        conversation_text = " ".join(words[: config.outline_conv_word_budget])

    draft_outline_text = _clean_up_outline(
        outline_generator.generate_direct_outline(topic),
        topic=topic,
    )
    refined_outline_text = _clean_up_outline(
        outline_generator.refine_outline(
        topic=topic,
        conversation_text=conversation_text,
        draft_outline=draft_outline_text,
    ),
        topic=topic,
    )
    return (
        StormArticle.from_outline_str(topic, refined_outline_text),
        StormArticle.from_outline_str(topic, draft_outline_text),
    )
