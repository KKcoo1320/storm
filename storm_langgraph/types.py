from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", (text or "").lower())


def _cosine_from_counters(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _text_vector(text: str) -> dict[str, float]:
    vector: dict[str, float] = {}
    for token in _tokenize(text):
        vector[token] = vector.get(token, 0.0) + 1.0
    return vector


@dataclass
class Information:
    url: str
    description: str
    snippets: list[str]
    title: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "description": self.description,
            "snippets": list(self.snippets),
            "title": self.title,
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Information":
        return cls(
            url=payload["url"],
            description=payload.get("description", ""),
            snippets=list(payload.get("snippets", [])),
            title=payload.get("title", ""),
            meta=dict(payload.get("meta", {})),
        )


@dataclass
class DialogueTurn:
    user_utterance: str
    agent_utterance: str
    search_queries: list[str] = field(default_factory=list)
    search_results: list[Information] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_utterance": self.user_utterance,
            "agent_utterance": self.agent_utterance,
            "search_queries": list(self.search_queries),
            "search_results": [item.to_dict() for item in self.search_results],
        }


@dataclass
class SectionNode:
    section_name: str
    content: str = ""
    children: list["SectionNode"] = field(default_factory=list)

    def add_child(self, child: "SectionNode", insert_to_front: bool = False) -> None:
        if insert_to_front:
            self.children.insert(0, child)
        else:
            self.children.append(child)


@dataclass
class StormArticle:
    topic_name: str
    root: SectionNode = field(init=False)
    references: dict[str, Any] = field(
        default_factory=lambda: {"url_to_unified_index": {}, "url_to_info": {}}
    )

    def __post_init__(self) -> None:
        self.root = SectionNode(self.topic_name)

    def find_section(
        self, node: Optional[SectionNode], name: str
    ) -> Optional[SectionNode]:
        if node is None:
            return None
        if node.section_name == name:
            return node
        for child in node.children:
            found = self.find_section(child, name)
            if found is not None:
                return found
        return None

    def get_first_level_section_names(self) -> list[str]:
        return [child.section_name for child in self.root.children]

    def get_outline_as_list(
        self,
        root_section_name: Optional[str] = None,
        add_hashtags: bool = False,
        include_root: bool = True,
    ) -> list[str]:
        node = self.root if root_section_name is None else self.find_section(self.root, root_section_name)
        if node is None:
            return []

        result: list[str] = []

        def walk(current: SectionNode, level: int) -> None:
            prefix = "#" * level if add_hashtags else ""
            result.append(f"{prefix} {current.section_name}".strip() if add_hashtags else current.section_name)
            for child in current.children:
                walk(child, level + 1)

        if include_root:
            walk(node, 1)
        else:
            for child in node.children:
                walk(child, 1)
        return result

    def insert_or_create_section(self, article_dict: dict[str, Any], parent_section_name: Optional[str] = None) -> None:
        parent = self.root if parent_section_name is None else self.find_section(self.root, parent_section_name)
        if parent is None:
            return
        for section_name, content_dict in article_dict.items():
            section = self.find_section(parent, section_name)
            if section is None:
                section = SectionNode(section_name=section_name, content=content_dict.get("content", "").strip())
                parent.add_child(
                    section,
                    insert_to_front=parent.section_name == self.root.section_name and section.section_name == "summary",
                )
            else:
                section.content = content_dict.get("content", "").strip()
            self.insert_or_create_section(content_dict.get("subsections", {}), section_name)

    def update_section(
        self,
        current_section_content: str,
        current_section_info_list: list[Information],
        parent_section_name: Optional[str] = None,
    ) -> None:
        citation_mapping = self._merge_new_info_to_references(current_section_info_list)
        updated_text = current_section_content
        for old_idx, new_idx in citation_mapping.items():
            updated_text = updated_text.replace(f"[{old_idx}]", f"[{new_idx}]")
        self.insert_or_create_section(parse_article_into_dict(updated_text), parent_section_name or self.root.section_name)

    def _merge_new_info_to_references(self, info_list: list[Information]) -> dict[int, int]:
        mapping: dict[int, int] = {}
        for idx, info in enumerate(info_list, start=1):
            if info.url not in self.references["url_to_unified_index"]:
                new_idx = len(self.references["url_to_unified_index"]) + 1
                self.references["url_to_unified_index"][info.url] = new_idx
                self.references["url_to_info"][info.url] = copy.deepcopy(info)
            mapping[idx] = self.references["url_to_unified_index"][info.url]
        return mapping

    def to_string(self) -> str:
        parts: list[str] = []

        def walk(node: SectionNode, level: int) -> None:
            parts.append(f"{'#' * level} {node.section_name}")
            if node.content.strip():
                parts.append(node.content.strip())
            for child in node.children:
                walk(child, level + 1)

        for child in self.root.children:
            walk(child, 1)
        return "\n\n".join(part for part in parts if part.strip())

    @classmethod
    def from_outline_str(cls, topic: str, outline_str: str) -> "StormArticle":
        article = cls(topic)
        lines = [line.strip() for line in (outline_str or "").splitlines() if line.strip()]
        if not lines:
            return article
        if lines[0].lstrip("# ").strip().lower() == topic.lower():
            lines = lines[1:]
        stack: list[tuple[int, SectionNode]] = [(0, article.root)]
        for line in lines:
            level = max(1, line.count("#"))
            name = line.lstrip("#").strip()
            node = SectionNode(name)
            while stack and level <= stack[-1][0]:
                stack.pop()
            stack[-1][1].add_child(node)
            stack.append((level, node))
        return article

    @classmethod
    def from_string(
        cls,
        topic_name: str,
        article_text: str,
        references: Optional[dict[str, Any]] = None,
    ) -> "StormArticle":
        article = cls(topic_name)
        article.insert_or_create_section(parse_article_into_dict(article_text))
        if references is not None:
            article.references = copy.deepcopy(references)
        return article


def parse_article_into_dict(article_text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, result)]
    current_name: Optional[str] = None
    for raw_line in (article_text or "").splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            name = line.lstrip("#").strip()
            entry = {"content": "", "subsections": {}}
            while stack and level <= stack[-1][0]:
                stack.pop()
            stack[-1][1][name] = entry
            stack.append((level, entry["subsections"]))
            current_name = name
        elif current_name is not None:
            parent_map = stack[-2][1]
            parent_map[current_name]["content"] = (parent_map[current_name]["content"] + "\n" + line).strip()
    return result


@dataclass
class StormInformationTable:
    conversations: list[tuple[str, list[DialogueTurn]]] = field(default_factory=list)
    url_to_info: dict[str, Information] = field(default_factory=dict)
    _snippet_rows: list[tuple[str, str, dict[str, float]]] = field(default_factory=list)

    def rebuild(self) -> None:
        merged: dict[str, Information] = {}
        for persona, turns in self.conversations:
            for turn in turns:
                for info in turn.search_results:
                    if info.url not in merged:
                        merged[info.url] = copy.deepcopy(info)
                    else:
                        merged[info.url].snippets = list(
                            dict.fromkeys(merged[info.url].snippets + info.snippets)
                        )
        self.url_to_info = merged
        self._snippet_rows = []

    def prepare_for_retrieval(self) -> None:
        if not self.url_to_info:
            self.rebuild()
        rows: list[tuple[str, str, dict[str, float]]] = []
        for url, info in self.url_to_info.items():
            for snippet in info.snippets:
                rows.append((url, snippet, _text_vector(snippet)))
        self._snippet_rows = rows

    def retrieve_information(self, queries: list[str] | str, search_top_k: int) -> list[Information]:
        if isinstance(queries, str):
            queries = [queries]
        if not self._snippet_rows:
            self.prepare_for_retrieval()
        selected: dict[str, set[str]] = {}
        for query in queries:
            q_vec = _text_vector(query)
            scored = [
                (url, snippet, _cosine_from_counters(q_vec, snippet_vec))
                for url, snippet, snippet_vec in self._snippet_rows
            ]
            scored.sort(key=lambda item: item[2], reverse=True)
            for url, snippet, _score in scored[:search_top_k]:
                selected.setdefault(url, set()).add(snippet)
        results: list[Information] = []
        for url, snippets in selected.items():
            base = copy.deepcopy(self.url_to_info[url])
            base.snippets = list(snippets)
            results.append(base)
        return results

    def to_conversation_log(self) -> list[dict[str, Any]]:
        return [
            {
                "perspective": persona,
                "dlg_turns": [turn.to_dict() for turn in turns],
            }
            for persona, turns in self.conversations
        ]
