from __future__ import annotations

import asyncio
import json
from pathlib import Path

from storm_langgraph.config import StormGraphConfig
from storm_langgraph.demo.mock_components import (
    MockAnswerSynthesizer,
    MockArticlePolisher,
    MockOutlineGenerator,
    MockPersonaGenerator,
    MockQueryGenerator,
    MockQuestionAsker,
    MockRetriever,
    MockSectionWriter,
)
from storm_langgraph.main_pipeline import build_graph


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "demo_output"


def _serialize_state(state):
    def fallback(value):
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if hasattr(value, "to_string"):
            return value.to_string()
        if hasattr(value, "to_conversation_log"):
            return value.to_conversation_log()
        if hasattr(value, "__dict__"):
            return value.__dict__
        return str(value)

    return json.loads(json.dumps(state, default=fallback, ensure_ascii=False, indent=2))


async def main():
    config = StormGraphConfig(max_perspective=3, max_conv_turn=3)
    graph = build_graph(
        config,
        persona_generator=MockPersonaGenerator(),
        question_asker=MockQuestionAsker(),
        query_generator=MockQueryGenerator(),
        retriever=MockRetriever(),
        answer_synthesizer=MockAnswerSynthesizer(),
        outline_generator=MockOutlineGenerator(),
        section_writer=MockSectionWriter(),
        polisher=MockArticlePolisher(),
    )

    state = await graph.ainvoke(
        {
            "topic": "STORM-style agentic long-form RAG",
            "ground_truth_url": "",
            "remove_duplicate": True,
        }
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    article = state["polished_article"].to_string()
    (OUTPUT_DIR / "demo_article.txt").write_text(article, encoding="utf-8")
    (OUTPUT_DIR / "demo_state.json").write_text(
        json.dumps(_serialize_state(state), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Demo run completed.")
    print(f"Output article: {OUTPUT_DIR / 'demo_article.txt'}")
    print(f"Output state  : {OUTPUT_DIR / 'demo_state.json'}")
    print()
    print(article)


if __name__ == "__main__":
    asyncio.run(main())
