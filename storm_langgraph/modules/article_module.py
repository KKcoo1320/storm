from __future__ import annotations

import copy

from ..config import StormGraphConfig
from ..interfaces import SectionWriter
from ..types import StormArticle, StormInformationTable


def run(
    config: StormGraphConfig,
    topic: str,
    information_table: StormInformationTable,
    outline: StormArticle,
    section_writer: SectionWriter,
) -> StormArticle:
    information_table.prepare_for_retrieval()
    article = copy.deepcopy(outline)
    for section_name in outline.get_first_level_section_names():
        if section_name.lower() == "introduction":
            continue
        if section_name.lower().startswith("conclusion") or section_name.lower().startswith("summary"):
            continue
        section_query = outline.get_outline_as_list(
            root_section_name=section_name,
            add_hashtags=False,
        )
        section_outline = "\n".join(
            outline.get_outline_as_list(
                root_section_name=section_name,
                add_hashtags=True,
            )
        )
        collected = information_table.retrieve_information(
            queries=section_query,
            search_top_k=config.retrieve_top_k,
        )
        section_text = section_writer.write_section(
            topic=topic,
            section_name=section_name,
            section_outline=section_outline,
            collected_info=collected,
        )
        article.update_section(
            current_section_content=section_text,
            current_section_info_list=collected,
            parent_section_name=topic,
        )
    return article

