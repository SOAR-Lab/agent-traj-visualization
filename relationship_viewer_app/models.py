"""Lightweight data structures for the relationship viewer."""

from dataclasses import dataclass


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
        return "Action → Result (Structural)" in self.selected_structural_edges


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
