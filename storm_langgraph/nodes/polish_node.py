from ..modules import polish_module


def build_node(polisher):
    async def node(state):
        polished_article = polish_module.run(
            topic=state["topic"],
            draft_article=state["draft_article"],
            polisher=polisher,
            remove_duplicate=state.get("remove_duplicate", False),
        )
        return {**state, "polished_article": polished_article}

    return node

