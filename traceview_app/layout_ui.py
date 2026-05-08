"""Shared app chrome and legacy UI exports."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from traceview_app.analysis.inspector_ui import render_inspector
from traceview_app.analysis.iteration_ui import render_iteration_context_panel
from traceview_app.analysis.route import (
    action_category_legend,
    format_patch_status_label,
    patch_category_badge_color,
    relation_legend,
    render_graph_guide,
    render_patch_overview,
    render_relationship_metrics,
    render_shared_legend,
)
from traceview_app.analysis.sidebar_ui import (
    INSPECTOR_PAGE_TOGGLE_KEY,
    INSPECTOR_PAGE_TOGGLE_QUERY_KEY,
    get_inspector_page_preference,
    render_sidebar_controls,
    set_inspector_page_preference,
)
from traceview_app.labeling.router import render_labeling_page
from traceview_app.overview.ui import render_overview_page
from traceview_app.shared.constants import (
    ROUTE_ANALYSIS,
    ROUTE_INSPECTOR,
    ROUTE_LABELING,
    ROUTE_OVERVIEW,
)


def render_app_header(
    *,
    current_route: str,
    selected_task_id: str | None = None,
) -> tuple[str, bool]:
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container():
            st.title("TraceView Inspector" if current_route == ROUTE_INSPECTOR else "TraceView")
            if current_route == ROUTE_INSPECTOR and selected_task_id:
                st.caption(selected_task_id)
        st.space("stretch")
        if st.button(
            ROUTE_LABELING,
            type="primary" if current_route == ROUTE_LABELING else "secondary",
            key="nav_labeling",
        ):
            return ROUTE_LABELING, True
        if st.button(
            ROUTE_OVERVIEW,
            type="primary" if current_route == ROUTE_OVERVIEW else "secondary",
            key="nav_overview",
        ):
            return ROUTE_OVERVIEW, True
        if st.button(
            ROUTE_ANALYSIS,
            type="primary" if current_route == ROUTE_ANALYSIS else "secondary",
            key="nav_analysis",
        ):
            return ROUTE_ANALYSIS, True

    st.divider()
    return current_route, False


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
