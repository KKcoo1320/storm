from __future__ import annotations

from ..config import StormGraphConfig
from ..interfaces import AnswerSynthesizer, QueryGenerator, QuestionAsker, Retriever
from ..types import DialogueTurn, StormInformationTable


def _compact_history(turns: list[DialogueTurn]) -> list[dict]:
    return [
        {
            "user": turn.user_utterance,
            "assistant": turn.agent_utterance,
            "queries": list(turn.search_queries),
        }
        for turn in turns[-8:]
    ]


def run(
    config: StormGraphConfig,
    topic: str,
    personas: list[str],
    question_asker: QuestionAsker,
    query_generator: QueryGenerator,
    retriever: Retriever,
    answer_synthesizer: AnswerSynthesizer,
    ground_truth_url: str = "",
) -> tuple[StormInformationTable, list[dict]]:
    conversations: list[tuple[str, list[DialogueTurn]]] = []
    for persona in personas:
        turns: list[DialogueTurn] = []
        for _ in range(config.max_conv_turn):
            question = question_asker.ask(topic, persona, _compact_history(turns)).strip()
            if not question or question.startswith("Thank you so much for your help!"):
                break
            queries = query_generator.generate_queries(
                topic,
                question,
                config.max_search_queries_per_turn,
            )[: config.max_search_queries_per_turn]
            search_results = retriever.retrieve(queries, exclude_urls=[ground_truth_url] if ground_truth_url else [])
            answer = answer_synthesizer.answer(topic, question, search_results)
            turns.append(
                DialogueTurn(
                    user_utterance=question,
                    agent_utterance=answer,
                    search_queries=queries,
                    search_results=search_results,
                )
            )
        conversations.append((persona, turns))

    info_table = StormInformationTable(conversations=conversations)
    info_table.rebuild()
    return info_table, info_table.to_conversation_log()
