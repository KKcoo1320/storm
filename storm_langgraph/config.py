from dataclasses import dataclass, field


@dataclass
class StormGraphConfig:
    max_conv_turn: int = 3
    max_perspective: int = 3
    max_search_queries_per_turn: int = 3
    search_top_k: int = 3
    retrieve_top_k: int = 3
    max_thread_num: int = 8
    vector_chunk_size: int = 500
    vector_chunk_overlap: int = 100
    web_snippet_chunk_size: int = 1000
    outline_conv_word_budget: int = 5000
    answer_info_word_budget: int = 1000
    section_info_word_budget: int = 1500
    persona_seed: list[str] = field(
        default_factory=lambda: [
            "Basic fact writer: Focus on broad and foundational coverage."
        ]
    )

