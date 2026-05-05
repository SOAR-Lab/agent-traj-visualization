"""Public entrypoint for the relationship-labeling page."""

from __future__ import annotations

import streamlit as st

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
    stage = st.session_state.get(LABELER_STAGE_STATE_KEY, "ingest")

    if stage == "annotating":
        render_annotating_screen()
        return
    if stage == "complete":
        render_summary_screen()
        return
    if stage == "workspace":
        render_workspace_page()
        return

    render_ingest_screen()
