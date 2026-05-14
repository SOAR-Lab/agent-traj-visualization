"""Shared helpers for the single-run labeling workspace."""

from __future__ import annotations

import html

from traceview_app.shared.models import ParsedTrajectory, RelationCandidate
from traceview_app.trajectory import (
    UNLABELED_ACTION_LABEL,
    UNLABELED_RELATION_LABEL,
    action_label_for_step,
    label_for_candidate,
)

LABELER_EDITOR_VERSION = "v4"
MIN_LABELS_TO_ADVANCE = 5
WORKSPACE_STEP_ACTIONS = "actions"
WORKSPACE_STEP_RELATIONSHIPS = "relationships"


def black_row_text(target: object, text: object, *, bold: bool = False) -> None:
    weight = "600" if bold else "400"
    target.markdown(
        (
            f'<span style="color:#111111;font-size:0.875rem;'
            f'font-weight:{weight};">{html.escape(str(text))}</span>'
        ),
        unsafe_allow_html=True,
    )


def option_index(options: tuple[str, ...], label: str) -> int:
    try:
        return options.index(label)
    except ValueError:
        return 0


def required_label_count(total_count: int) -> int:
    return min(MIN_LABELS_TO_ADVANCE, max(total_count, 0))


def labels_ready(labeled_count: int, total_count: int) -> bool:
    return labeled_count >= required_label_count(total_count)


def remaining_required_labels(labeled_count: int, total_count: int) -> int:
    return max(required_label_count(total_count) - labeled_count, 0)


def count_action_labels(
    trajectory: ParsedTrajectory,
    current_action_labels: dict[str, str],
) -> int:
    return sum(
        1
        for step in trajectory.steps
        if action_label_for_step(
            trajectory,
            step.step_index,
            current_action_labels,
        )
        != UNLABELED_ACTION_LABEL
    )


def count_relationship_labels(
    candidates: list[RelationCandidate],
    current_labels: dict[str, str],
) -> int:
    return sum(
        1
        for candidate in candidates
        if label_for_candidate(candidate, current_labels) != UNLABELED_RELATION_LABEL
    )
