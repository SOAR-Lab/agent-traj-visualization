"""Iteration context UI for collapsed graph mode."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from traceview_app.models import IterationRecord


def _format_iteration_files(files: list[str], limit: int = 2) -> str:
    if not files:
        return "none"
    shown = files[:limit]
    label = ", ".join(shown)
    if len(files) > limit:
        label = f"{label} +{len(files) - limit}"
    return label


def _format_iteration_signals(iteration: IterationRecord) -> str:
    flagged = iteration.get("flagged_relations", [])
    if flagged:
        return ", ".join(flagged)
    relation_count = int(iteration.get("relation_count", 0))
    return f"{relation_count} relations" if relation_count else "none"


def _iteration_context_df(iterations: list[IterationRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Iteration": str(iteration["iteration_id"]),
                "Category": iteration["category"],
                "Action context": iteration.get("action_summary") or "none",
                "Files": _format_iteration_files(iteration.get("files", [])),
                "Signals": _format_iteration_signals(iteration),
            }
            for iteration in iterations
        ]
    )


def render_iteration_context_panel(
    iterations: list[IterationRecord],
    *,
    show_heading: bool = True,
) -> None:
    if not iterations:
        return

    if show_heading:
        st.markdown("### Iteration Context")
    st.caption(
        "Collapsed iteration nodes are summarized from the reconstructed log: "
        "action, files mentioned, and relation signals."
    )
    st.dataframe(
        _iteration_context_df(iterations),
        hide_index=True,
        width="stretch",
    )
