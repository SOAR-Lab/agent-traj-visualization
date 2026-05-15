"""Lightweight data structures for TraceView."""

from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict


@dataclass(frozen=True)
class SidebarControls:
    graph_mode: str
    inspector_separate_page: bool
    selected_edge_families: tuple[str, ...]
    selected_structural_edges: tuple[str, ...]
    show_only_bad: bool
    show_only_loopish: bool
    show_only_no_influence: bool
    step_spacing: int
    lane_gap: int
    node_size: int
    label_max_len: int
    show_edge_labels: bool

    @property
    def filters_active(self) -> bool:
        return (
            self.show_only_bad
            or self.show_only_loopish
            or self.show_only_no_influence
        )

    @property
    def show_ta(self) -> bool:
        return "Thought → Action" in self.selected_edge_families

    @property
    def show_tt(self) -> bool:
        return "Thought → Thought" in self.selected_edge_families

    @property
    def show_aa(self) -> bool:
        return "Action → Action" in self.selected_edge_families

    @property
    def show_rt(self) -> bool:
        return "Result → Thought" in self.selected_edge_families

    @property
    def show_ra(self) -> bool:
        return "Result → Action" in self.selected_edge_families

    @property
    def show_structural_ar(self) -> bool:
        return self.show_structural_flow

    @property
    def show_structural_flow(self) -> bool:
        return any(
            option in self.selected_structural_edges
            for option in (
                "Core Flow (Structural)",
                "Action → Result (Structural)",
            )
        )


@dataclass(frozen=True)
class TrajectoryStep:
    step_index: int
    thought: str
    action: str
    result: str


@dataclass(frozen=True)
class ParsedTrajectory:
    task_id: str
    source_name: str
    steps: tuple[TrajectoryStep, ...]

    @property
    def key(self) -> str:
        return self.source_name or self.task_id


@dataclass(frozen=True)
class RelationCandidate:
    key: str
    task_id: str
    family: str
    source_node: str
    target_node: str
    source_step: int
    target_step: int
    source_text: str
    target_text: str


class IterationRecord(TypedDict):
    iteration_id: int
    category: str
    start_step: int
    end_step: int
    steps: list[int]
    action_summary: NotRequired[str]
    files: NotRequired[list[str]]
    context_label: NotRequired[str]
    relation_count: NotRequired[int]
    flagged_relations: NotRequired[list[str]]


class EdgeRecord(TypedDict):
    family: str
    source: str
    target: str
    src_step: int
    dst_step: int
    relation: str


class IterationEdgeRecord(TypedDict):
    source: str
    target: str
    color: str
    label: str
    record: EdgeRecord


class StaticRelationRecord(TypedDict):
    family: str
    relation: str


class ViewContext(TypedDict):
    task_id: str
    bug_report_url: str | None
    pull_request_url: str | None
    steps: list[int]
    cat_map: dict[int, str]
    iterations: list[IterationRecord]
    step_iteration: dict[int, int]
    log_data: dict[int, dict[str, str]]
    matched_patch_categories: list[str]
    patch_status: str
    static_relation_records: list[StaticRelationRecord]
    edge_records: list[EdgeRecord]
    nodes: list[Any]
    edges: list[Any]
    available_node_ids: set[str]


class OverviewRow(TypedDict):
    filename: str
    task_id: str
    agent_name: str
    outcome: str
    patch_status: str
    matched_patch_categories: list[str]
    iteration_count: int
    categories: list[str]
    relation_counts: dict[str, int]
    flagged_relations: list[str]
    first_flagged_iteration: int | None
    pull_request_url: str | None
    is_user_export: bool
