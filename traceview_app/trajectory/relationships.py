"""Relationship and label helpers for parsed trajectories."""

from __future__ import annotations

from traceview_app.shared.constants import (
    ACTION_LABEL_OPTIONS,
    REL_SPECS,
    RELATION_LABEL_OPTIONS,
    RELATION_LABEL_OPTIONS_BY_FAMILY,
)
from traceview_app.shared.models import ParsedTrajectory, RelationCandidate, TrajectoryStep
from traceview_app.shared.node_ids import (
    ACTION_NODE_KIND,
    RESULT_NODE_KIND,
    THOUGHT_NODE_KIND,
    node_kind_name,
    step_node_id,
)
from traceview_app.trajectory.common import (
    UNLABELED_ACTION_LABEL,
    UNLABELED_RELATION_LABEL,
    VIEWER_EXPORT_CATEGORY,
)


def node_text(step: TrajectoryStep, node_kind: str) -> str:
    if node_kind == THOUGHT_NODE_KIND:
        return step.thought
    if node_kind == ACTION_NODE_KIND:
        return step.action
    if node_kind == RESULT_NODE_KIND:
        return step.result
    return ""


def build_relation_candidates(trajectory: ParsedTrajectory) -> list[RelationCandidate]:
    candidates: list[RelationCandidate] = []
    steps_by_index = {step.step_index: step for step in trajectory.steps}

    for family, spec in REL_SPECS.items():
        for step in trajectory.steps:
            source_step = step.step_index
            target_step = source_step + int(spec["offset"])
            target = steps_by_index.get(target_step)
            if target is None:
                continue

            source_node = step_node_id(spec["src"], source_step)
            target_node = step_node_id(spec["dst"], target_step)
            candidates.append(
                RelationCandidate(
                    key=f"{trajectory.key}|{family}|{source_step}",
                    task_id=trajectory.task_id,
                    family=family,
                    source_node=source_node,
                    target_node=target_node,
                    source_step=source_step,
                    target_step=target_step,
                    source_text=node_text(step, spec["src"]),
                    target_text=node_text(target, spec["dst"]),
                )
            )

    return candidates


def family_display_name(family: str) -> str:
    spec = REL_SPECS[family]
    return f"{node_kind_name(spec['src'])} -> {node_kind_name(spec['dst'])}"


def relation_label_options_for_family(family: str) -> tuple[str, ...]:
    return RELATION_LABEL_OPTIONS_BY_FAMILY.get(family, RELATION_LABEL_OPTIONS)


def ui_label_options_for_family(family: str) -> tuple[str, ...]:
    return (UNLABELED_RELATION_LABEL, *relation_label_options_for_family(family))


def label_for_candidate(candidate: RelationCandidate, labels: dict[str, str]) -> str:
    label = labels.get(candidate.key, UNLABELED_RELATION_LABEL)
    if label not in relation_label_options_for_family(candidate.family):
        return UNLABELED_RELATION_LABEL
    return label


def export_label_for_candidate(candidate: RelationCandidate, labels: dict[str, str]) -> str:
    label = label_for_candidate(candidate, labels)
    return "" if label == UNLABELED_RELATION_LABEL else label


def action_label_key(trajectory: ParsedTrajectory, step_index: int) -> str:
    return f"{trajectory.key}|action|{step_index}"


def action_label_for_step(
    trajectory: ParsedTrajectory,
    step_index: int,
    action_labels: dict[str, str],
) -> str:
    label = action_labels.get(action_label_key(trajectory, step_index), UNLABELED_ACTION_LABEL)
    return label if label in ACTION_LABEL_OPTIONS else UNLABELED_ACTION_LABEL


def export_action_label_for_step(
    trajectory: ParsedTrajectory,
    step_index: int,
    action_labels: dict[str, str],
) -> str:
    label = action_label_for_step(trajectory, step_index, action_labels)
    return VIEWER_EXPORT_CATEGORY if label == UNLABELED_ACTION_LABEL else label
