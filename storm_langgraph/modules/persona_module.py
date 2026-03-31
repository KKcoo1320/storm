from __future__ import annotations

from ..config import StormGraphConfig
from ..interfaces import PersonaGenerator


def run(
    config: StormGraphConfig,
    topic: str,
    persona_generator: PersonaGenerator | None = None,
) -> list[str]:
    if persona_generator is None:
        return list(config.persona_seed)
    personas = persona_generator.generate_personas(topic, config.max_perspective)
    if not personas:
        return list(config.persona_seed)
    merged = list(config.persona_seed)
    for persona in personas:
        if persona not in merged:
            merged.append(persona)
    return merged[: config.max_perspective + len(config.persona_seed)]

