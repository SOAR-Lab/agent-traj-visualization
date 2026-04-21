"""UI helpers for the relationship viewer."""

from __future__ import annotations

import re

import streamlit as st

from relationship_viewer_app.constants import (
    CATEGORY_COLOR,
    EDGE_FAMILY_OPTIONS,
    STRUCTURAL_EDGE_OPTIONS,
)
from relationship_viewer_app.models import SidebarControls

INSPECTOR_PAGE_TOGGLE_KEY = "relationship_viewer_inspector_separate_page"
INSPECTOR_PAGE_TOGGLE_QUERY_KEY = "inspector_page"


def wrapped_log_block(text: str) -> None:
    text = text or "(empty)"
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    st.code(text, language=None, wrap_lines=True)


def action_category_legend(title: str = "#### Action Categories") -> None:
    st.markdown(title)

    items = [
        ("Explore", CATEGORY_COLOR["explore"]),
        ("Locate", CATEGORY_COLOR["locate"]),
        ("Search", CATEGORY_COLOR["search"]),
        ("Reproduce", CATEGORY_COLOR["reproduce"]),
        ("Generate fix", CATEGORY_COLOR["generate fix"]),
        ("Run tests", CATEGORY_COLOR["run tests"]),
        ("Refactor", CATEGORY_COLOR["refactor"]),
        ("Explain", CATEGORY_COLOR["explain"]),
    ]

    cols = st.columns(4)
    for index, (label, color) in enumerate(items):
        with cols[index % 4]:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <div style="width:14px;height:14px;border-radius:50%;background:{color};border:1px solid #444;"></div>
                    <div>{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def relation_legend(title: str = "#### Edge Types") -> None:
    items = [
        ("Good flow", "#54A24B"),
        ("Shift / divergence", "#F58518"),
        ("Loop-ish", "#7F3C8D"),
        ("Bad", "#E45756"),
        ("No influence", "#9E9E9E"),
        ("Structural", "#D0D0D0"),
    ]
    st.markdown(title)
    cols = st.columns(3)
    for index, (label, color) in enumerate(items):
        with cols[index % 3]:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <div style="width:18px;height:4px;background:{color};border-radius:3px;"></div>
                    <div>{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_shared_legend() -> None:
    st.markdown("### Legend")
    st.caption("Node color shows action category. Edge color shows relation type in both modes.")

    col_left, col_right = st.columns([1.35, 1.0])

    with col_left:
        action_category_legend()

    with col_right:
        relation_legend()


def hide_sidebar_chrome() -> None:
    st.markdown(
        """
<style>
section[data-testid="stSidebar"] {
    display: none !important;
}
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}
[data-testid="collapsedControl"] {
    display: none !important;
}
button[kind="header"][aria-label="Open sidebar"] {
    display: none !important;
}
button[kind="header"][aria-label="Close sidebar"] {
    display: none !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_inspector_page_header(
    *,
    task_id: str,
) -> bool:
    title_col, button_col = st.columns([0.82, 0.18], vertical_alignment="top")
    with title_col:
        st.caption(task_id)
        st.title("Inspector")
    with button_col:
        back_pressed = st.button("Back to graph", use_container_width=True)

    st.divider()

    return back_pressed


def format_patch_status_label(primary_status: str) -> str:
    pretty = {
        "RESOLVED": "RESOLVED",
        "PATCH NOT APPLIED": "NO APPLY",
        "TEST ERRORED": "TEST ERRORED",
        "TEST TIMEOUT": "TEST TIMEOUT",
        "NO GENERATION": "NO GENERATION",
        "INSTALL FAIL": "INSTALL FAIL",
        "RESET FAILED": "RESET FAILED",
        "APPLIED": "APPLIED",
        "GENERATED": "GENERATED",
        "HAS LOGS": "HAS LOGS",
        "UNKNOWN": "UNKNOWN",
    }
    shown = pretty.get(primary_status, primary_status)
    if primary_status == "RESOLVED":
        return f"PASS ({shown})"
    return f"FAIL ({shown})"


def _query_param_to_bool(value: object) -> bool:
    if isinstance(value, list):
        value = value[-1] if value else None
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_inspector_page_preference() -> bool:
    if INSPECTOR_PAGE_TOGGLE_KEY in st.session_state:
        return bool(st.session_state[INSPECTOR_PAGE_TOGGLE_KEY])
    return _query_param_to_bool(st.query_params.get(INSPECTOR_PAGE_TOGGLE_QUERY_KEY))


def set_inspector_page_preference(value: bool) -> None:
    st.session_state[INSPECTOR_PAGE_TOGGLE_KEY] = value
    if value:
        st.query_params[INSPECTOR_PAGE_TOGGLE_QUERY_KEY] = "1"
        return
    if INSPECTOR_PAGE_TOGGLE_QUERY_KEY in st.query_params:
        del st.query_params[INSPECTOR_PAGE_TOGGLE_QUERY_KEY]


def render_sidebar_controls(task_files: list[str]) -> tuple[str, SidebarControls]:
    st.sidebar.header("Dataset")
    filename = st.sidebar.selectbox("Task file", task_files)

    graph_mode = st.sidebar.radio(
        "Graph mode",
        ["Detailed", "Iteration"],
        horizontal=True,
    )
    inspector_page_preference = get_inspector_page_preference()

    inspector_separate_page = st.sidebar.toggle(
        "Open inspector on separate page",
        value=inspector_page_preference,
    )
    if inspector_separate_page != inspector_page_preference:
        set_inspector_page_preference(inspector_separate_page)
    else:
        st.session_state[INSPECTOR_PAGE_TOGGLE_KEY] = inspector_separate_page

    selected_edge_families = tuple(EDGE_FAMILY_OPTIONS)
    selected_structural_edges = tuple(STRUCTURAL_EDGE_OPTIONS)

    if graph_mode == "Detailed":
        st.sidebar.header("Relational Edges")
        selected_edge_families = tuple(
            st.sidebar.pills(
                "Edge families",
                EDGE_FAMILY_OPTIONS,
                selection_mode="multi",
                default=list(EDGE_FAMILY_OPTIONS),
                label_visibility="collapsed",
            )
        )

        selected_structural_edges = tuple(
            st.sidebar.pills(
                "Structural edges",
                STRUCTURAL_EDGE_OPTIONS,
                selection_mode="multi",
                default=list(STRUCTURAL_EDGE_OPTIONS),
                label_visibility="collapsed",
            )
        )

    st.sidebar.header("Filters")
    show_only_bad = st.sidebar.checkbox("Only bad relations", False)
    show_only_loopish = st.sidebar.checkbox("Only loop-ish relations", False)
    show_only_no_influence = st.sidebar.checkbox("Only no-influence relations", False)

    st.sidebar.header("Layout")
    step_spacing = st.sidebar.slider("Step spacing", 120, 320, 190, 10)
    lane_gap = st.sidebar.slider("Lane gap", 90, 180, 120, 10)
    node_size = st.sidebar.slider("Node size", 18, 46, 26, 1)
    label_max_len = st.sidebar.slider("Max action label length", 8, 24, 14, 1)
    show_edge_labels = st.sidebar.checkbox("Show edge labels", True)

    controls = SidebarControls(
        graph_mode=graph_mode,
        inspector_separate_page=inspector_separate_page,
        selected_edge_families=selected_edge_families,
        selected_structural_edges=selected_structural_edges,
        show_only_bad=show_only_bad,
        show_only_loopish=show_only_loopish,
        show_only_no_influence=show_only_no_influence,
        step_spacing=step_spacing,
        lane_gap=lane_gap,
        node_size=node_size,
        label_max_len=label_max_len,
        show_edge_labels=show_edge_labels,
    )
    return filename, controls


def render_patch_overview(
    *,
    task_id: str,
    bug_url: str | None,
    graph_mode: str,
    iterations_count: int,
    steps_count: int,
    patch_status: str,
    matched_patch_categories: list[str],
) -> None:
    st.markdown("### Report → Patch Overview")
    col1, col2, col3 = st.columns([0.55, 0.1, 0.35])

    with col1:
        st.metric("Bug report", task_id)
        if bug_url:
            st.link_button("Open bug report", bug_url)
    with col2:
        if graph_mode == "Iteration":
            st.metric("Iterations", iterations_count)
        else:
            st.metric("Iterations", steps_count)
    with col3:
        st.metric("Patch result", format_patch_status_label(patch_status))

    if matched_patch_categories:
        st.markdown("**All matched patch result categories**")
        badge_html = " ".join(
            f'<span style="display:inline-block;padding:4px 10px;margin:2px;border-radius:12px;background:#eee;border:1px solid #ccc;">{category}</span>'
            for category in matched_patch_categories
        )
        st.markdown(badge_html, unsafe_allow_html=True)


def render_graph_guide(graph_mode: str) -> None:
    if graph_mode == "Detailed":
        st.markdown(
            """
### How to read this graph

Detailed mode shows one `T → A → R` triplet per step.
Read the graph left to right across iterations, then click any node to inspect that step and its attached relations.
"""
        )
        return

    st.markdown(
        """
### How to read this graph

Iteration mode collapses consecutive detailed steps with the same action category into iteration nodes like `I7`.
Clicking a node opens the grouped content and cross-iteration relations.
"""
    )


def _pretty_node_id(node_id: str) -> str:
    kind, step = node_id.split("_")
    kind_name = {"T": "Thought", "A": "Action", "R": "Result"}.get(kind, kind)
    return f"{kind_name} {step}"


def _render_relation_list(title: str, rels: list[dict]) -> None:
    st.markdown(f"**{title}**")
    if not rels:
        st.write("None")
        return

    grouped: dict[str, list[dict]] = {}
    for rel in rels:
        grouped.setdefault(rel["family"], []).append(rel)

    for family, family_rels in grouped.items():
        pretty_family = family.replace("_", " → ").title()
        st.markdown(
            f"<span style='color:#666'>{pretty_family}</span>",
            unsafe_allow_html=True,
        )
        for rel in family_rels:
            st.markdown(
                f"- {_pretty_node_id(rel['source'])} → {_pretty_node_id(rel['target'])} : **{rel['relation']}**"
            )


def _render_relation_column(title: str, rels: list[dict]) -> None:
    st.markdown(f"### {title}")
    if not rels:
        st.write("None")
        return

    grouped: dict[str, list[dict]] = {}
    for rel in rels:
        grouped.setdefault(rel["family"], []).append(rel)

    for family, family_rels in grouped.items():
        pretty_family = family.replace("_", " → ").title()
        st.markdown(f"**{pretty_family}**")
        for rel in family_rels:
            st.markdown(
                f"- Step {rel['src_step']} → Step {rel['dst_step']} : **{rel['relation']}**"
            )


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
        st.subheader(f"Step {step_index} · {kind_name}")
        if category:
            st.write("Action category:", category)

        rels_for_node = [
            edge
            for edge in edge_records
            if edge["source"] == selected_id or edge["target"] == selected_id
        ]

        if rels_for_node:
            st.markdown("### Relations touching this node")

            incoming = [edge for edge in rels_for_node if edge["target"] == selected_id]
            outgoing = [edge for edge in rels_for_node if edge["source"] == selected_id]

            col_in, col_out = st.columns(2)
            with col_in:
                _render_relation_list("Incoming", incoming)
            with col_out:
                _render_relation_list("Outgoing", outgoing)

        st.subheader("Selected Node Content")
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
    st.subheader(f"Iteration {iteration_id}")
    st.write("Category: ", iteration["category"])

    rels_for_iteration = [
        edge
        for edge in edge_records
        if step_iteration.get(edge["src_step"]) == iteration_id
        or step_iteration.get(edge["dst_step"]) == iteration_id
    ]

    if rels_for_iteration:
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

        col_prev, col_next = st.columns(2)
        with col_prev:
            _render_relation_column("Previous Iteration Relations", incoming_rels)
        with col_next:
            _render_relation_column("Next Iteration Relations", outgoing_rels)

    st.subheader("Iteration Content")
    for step_index in iteration["steps"]:
        entry = log_data.get(step_index, {})
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


def render_relationship_metrics(static_relation_records: list[dict]) -> None:
    st.markdown("---")
    st.header("Relationship Metrics")

    if not static_relation_records:
        st.write("No relation data available for this task.")
        return

    relation_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}

    for edge in static_relation_records:
        relation_counts[edge["relation"]] = relation_counts.get(edge["relation"], 0) + 1
        family_counts[edge["family"]] = family_counts.get(edge["family"], 0) + 1

    total = sum(relation_counts.values())
    st.metric("Total labeled relations", total)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**By relationship**")
        for relation, count in sorted(
            relation_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            st.write(f"- {relation}: {count} ({count / total:.1%})")

    with col_b:
        st.markdown("**By edge family**")
        for family, count in sorted(
            family_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            st.write(f"- {family}: {count}")
