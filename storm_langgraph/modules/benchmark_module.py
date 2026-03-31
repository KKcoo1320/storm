from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkPlan:
    dataset: str
    input_unit: str
    output_unit: str
    metrics: list[str]
    notes: str


def default_plans() -> list[BenchmarkPlan]:
    return [
        BenchmarkPlan(
            dataset="FreshWiki",
            input_unit="topic",
            output_unit="article with citations",
            metrics=[
                "outline tree similarity",
                "citation coverage",
                "section-level ROUGE-L",
                "reference diversity",
            ],
            notes="Closest public dataset to the original STORM paper setup.",
        ),
        BenchmarkPlan(
            dataset="WildSeek",
            input_unit="topic + information goal",
            output_unit="report helpfulness",
            metrics=[
                "human preference",
                "goal coverage",
                "citation usefulness",
            ],
            notes="Better for downstream utility than exact outline matching.",
        ),
    ]

