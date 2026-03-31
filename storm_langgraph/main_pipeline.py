from __future__ import annotations

from langgraph.graph import END, StateGraph

from .config import StormGraphConfig
from .nodes.article_node import build_node as article_node
from .nodes.curation_node import build_node as curation_node
from .nodes.outline_node import build_node as outline_node
from .nodes.persona_node import build_node as persona_node
from .nodes.polish_node import build_node as polish_node
from .state import StormGraphState


def build_graph(
    config: StormGraphConfig,
    *,
    persona_generator=None,
    question_asker,
    query_generator,
    retriever,
    answer_synthesizer,
    outline_generator,
    section_writer,
    polisher,
):
    graph = StateGraph(StormGraphState)

    graph.add_node("persona", persona_node(config, persona_generator=persona_generator))
    graph.add_node(
        "curation",
        curation_node(
            config,
            question_asker=question_asker,
            query_generator=query_generator,
            retriever=retriever,
            answer_synthesizer=answer_synthesizer,
        ),
    )
    graph.add_node("outline", outline_node(config, outline_generator=outline_generator))
    graph.add_node("article", article_node(config, section_writer=section_writer))
    graph.add_node("polish", polish_node(polisher=polisher))

    graph.set_entry_point("persona")
    graph.add_edge("persona", "curation")
    graph.add_edge("curation", "outline")
    graph.add_edge("outline", "article")
    graph.add_edge("article", "polish")
    graph.add_edge("polish", END)
    return graph.compile()

