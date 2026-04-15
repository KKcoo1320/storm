from __future__ import annotations

import asyncio
import csv
import json
import os
from pathlib import Path

from storm_langgraph.config import StormGraphConfig
from storm_langgraph.demo.real_components import (
    DuckDuckGoRetriever,
    LLMAnswerSynthesizer,
    LLMArticlePolisher,
    LLMOutlineGenerator,
    LLMPersonaGenerator,
    LLMQueryGenerator,
    LLMQuestionAsker,
    LLMSectionWriter,
    LocalTopicFileRetriever,
    OpenAICompatLLM,
    YouRetriever,
)
from storm_langgraph.main_pipeline import build_graph


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "real_output_batch"


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


def build_retriever(name: str, topic: str, config: StormGraphConfig):
    if name == "duckduckgo":
        return DuckDuckGoRetriever(k=config.search_top_k)
    if name == "freshwiki_local":
        freshwiki_dir = os.environ.get(
            "STORM_LANGGRAPH_FRESHWIKI_DIR",
            "/Users/wangbozhi/Documents/New project/storm_upstream_naacl/FreshWiki/txt",
        )
        return LocalTopicFileRetriever(
            topic=topic,
            corpus_dir=freshwiki_dir,
            chunk_size=config.web_snippet_chunk_size,
            chunk_overlap=config.vector_chunk_overlap,
            k=config.search_top_k,
        )
    return YouRetriever(k=config.search_top_k)


def build_config() -> StormGraphConfig:
    default_config = StormGraphConfig()
    return StormGraphConfig(
        max_perspective=int(
            os.environ.get("STORM_LANGGRAPH_MAX_PERSPECTIVE", default_config.max_perspective)
        ),
        max_conv_turn=int(
            os.environ.get("STORM_LANGGRAPH_MAX_CONV_TURN", default_config.max_conv_turn)
        ),
    )


async def run_topic(topic: str, ground_truth_url: str = ""):
    retriever_name = os.environ.get("STORM_LANGGRAPH_RETRIEVER", "you").lower()
    config = build_config()
    llm = OpenAICompatLLM()
    graph = build_graph(
        config,
        persona_generator=LLMPersonaGenerator(llm),
        question_asker=LLMQuestionAsker(llm),
        query_generator=LLMQueryGenerator(llm),
        retriever=build_retriever(retriever_name, topic, config),
        answer_synthesizer=LLMAnswerSynthesizer(llm),
        outline_generator=LLMOutlineGenerator(llm),
        section_writer=LLMSectionWriter(llm),
        polisher=LLMArticlePolisher(llm),
    )

    state = await graph.ainvoke(
        {
            "topic": topic,
            "ground_truth_url": ground_truth_url,
            "remove_duplicate": True,
        }
    )

    topic_name = topic.replace(" ", "_").replace("/", "_")
    topic_dir = OUTPUT_DIR / topic_name
    topic_dir.mkdir(parents=True, exist_ok=True)
    (topic_dir / "storm_gen_article_polished.txt").write_text(
        state["polished_article"].to_string(), encoding="utf-8"
    )
    (topic_dir / "storm_gen_article.txt").write_text(
        state["draft_article"].to_string(), encoding="utf-8"
    )
    (topic_dir / "storm_gen_outline.txt").write_text(
        state["outline"].to_string(), encoding="utf-8"
    )
    (topic_dir / "conversation_log.json").write_text(
        json.dumps(state["conversation_log"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (topic_dir / "state.json").write_text(
        json.dumps(_serialize_state(state), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Completed LangGraph topic: {topic}")


async def main():
    input_csv = os.environ.get("STORM_LANGGRAPH_BATCH_INPUT")
    if not input_csv:
        raise RuntimeError("STORM_LANGGRAPH_BATCH_INPUT is not set.")

    with open(input_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for row in rows:
        await run_topic(row["topic"], row.get("url", ""))


if __name__ == "__main__":
    asyncio.run(main())
