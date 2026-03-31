from ..modules import persona_module


def build_node(config, persona_generator=None):
    async def node(state):
        personas = persona_module.run(
            config=config,
            topic=state["topic"],
            persona_generator=persona_generator,
        )
        return {**state, "personas": personas}

    return node

