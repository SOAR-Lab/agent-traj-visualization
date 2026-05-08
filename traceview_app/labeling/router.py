"""Public entrypoint for the relationship-labeling page."""

from __future__ import annotations

import streamlit as st

from traceview_app.shared.constants import (
    LABELER_STAGE_ANNOTATING,
    LABELER_STAGE_COMPLETE,
    LABELER_STAGE_INGEST,
    LABELER_STAGE_WORKSPACE,
)
from traceview_app.labeling.ingest_ui import (
    render_annotating_screen,
    render_ingest_screen,
)
from traceview_app.labeling.state import (
    LABELER_PASTE_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
)
from traceview_app.labeling.summary_ui import render_summary_screen
from traceview_app.labeling.workspace_ui import render_workspace_page


def render_labeling_page() -> None:
    st.session_state.setdefault(LABELER_PASTE_STATE_KEY, "")
    stage = st.session_state.get(LABELER_STAGE_STATE_KEY, LABELER_STAGE_INGEST)

    if stage == LABELER_STAGE_ANNOTATING:
        render_annotating_screen()
        return
    if stage == LABELER_STAGE_COMPLETE:
        render_summary_screen()
        return
    if stage == LABELER_STAGE_WORKSPACE:
        render_workspace_page()
        return

    render_ingest_screen()
