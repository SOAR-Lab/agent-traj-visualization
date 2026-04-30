"""Inspector UI for node-level evidence and raw logs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from relationship_viewer_app.constants import BAD_RELS, LOOPISH_RELS
from relationship_viewer_app.context import extract_file_mentions, summarize_action
from relationship_viewer_app.models import SidebarControls
from relationship_viewer_app.ui_common import format_step_range, wrapped_log_block


def _pretty_node_id(node_id: str) -> str:
    kind, step = node_id.split("_")
    kind_name = {"T": "Thought", "A": "Action", "R": "Result"}.get(kind, kind)
    return f"{kind_name} {step}"


def _relation_table_df(rels: list[dict]) -> pd.DataFrame:
    rows = []
    for rel in rels:
        rows.append(
            {
                "Family": rel["family"].replace("_", " → ").title(),
                "Source": _pretty_node_id(rel["source"]),
                "Target": _pretty_node_id(rel["target"]),
                "Label": rel["relation"],
            }
        )
    return pd.DataFrame(rows)


def _iteration_relation_table_df(rels: list[dict]) -> pd.DataFrame:
    rows = []
    for rel in rels:
        rows.append(
            {
                "Family": rel["family"].replace("_", " → ").title(),
                "Source step": rel["src_step"],
                "Target step": rel["dst_step"],
                "Label": rel["relation"],
            }
        )
    return pd.DataFrame(rows)


def _render_relation_table(title: str, rels: list[dict]) -> None:
    st.markdown(f"**{title}**")
    if not rels:
        st.caption("None")
        return
    st.dataframe(
        _relation_table_df(rels),
        hide_index=True,
        use_container_width=True,
    )


def _render_iteration_relation_table(title: str, rels: list[dict]) -> None:
    st.markdown(f"**{title}**")
    if not rels:
        st.caption("None")
        return
    st.dataframe(
        _iteration_relation_table_df(rels),
        hide_index=True,
        use_container_width=True,
    )


def _short_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    return normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized


def _relation_signal_color(relation: str) -> str:
    if relation in BAD_RELS:
        return "red"
    if relation in LOOPISH_RELS:
        return "violet"
    if relation in {"Alignment", "Follow-up", "Follow up", "Refinement", "Informative", "Triggering"}:
        return "green"
    if relation in {"No influence", "No-influence"}:
        return "gray"
    return "orange"


def _flagged_relation_labels(rels: list[dict]) -> list[str]:
    labels = sorted(
        {
            rel["relation"]
            for rel in rels
            if rel["relation"] in BAD_RELS or rel["relation"] in LOOPISH_RELS
        }
    )
    return labels


def _render_badge_row(values: list[str], *, color: str = "gray") -> None:
    if not values:
        st.caption("none")
        return
    with st.container(horizontal=True):
        for value in values:
            st.badge(_short_path(value), color=color, help=value)


def _render_relation_badges(relations: list[str]) -> None:
    if not relations:
        st.caption("none")
        return
    with st.container(horizontal=True):
        for relation in relations:
            st.badge(relation, color=_relation_signal_color(relation))


def _render_inspector_evidence_header(
    *,
    title: str,
    subtitle: str,
    category: str,
    span: str,
    action_context: str,
    files: list[str],
    incoming_count: int,
    outgoing_count: int,
    flagged_relations: list[str],
) -> None:
    with st.container(border=True):
        st.caption("INSPECTOR TARGET")
        st.subheader(title)
        if subtitle:
            st.caption(subtitle)

        metric_cols = st.columns(4)
        metric_cols[0].metric("Category", category or "unknown")
        metric_cols[1].metric("Span", span)
        metric_cols[2].metric("Incoming", incoming_count)
        metric_cols[3].metric("Outgoing", outgoing_count)

        if action_context:
            st.markdown("**Action context**")
            st.write(action_context)

        file_col, relation_col = st.columns(2)
        with file_col:
            st.markdown("**Files mentioned**")
            _render_badge_row(files[:4])
        with relation_col:
            st.markdown("**Flagged relations**")
            _render_relation_badges(flagged_relations)

        st.caption("Raw logs below are the evidence for this selected graph target.")


def _render_step_log_evidence(
    *,
    step_index: int,
    entry: dict[str, str],
    category: str,
    expanded: bool,
) -> None:
    label = f"Step {step_index}"
    if category:
        label = f"{label} · {category}"
    with st.expander(label, expanded=expanded):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Thought**")
            wrapped_log_block(entry.get("thought", ""))
        with col2:
            st.markdown("**Action**")
            wrapped_log_block(entry.get("action", ""))
        with col3:
            st.markdown("**Result**")
            wrapped_log_block(entry.get("result", ""))


def render_inspector(
    *,
    selected: str | None,
    controls: SidebarControls,
    cat_map: dict[int, str],
    log_data: dict[int, dict[str, str]],
    edge_records: list[dict],
    iterations: list[dict],
    step_iteration: dict[int, int],
    standalone: bool = False,
) -> None:
    if not standalone:
        st.markdown("---")
        st.header("Inspector")

    if not selected:
        if not standalone:
            st.write("Click a node to inspect it.")
        return

    selected_id = str(selected)

    if controls.graph_mode == "Detailed":
        node_kind, step_str = selected_id.split("_")
        step_index = int(step_str)
        category = cat_map.get(step_index, "")
        entry = log_data.get(step_index, {})

        kind_name = {"T": "Thought", "A": "Action", "R": "Result"}.get(
            node_kind,
            node_kind,
        )
        rels_for_node = [
            edge
            for edge in edge_records
            if edge["source"] == selected_id or edge["target"] == selected_id
        ]
        incoming = [edge for edge in rels_for_node if edge["target"] == selected_id]
        outgoing = [edge for edge in rels_for_node if edge["source"] == selected_id]
        files = extract_file_mentions(
            entry.get("thought", ""),
            entry.get("action", ""),
            entry.get("result", ""),
        )

        _render_inspector_evidence_header(
            title=f"Step {step_index} · {kind_name}",
            subtitle=f"Detailed node {selected_id}",
            category=category,
            span=f"Step {step_index}",
            action_context=summarize_action(entry.get("action", "")),
            files=files,
            incoming_count=len(incoming),
            outgoing_count=len(outgoing),
            flagged_relations=_flagged_relation_labels(rels_for_node),
        )

        if rels_for_node:
            st.subheader("Relation Evidence")
            st.caption("Only relations attached to the selected node are shown here.")

            col_in, col_out = st.columns(2)
            with col_in:
                _render_relation_table("Incoming", incoming)
            with col_out:
                _render_relation_table("Outgoing", outgoing)

        st.subheader("Raw Log Evidence")
        st.caption("This is the raw log section for the selected node.")
        if node_kind == "T":
            st.markdown("**Thought**")
            wrapped_log_block(entry.get("thought", ""))
        elif node_kind == "A":
            st.markdown("**Action**")
            wrapped_log_block(entry.get("action", ""))
        elif node_kind == "R":
            st.markdown("**Result**")
            wrapped_log_block(entry.get("result", ""))
        return

    iteration_id = int(selected_id.replace("IT_", ""))
    iteration = iterations[iteration_id]
    rels_for_iteration = [
        edge
        for edge in edge_records
        if step_iteration.get(edge["src_step"]) == iteration_id
        or step_iteration.get(edge["dst_step"]) == iteration_id
    ]
    iteration_step_set = set(iteration["steps"])
    incoming_rels = []
    outgoing_rels = []

    for rel in rels_for_iteration:
        src_in_iteration = rel["src_step"] in iteration_step_set
        dst_in_iteration = rel["dst_step"] in iteration_step_set

        if dst_in_iteration and not src_in_iteration:
            incoming_rels.append(rel)
        elif src_in_iteration and not dst_in_iteration:
            outgoing_rels.append(rel)

    _render_inspector_evidence_header(
        title=f"Iteration {iteration_id}",
        subtitle=f"Collapsed node {selected_id}",
        category=iteration["category"],
        span=format_step_range(iteration["steps"]),
        action_context=iteration.get("action_summary", ""),
        files=iteration.get("files", []),
        incoming_count=len(incoming_rels),
        outgoing_count=len(outgoing_rels),
        flagged_relations=iteration.get("flagged_relations", [])
        or _flagged_relation_labels(rels_for_iteration),
    )

    if rels_for_iteration:
        st.subheader("Relation Evidence")
        st.caption("Only cross-iteration relations attached to this collapsed iteration are shown here.")
        col_prev, col_next = st.columns(2)
        with col_prev:
            _render_iteration_relation_table(
                "Incoming from other iterations",
                incoming_rels,
            )
        with col_next:
            _render_iteration_relation_table(
                "Outgoing to other iterations",
                outgoing_rels,
            )

    st.subheader("Raw Log Evidence")
    st.caption("Each section is one detailed step contained inside this collapsed iteration.")
    for step_index in iteration["steps"]:
        entry = log_data.get(step_index, {})
        _render_step_log_evidence(
            step_index=step_index,
            entry=entry,
            category=cat_map.get(step_index, ""),
            expanded=len(iteration["steps"]) <= 3,
        )
