from __future__ import annotations

from ..config import StormGraphConfig
from ..interfaces import OutlineGenerator
from ..types import StormArticle


def run(
    config: StormGraphConfig,
    topic: str,
    information_table,
    outline_generator: OutlineGenerator,
) -> tuple[StormArticle, StormArticle]:
    turns = []
    for _persona, dialogue_turns in information_table.conversations:
        turns.extend(dialogue_turns)
    conversation_text = "\n".join(
        f"Wikipedia Writer: {turn.user_utterance}\nExpert: {turn.agent_utterance}"
        for turn in turns
    )
    words = conversation_text.split()
    if len(words) > config.outline_conv_word_budget:
        conversation_text = " ".join(words[: config.outline_conv_word_budget])

    draft_outline_text = outline_generator.generate_direct_outline(topic)
    refined_outline_text = outline_generator.refine_outline(
        topic=topic,
        conversation_text=conversation_text,
        draft_outline=draft_outline_text,
    )
    return (
        StormArticle.from_outline_str(topic, refined_outline_text),
        StormArticle.from_outline_str(topic, draft_outline_text),
    )

