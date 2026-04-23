"""WTB integration for the STORM LangGraph pipeline.

Provides a zero-arg ``graph_factory`` suitable for ``WorkflowProject``,
plus helper functions for registering canonical component variants.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .adapters import CanonicalToStormRetriever
from .config import StormGraphConfig
from .main_pipeline import build_graph


def create_storm_graph_factory(
    config: StormGraphConfig | None = None,
    *,
    persona_generator: Any = None,
    question_asker: Any = None,
    query_generator: Any = None,
    retriever: Any = None,
    answer_synthesizer: Any = None,
    outline_generator: Any = None,
    section_writer: Any = None,
    polisher: Any = None,
) -> Callable:
    """Return a zero-arg factory that builds the STORM LangGraph.

    All component arguments are captured in the closure so that the
    returned callable matches ``WorkflowProject.graph_factory`` signature
    (``Callable[[], CompiledGraph]``).
    """
    cfg = config or StormGraphConfig()

    def factory():
        return build_graph(
            cfg,
            persona_generator=persona_generator,
            question_asker=question_asker,
            query_generator=query_generator,
            retriever=retriever,
            answer_synthesizer=answer_synthesizer,
            outline_generator=outline_generator,
            section_writer=section_writer,
            polisher=polisher,
        )

    return factory


def create_storm_project(
    name: str = "storm_langgraph",
    config: StormGraphConfig | None = None,
    *,
    persona_generator: Any = None,
    question_asker: Any = None,
    query_generator: Any = None,
    retriever: Any = None,
    answer_synthesizer: Any = None,
    outline_generator: Any = None,
    section_writer: Any = None,
    polisher: Any = None,
) -> Any:
    """Create a ``WorkflowProject`` for the STORM pipeline.

    Returns the project so callers can further ``register_variant()`` on it.
    """
    from wtb.sdk import WorkflowProject

    factory = create_storm_graph_factory(
        config,
        persona_generator=persona_generator,
        question_asker=question_asker,
        query_generator=query_generator,
        retriever=retriever,
        answer_synthesizer=answer_synthesizer,
        outline_generator=outline_generator,
        section_writer=section_writer,
        polisher=polisher,
    )

    project = WorkflowProject(
        name=name,
        graph_factory=factory,
        description="STORM Wikipedia-style article generation pipeline (LangGraph)",
    )
    return project
