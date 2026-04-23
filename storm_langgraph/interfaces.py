from __future__ import annotations

from typing import Protocol

from .types import Information


class PersonaGenerator(Protocol):
    def generate_personas(self, topic: str, max_num_persona: int) -> list[str]: ...


class QuestionAsker(Protocol):
    def ask(self, topic: str, persona: str, dialogue_history: list[dict]) -> str: ...


class QueryGenerator(Protocol):
    def generate_queries(self, topic: str, question: str, max_queries: int) -> list[str]: ...


class Retriever(Protocol):
    def retrieve(self, queries: list[str], exclude_urls: list[str] | None = None) -> list[Information]: ...


class AnswerSynthesizer(Protocol):
    def answer(self, topic: str, question: str, gathered_info: list[Information]) -> str: ...


class OutlineGenerator(Protocol):
    def generate_direct_outline(self, topic: str) -> str: ...
    def refine_outline(self, topic: str, conversation_text: str, draft_outline: str) -> str: ...


class SectionWriter(Protocol):
    def write_section(self, topic: str, section_name: str, section_outline: str, collected_info: list[Information]) -> str: ...


class ArticlePolisher(Protocol):
    def write_lead(self, topic: str, draft_article: str) -> str: ...
    def deduplicate(self, draft_article: str) -> str: ...
