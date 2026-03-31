from __future__ import annotations

from ..interfaces import ArticlePolisher
from ..types import StormArticle


def run(
    topic: str,
    draft_article: StormArticle,
    polisher: ArticlePolisher,
    remove_duplicate: bool = False,
) -> StormArticle:
    article_text = draft_article.to_string()
    lead = polisher.write_lead(topic, article_text).strip()
    body = polisher.deduplicate(article_text).strip() if remove_duplicate else article_text
    polished = StormArticle.from_string(topic, f"# summary\n{lead}\n\n{body}", draft_article.references)
    return polished

