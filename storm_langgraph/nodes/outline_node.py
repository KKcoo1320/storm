from ..modules import outline_module


def build_node(config, outline_generator):
    async def node(state):
        outline, draft_outline = outline_module.run(
            config=config,
            topic=state["topic"],
            information_table=state["information_table"],
            outline_generator=outline_generator,
        )
        return {
            **state,
            "outline": outline,
            "draft_outline": draft_outline,
        }

    return node

