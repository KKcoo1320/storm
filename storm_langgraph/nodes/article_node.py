from ..modules import article_module


def build_node(config, section_writer):
    async def node(state):
        draft_article = article_module.run(
            config=config,
            topic=state["topic"],
            information_table=state["information_table"],
            outline=state["outline"],
            section_writer=section_writer,
        )
        return {**state, "draft_article": draft_article}

    return node

