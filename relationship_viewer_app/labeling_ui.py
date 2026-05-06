"""Public entrypoint for the relationship-labeling page."""

from __future__ import annotations

import streamlit as st

from relationship_viewer_app.constants import (
    LABELER_STAGE_ANNOTATING,
    LABELER_STAGE_COMPLETE,
    LABELER_STAGE_INGEST,
    LABELER_STAGE_WORKSPACE,
)
from relationship_viewer_app.labeling_ingest import (
    render_annotating_screen,
    render_ingest_screen,
)
from relationship_viewer_app.labeling_state import (
    LABELER_PASTE_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
)
from relationship_viewer_app.labeling_summary import render_summary_screen
from relationship_viewer_app.labeling_workspace import render_workspace_page


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
