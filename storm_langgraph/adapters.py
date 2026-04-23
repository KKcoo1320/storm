"""Adapters between STORM-internal types/protocols and canonical rag_contracts.

Two directions:
  - Forward: STORM implementation -> canonical protocol (export STORM components)
  - Reverse: canonical protocol -> STORM interface (import external components)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from rag_contracts import (
    GenerationResult,
    QueryContext,
    RetrievalResult,
)
from rag_contracts import Generation as CanonicalGeneration
from rag_contracts import Query as CanonicalQuery
from rag_contracts import Reranking as CanonicalReranking
from rag_contracts import Retrieval as CanonicalRetrieval

from .interfaces import (
    AnswerSynthesizer,
    ArticlePolisher,
    OutlineGenerator,
    PersonaGenerator,
    QueryGenerator,
    QuestionAsker,
    SectionWriter,
)
from .types import Information, StormInformationTable


# ═══════════════════════════════════════════════════════════════════════════════
# Conversion helpers
# ═══════════════════════════════════════════════════════════════════════════════


def information_to_retrieval_result(info: Information) -> RetrievalResult:
    return RetrievalResult(
        source_id=info.url,
        content="\n".join(info.snippets),
        score=0.0,
        title=info.title,
        metadata={
            "description": info.description,
            "snippets": list(info.snippets),
            **info.meta,
        },
    )


def retrieval_result_to_information(result: RetrievalResult) -> Information:
    snippets = result.metadata.get("snippets")
    if not snippets:
        snippets = [result.content] if result.content else []
    return Information(
        url=result.source_id,
        description=result.metadata.get("description", ""),
        snippets=list(snippets),
        title=result.title,
        meta={
            k: v
            for k, v in result.metadata.items()
            if k not in ("description", "snippets")
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Forward adapters: STORM implementation -> canonical protocol
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class StormRetrievalAdapter:
    """Wraps a STORM ``Retriever`` to satisfy ``rag_contracts.Retrieval``."""

    storm_retriever: Any

    def retrieve(
        self, queries: list[str], top_k: int = 10
    ) -> list[RetrievalResult]:
        infos: list[Information] = self.storm_retriever.retrieve(queries)
        return [information_to_retrieval_result(i) for i in infos[:top_k]]


@dataclass
class StormRerankingAdapter:
    """Wraps ``StormInformationTable.retrieve_information`` as ``rag_contracts.Reranking``."""

    info_table: StormInformationTable

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 10
    ) -> list[RetrievalResult]:
        infos = self.info_table.retrieve_information([query], search_top_k=top_k)
        return [information_to_retrieval_result(i) for i in infos]


@dataclass
class StormQueryAdapter:
    """Wraps STORM's persona-driven query expansion as ``rag_contracts.Query``."""

    question_asker: QuestionAsker
    query_generator: QueryGenerator
    persona: str = "General researcher"

    def process(self, query: str, context: QueryContext) -> list[str]:
        history = [
            {"user": h.get("user", ""), "assistant": h.get("assistant", "")}
            for h in context.history
        ]
        question = self.question_asker.ask(context.topic or query, self.persona, history)
        if not question or question.startswith("Thank you so much for your help!"):
            return [query]
        queries = self.query_generator.generate_queries(
            context.topic or query, question, 5
        )
        return queries if queries else [query]


@dataclass
class StormGenerationAdapter:
    """Wraps STORM's ``SectionWriter`` as ``rag_contracts.Generation``."""

    section_writer: SectionWriter

    def generate(
        self,
        query: str,
        context: list[RetrievalResult],
        instruction: str = "",
    ) -> GenerationResult:
        infos = [retrieval_result_to_information(r) for r in context]
        section_name = instruction or query
        text = self.section_writer.write_section(
            topic=query,
            section_name=section_name,
            section_outline=instruction,
            collected_info=infos,
        )
        citations = [r.source_id for r in context]
        return GenerationResult(output=text, citations=citations)


# ═══════════════════════════════════════════════════════════════════════════════
# Reverse adapters: canonical protocol -> STORM interface
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CanonicalToStormRetriever:
    """Wraps a ``rag_contracts.Retrieval`` to satisfy STORM's ``Retriever`` protocol."""

    canonical_retrieval: Any
    default_top_k: int = 10

    def retrieve(
        self, queries: list[str], exclude_urls: list[str] | None = None
    ) -> list[Information]:
        results: list[RetrievalResult] = self.canonical_retrieval.retrieve(
            queries, top_k=self.default_top_k
        )
        exclude = set(exclude_urls or [])
        infos = [
            retrieval_result_to_information(r)
            for r in results
            if r.source_id not in exclude
        ]
        return infos


@dataclass
class CanonicalToStormReranking:
    """Wraps a ``rag_contracts.Reranking`` so it can be used where STORM expects
    ``StormInformationTable.retrieve_information``-style calls."""

    canonical_reranking: Any
    info_table: StormInformationTable | None = None

    def retrieve_information(
        self, queries: list[str] | str, search_top_k: int
    ) -> list[Information]:
        if isinstance(queries, str):
            queries = [queries]
        if self.info_table is not None:
            self.info_table.prepare_for_retrieval()
            candidate_infos = []
            for url, info in self.info_table.url_to_info.items():
                candidate_infos.append(info)
            candidates = [information_to_retrieval_result(i) for i in candidate_infos]
        else:
            candidates = []

        all_reranked: list[RetrievalResult] = []
        for q in queries:
            reranked = self.canonical_reranking.rerank(q, candidates, top_k=search_top_k)
            all_reranked.extend(reranked)

        seen: dict[str, Information] = {}
        for rr in all_reranked:
            info = retrieval_result_to_information(rr)
            if info.url not in seen:
                seen[info.url] = info
            else:
                seen[info.url].snippets = list(
                    dict.fromkeys(seen[info.url].snippets + info.snippets)
                )
        return list(seen.values())[:search_top_k]


@dataclass
class CanonicalToStormQuery:
    """Wraps a ``rag_contracts.Query`` to satisfy STORM's
    ``QueryGenerator`` protocol.

    STORM's ``QueryGenerator`` has ``generate_queries(topic, question, max_queries)``.
    This adapter delegates to the canonical ``Query.process()`` method,
    ignoring the *question* parameter (the canonical interface doesn't
    distinguish topic from sub-question).
    """

    canonical_query: Any

    def generate_queries(
        self, topic: str, question: str, max_queries: int
    ) -> list[str]:
        ctx = QueryContext(topic=topic, history=[{"user": question, "assistant": ""}])
        expanded = self.canonical_query.process(question, ctx)
        return expanded[:max_queries] if expanded else [question]


@dataclass
class CanonicalToStormGeneration:
    """Wraps a ``rag_contracts.Generation`` to satisfy STORM's
    ``SectionWriter`` protocol.

    STORM's ``SectionWriter`` has
    ``write_section(topic, section_name, section_outline, collected_info)``.
    This adapter converts the STORM ``Information`` list to canonical
    ``RetrievalResult``, calls the canonical generator, and returns the
    text output.
    """

    canonical_generation: Any

    def write_section(
        self,
        topic: str,
        section_name: str,
        section_outline: str,
        collected_info: list[Information],
    ) -> str:
        context = [information_to_retrieval_result(i) for i in collected_info]
        result = self.canonical_generation.generate(
            query=topic,
            context=context,
            instruction=section_outline or section_name,
        )
        return result.output
