"""UI helpers for the relationship viewer."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from relationship_viewer_app.constants import (
    BAD_RELS,
    CATEGORY_COLOR,
    EDGE_FAMILY_OPTIONS,
    LOOPISH_RELS,
    STRUCTURAL_EDGE_OPTIONS,
)
from relationship_viewer_app.context import extract_file_mentions, summarize_action
from relationship_viewer_app.models import SidebarControls

INSPECTOR_PAGE_TOGGLE_KEY = "relationship_viewer_inspector_separate_page"
INSPECTOR_PAGE_TOGGLE_QUERY_KEY = "inspector_page"
OVERVIEW_SELECTED_FILE_KEY = "relationship_viewer_overview_selected_file"


def render_app_header(
    *,
    current_route: str,
    selected_task_id: str | None = None,
) -> str:
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container():
            st.title("Inspector" if current_route == "Inspector" else "Relationship Viewer")
            if current_route == "Inspector" and selected_task_id:
                st.caption(selected_task_id)
        st.space("stretch")
        if st.button(
            "Overview",
            type="primary" if current_route == "Overview" else "secondary",
            key="nav_overview",
        ):
            return "Overview"
        if st.button(
            "Analysis",
            type="primary" if current_route == "Analysis" else "secondary",
            key="nav_analysis",
        ):
            return "Analysis"

    st.divider()
    return current_route


def wrapped_log_block(text: str) -> None:
    text = text or "(empty)"
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    st.code(text, language=None, wrap_lines=True)


def _format_task_name(task_id: str) -> str:
    match = re.match(r"(.+)__(.+)-(\d+)$", task_id)
    if not match:
        return task_id
    owner, repo, issue = match.groups()
    return f"{repo} #{issue}"


def _compact_categories(categories: list[str], limit: int = 5) -> str:
    if not categories:
        return "none"

    grouped = []
    current = categories[0]
    count = 0
    for category in categories:
        if category == current:
            count += 1
            continue
        grouped.append((current, count))
        current = category
        count = 1
    grouped.append((current, count))

    parts = [
        f"{category} x{count}" if count > 1 else category
        for category, count in grouped[:limit]
    ]
    if len(grouped) > limit:
        parts.append("...")
    return " > ".join(parts)


def _format_flags(row: dict, limit: int = 4) -> str:
    flags = []
    if row.get("first_flagged_iteration") is not None:
        flags.append(f"first flagged: i{row['first_flagged_iteration']}")
    flags.extend(str(tag).lower() for tag in row.get("flagged_relations", []))
    return ", ".join(flags[:limit]) if flags else "none"


def _relation_counts_df(relation_counts: dict[str, int], limit: int = 8) -> pd.DataFrame:
    if not relation_counts:
        return pd.DataFrame(columns=["Relation", "Count"])

    sorted_counts = sorted(
        relation_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:limit]
    return pd.DataFrame(
        [{"Relation": relation, "Count": count} for relation, count in sorted_counts]
    )


def _overview_table_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Agent": row["agent_name"],
                "Outcome": row["outcome"],
                "Iterations": row["iteration_count"],
                "Task": _format_task_name(row["task_id"]),
                "Behavior": _compact_categories(row.get("categories", [])),
                "Tags": _format_flags(row),
            }
            for row in rows
        ]
    )


def _overview_summary_metrics(rows: list[dict]) -> None:
    total = len(rows)
    pass_count = sum(1 for row in rows if row["outcome"] == "pass")
    fail_count = sum(1 for row in rows if row["outcome"] == "fail")
    avg_iterations = (
        sum(int(row["iteration_count"]) for row in rows) / total if total else 0
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Runs", total)
    metric_cols[1].metric("Pass", pass_count)
    metric_cols[2].metric("Fail", fail_count)
    metric_cols[3].metric("Avg iterations", f"{avg_iterations:.1f}")


def render_overview_page(rows: list[dict]) -> str | None:
    if not rows:
        st.info("No task runs are available.")
        return None

    selected_filename = st.session_state.get(OVERVIEW_SELECTED_FILE_KEY)
    if selected_filename not in {row["filename"] for row in rows}:
        selected_filename = rows[0]["filename"]
        st.session_state[OVERVIEW_SELECTED_FILE_KEY] = selected_filename

    st.markdown("### Runs")
    _overview_summary_metrics(rows)

    tag_options = sorted(
        {
            tag.lower()
            for row in rows
            for tag in row.get("flagged_relations", [])
        }
    )

    filter_col, table_col, summary_col = st.columns([0.18, 0.56, 0.26], gap="large")

    with filter_col:
        with st.container(border=True):
            st.caption("FILTERS")
            outcome_filter = st.radio(
                "Outcome",
                ["all", "pass", "fail"],
                horizontal=False,
                label_visibility="visible",
            )
            selected_tags = st.multiselect("Tags", tag_options)
            search_text = st.text_input("Task search", placeholder="django, sympy, issue...")

    filtered_rows = rows
    if outcome_filter != "all":
        filtered_rows = [row for row in filtered_rows if row["outcome"] == outcome_filter]
    if selected_tags:
        selected_tag_set = set(selected_tags)
        filtered_rows = [
            row
            for row in filtered_rows
            if selected_tag_set.intersection(
                {tag.lower() for tag in row.get("flagged_relations", [])}
            )
        ]
    if search_text.strip():
        needle = search_text.strip().lower()
        filtered_rows = [
            row
            for row in filtered_rows
            if needle in row["task_id"].lower()
            or needle in _format_task_name(row["task_id"]).lower()
        ]

    if filtered_rows and selected_filename not in {row["filename"] for row in filtered_rows}:
        selected_filename = filtered_rows[0]["filename"]
        st.session_state[OVERVIEW_SELECTED_FILE_KEY] = selected_filename

    with table_col:
        st.caption("RUN INDEX")
        if not filtered_rows:
            st.warning("No runs match the current filters.")
        else:
            table_state = st.dataframe(
                _overview_table_df(filtered_rows),
                hide_index=True,
                use_container_width=True,
                height=min(560, 38 * len(filtered_rows) + 38),
                on_select="rerun",
                selection_mode="single-row",
                key="overview_run_table",
                column_config={
                    "Iterations": st.column_config.NumberColumn(
                        "IT",
                        help="Number of detailed iterations in the run.",
                    ),
                    "Behavior": st.column_config.TextColumn(
                        "Behavior",
                        help="Compressed sequence of action categories.",
                    ),
                },
            )
            selected_indices = table_state.selection.rows
            if selected_indices and selected_indices[0] < len(filtered_rows):
                selected_filename = filtered_rows[selected_indices[0]]["filename"]
                st.session_state[OVERVIEW_SELECTED_FILE_KEY] = selected_filename

    selected_row = next(
        (row for row in rows if row["filename"] == selected_filename),
        rows[0],
    )

    with summary_col:
        with st.container(border=True):
            st.caption("RUN SUMMARY")
            st.subheader(_format_task_name(selected_row["task_id"]))
            st.caption(selected_row["task_id"])
            metric_cols = st.columns(2)
            metric_cols[0].metric("Outcome", selected_row["outcome"].upper())
            metric_cols[1].metric("Iterations", selected_row["iteration_count"])
            st.markdown("**Behavior**")
            st.write(_compact_categories(selected_row.get("categories", []), limit=10))
            st.markdown("**Relations**")
            relation_counts_df = _relation_counts_df(
                selected_row.get("relation_counts", {})
            )
            if relation_counts_df.empty:
                st.caption("No labeled relations")
            else:
                st.dataframe(
                    relation_counts_df,
                    hide_index=True,
                    use_container_width=True,
                )
            st.markdown("**Flags**")
            st.write(_format_flags(selected_row, limit=6))
            if selected_row.get("bug_url"):
                st.link_button("Open bug report", selected_row["bug_url"], use_container_width=True)
            if st.button("Open analysis", type="primary", use_container_width=True):
                return selected_row["filename"]

    return None


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


def scroll_page_to_top() -> None:
    components.html(
        """
<script>
const scrollTop = () => {
  const doc = window.parent.document;
  window.parent.scrollTo(0, 0);
  [
    doc.scrollingElement,
    doc.documentElement,
    doc.body,
    doc.querySelector('[data-testid="stAppViewContainer"]'),
    doc.querySelector('[data-testid="stMain"]'),
    doc.querySelector('.stMain')
  ].filter(Boolean).forEach((el) => {
    el.scrollTop = 0;
    if (el.scrollTo) el.scrollTo(0, 0);
  });
};
setTimeout(scrollTop, 0);
setTimeout(scrollTop, 150);
setTimeout(scrollTop, 400);
</script>
        """,
        height=0,
    )


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


def patch_category_badge_color(category: str) -> str:
    normalized = category.strip().lower()
    if normalized == "resolved":
        return "green"
    if normalized in {"test_timeout", "test_errored", "no_apply", "no_generation"}:
        return "red"
    if normalized in {"applied", "generated"}:
        return "blue"
    if normalized in {"with_logs", "install_fail", "reset_failed"}:
        return "orange"
    return "gray"


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


def render_sidebar_controls(
    task_files: list[str],
    default_filename: str | None = None,
    default_controls: SidebarControls | None = None,
) -> tuple[str, SidebarControls]:
    st.sidebar.header("Dataset")
    selected_index = 0
    if default_filename in task_files:
        selected_index = task_files.index(default_filename)
    filename = st.sidebar.selectbox("Task file", task_files, index=selected_index)

    graph_mode_options = ["Detailed", "Iteration"]
    default_graph_mode = (
        default_controls.graph_mode
        if default_controls and default_controls.graph_mode in graph_mode_options
        else "Detailed"
    )
    graph_mode = st.sidebar.radio(
        "Graph mode",
        graph_mode_options,
        index=graph_mode_options.index(default_graph_mode),
        horizontal=True,
    )
    inspector_page_preference = (
        default_controls.inspector_separate_page
        if default_controls
        else get_inspector_page_preference()
    )

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
        default_edge_families = list(EDGE_FAMILY_OPTIONS)
        if default_controls:
            default_edge_families = [
                option
                for option in default_controls.selected_edge_families
                if option in EDGE_FAMILY_OPTIONS
            ]
        selected_edge_families = tuple(
            st.sidebar.pills(
                "Edge families",
                EDGE_FAMILY_OPTIONS,
                selection_mode="multi",
                default=default_edge_families,
                label_visibility="collapsed",
            )
        )

        default_structural_edges = list(STRUCTURAL_EDGE_OPTIONS)
        if default_controls:
            default_structural_edges = [
                option
                for option in default_controls.selected_structural_edges
                if option in STRUCTURAL_EDGE_OPTIONS
            ]
        selected_structural_edges = tuple(
            st.sidebar.pills(
                "Structural edges",
                STRUCTURAL_EDGE_OPTIONS,
                selection_mode="multi",
                default=default_structural_edges,
                label_visibility="collapsed",
            )
        )

    st.sidebar.header("Filters")
    show_only_bad = st.sidebar.checkbox(
        "Only bad relations",
        default_controls.show_only_bad if default_controls else False,
    )
    show_only_loopish = st.sidebar.checkbox(
        "Only loop-ish relations",
        default_controls.show_only_loopish if default_controls else False,
    )
    show_only_no_influence = st.sidebar.checkbox(
        "Only no-influence relations",
        default_controls.show_only_no_influence if default_controls else False,
    )

    st.sidebar.header("Layout")
    step_spacing = st.sidebar.slider(
        "Step spacing",
        120,
        320,
        default_controls.step_spacing if default_controls else 190,
        10,
    )
    lane_gap = st.sidebar.slider(
        "Lane gap",
        90,
        180,
        default_controls.lane_gap if default_controls else 120,
        10,
    )
    node_size = st.sidebar.slider(
        "Node size",
        18,
        46,
        default_controls.node_size if default_controls else 26,
        1,
    )
    label_max_len = st.sidebar.slider(
        "Max action label length",
        8,
        24,
        default_controls.label_max_len if default_controls else 14,
        1,
    )
    show_edge_labels = st.sidebar.checkbox(
        "Show edge labels",
        default_controls.show_edge_labels if default_controls else True,
    )

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
    st.caption("SELECTED RUN")
    title_col, action_col = st.columns([0.72, 0.28], vertical_alignment="center")

    with title_col:
        st.subheader(_format_task_name(task_id))
        st.caption(task_id)
    with action_col:
        if bug_url:
            st.link_button("Open bug report", bug_url, use_container_width=True)

    count_label = "Iterations" if graph_mode == "Iteration" else "Steps"
    count_value = iterations_count if graph_mode == "Iteration" else steps_count
    metric_cols = st.columns(3)
    metric_cols[0].metric("Graph mode", graph_mode)
    metric_cols[1].metric(count_label, count_value)
    metric_cols[2].metric("Patch result", format_patch_status_label(patch_status))

    if matched_patch_categories:
        st.caption("Patch result categories")
        with st.container(horizontal=True):
            for category in matched_patch_categories:
                st.badge(category, color=patch_category_badge_color(category))


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


def _format_step_range(steps: list[int]) -> str:
    if not steps:
        return ""
    if len(steps) == 1:
        return str(steps[0])
    return f"{steps[0]}-{steps[-1]}"


def _format_iteration_files(files: list[str], limit: int = 2) -> str:
    if not files:
        return "none"
    shown = files[:limit]
    label = ", ".join(shown)
    if len(files) > limit:
        label = f"{label} +{len(files) - limit}"
    return label


def _format_iteration_signals(iteration: dict) -> str:
    flagged = iteration.get("flagged_relations", [])
    if flagged:
        return ", ".join(flagged)
    relation_count = int(iteration.get("relation_count", 0))
    return f"{relation_count} relations" if relation_count else "none"


def _iteration_context_df(iterations: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Iteration": f"I{iteration['iteration_id']}",
                "Steps": _format_step_range(iteration["steps"]),
                "Category": iteration["category"],
                "Action context": iteration.get("action_summary") or "none",
                "Files": _format_iteration_files(iteration.get("files", [])),
                "Signals": _format_iteration_signals(iteration),
            }
            for iteration in iterations
        ]
    )


def render_iteration_context_panel(
    iterations: list[dict],
    *,
    show_heading: bool = True,
) -> None:
    if not iterations:
        return

    if show_heading:
        st.markdown("### Iteration Context")
    st.caption(
        "Collapsed iteration nodes are summarized from the reconstructed log: action, files mentioned, and relation signals."
    )
    st.table(_iteration_context_df(iterations).style.hide(axis="index"))


def _pretty_node_id(node_id: str) -> str:
    kind, step = node_id.split("_")
    kind_name = {"T": "Thought", "A": "Action", "R": "Result"}.get(kind, kind)
    return f"{kind_name} {step}"


def _relation_table_df(rels: list[dict], *, direction: str | None = None) -> pd.DataFrame:
    rows = []
    for rel in rels:
        row = {
            "Family": rel["family"].replace("_", " → ").title(),
            "Source": _pretty_node_id(rel["source"]),
            "Target": _pretty_node_id(rel["target"]),
            "Label": rel["relation"],
        }
        if direction:
            row = {"Direction": direction, **row}
        rows.append(row)
    return pd.DataFrame(rows)


def _iteration_relation_table_df(rels: list[dict], *, direction: str | None = None) -> pd.DataFrame:
    rows = []
    for rel in rels:
        row = {
            "Family": rel["family"].replace("_", " → ").title(),
            "Source step": rel["src_step"],
            "Target step": rel["dst_step"],
            "Label": rel["relation"],
        }
        if direction:
            row = {"Direction": direction, **row}
        rows.append(row)
    return pd.DataFrame(rows)


def _render_relation_table(title: str, rels: list[dict], *, direction: str | None = None) -> None:
    st.markdown(f"**{title}**")
    if not rels:
        st.caption("None")
        return
    st.table(_relation_table_df(rels, direction=direction).style.hide(axis="index"))


def _render_iteration_relation_table(
    title: str,
    rels: list[dict],
    *,
    direction: str | None = None,
) -> None:
    st.markdown(f"**{title}**")
    if not rels:
        st.caption("None")
        return
    st.table(_iteration_relation_table_df(rels, direction=direction).style.hide(axis="index"))


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
                _render_relation_table("Incoming", incoming, direction="Incoming")
            with col_out:
                _render_relation_table("Outgoing", outgoing, direction="Outgoing")

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
        span=_format_step_range(iteration["steps"]),
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
                direction="Incoming",
            )
        with col_next:
            _render_iteration_relation_table(
                "Outgoing to other iterations",
                outgoing_rels,
                direction="Outgoing",
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


def render_relationship_metrics(
    static_relation_records: list[dict],
    *,
    embedded: bool = False,
) -> None:
    if embedded:
        st.caption("Relation totals for the selected run.")
    else:
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
