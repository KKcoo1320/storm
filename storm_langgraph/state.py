from typing import Any, Optional, TypedDict

from .types import StormArticle, StormInformationTable


class StormGraphState(TypedDict, total=False):
    topic: str
    ground_truth_url: str
    do_research: bool
    do_generate_outline: bool
    do_generate_article: bool
    do_polish_article: bool
    remove_duplicate: bool
    personas: list[str]
    conversation_log: list[dict[str, Any]]
    information_table: StormInformationTable
    outline: StormArticle
    draft_outline: StormArticle
    draft_article: StormArticle
    polished_article: StormArticle
    artifacts_dir: Optional[str]

