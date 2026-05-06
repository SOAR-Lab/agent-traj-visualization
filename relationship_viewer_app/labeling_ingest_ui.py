"""Ingest and progress screens for relationship labeling."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from relationship_viewer_app.constants import (
    LABELER_STAGE_COMPLETE,
    LABELER_STAGE_INGEST,
)
from relationship_viewer_app.labeling_common_ui import (
    render_labeling_header,
    render_parser_warnings,
)
from relationship_viewer_app.labeling_state import (
    LABELER_ERRORS_STATE_KEY,
    LABELER_PASTE_STATE_KEY,
    LABELER_PROGRESS_ADVANCED_STATE_KEY,
    LABELER_STAGE_STATE_KEY,
    LABELER_UPLOAD_SIGNATURE_STATE_KEY,
    TRACE_UPLOAD_TYPES,
    active_source_meta,
    annotation_stats,
    format_size,
    labels,
    selected_trajectory,
    start_annotation_from_local_folder,
    start_annotation_from_sources,
)
from relationship_viewer_app.trajectory_parser import LOCAL_SWEAGENT_TRAJECTORY_DIR


def render_ingest_screen() -> None:
    render_labeling_header("INGEST RAW TRACE", "Paste or upload a raw agent trace.")

    upload_tab, paste_tab, local_tab = st.tabs(["Upload", "Paste", "Local folder"])
    with upload_tab:
        uploaded_files = st.file_uploader(
            "Drop files here",
            type=TRACE_UPLOAD_TYPES,
            accept_multiple_files=True,
            help=".jsonl, .json, .traj, .log, .txt, or .zip up to 25 MB",
        )
        if uploaded_files:
            sources = [
                (uploaded_file.name, uploaded_file.getvalue())
                for uploaded_file in uploaded_files
            ]
            upload_signature = tuple((name, len(contents)) for name, contents in sources)
            if upload_signature != st.session_state.get(LABELER_UPLOAD_SIGNATURE_STATE_KEY):
                st.session_state[LABELER_UPLOAD_SIGNATURE_STATE_KEY] = upload_signature
                if start_annotation_from_sources(sources):
                    st.rerun()

    with paste_tab:
        pasted_trace = st.text_area(
            "Raw trace",
            key=LABELER_PASTE_STATE_KEY,
            height=220,
            placeholder="Paste raw trace text here.",
        )
        if st.button(
            "Annotate pasted trace",
            type="primary",
            width="stretch",
            disabled=not pasted_trace.strip(),
        ):
            sources = [("pasted-trace.txt", pasted_trace.encode("utf-8"))]
            if start_annotation_from_sources(sources):
                st.rerun()

    with local_tab:
        if LOCAL_SWEAGENT_TRAJECTORY_DIR.exists():
            st.caption(str(LOCAL_SWEAGENT_TRAJECTORY_DIR))
            if st.button("Load local SWE-agent folder", width="stretch"):
                if start_annotation_from_local_folder():
                    st.rerun()
        else:
            st.info("No local SWE-agent trajectory folder found.")

    render_parser_warnings(
        st.session_state.get(LABELER_ERRORS_STATE_KEY, []),
        expanded=True,
    )


def render_annotating_screen() -> None:
    trajectory = selected_trajectory()
    if trajectory is None:
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_INGEST
        st.rerun()

    meta = active_source_meta()
    size_label = format_size(meta.get("bytes") if isinstance(meta.get("bytes"), int) else None)
    uploaded_meta = f"{size_label} - uploaded just now" if size_label else "uploaded just now"
    render_labeling_header(
        "ANNOTATING",
        str(meta.get("name") or trajectory.source_name),
        uploaded_meta,
    )

    stats = annotation_stats(trajectory, labels())
    progress = 0.68
    st.progress(progress, text=f"Progress {round(progress * 100)}%")

    progress_rows = pd.DataFrame(
        [
            {
                "Task": "Parsing raw trace",
                "Status": "done",
                "Detail": (
                    f"Found {len(trajectory.steps)} iterations, "
                    f"{len(trajectory.steps) * 3} turns"
                ),
            },
            {
                "Task": "Classifying node types",
                "Status": "done",
                "Detail": (
                    f"{len(trajectory.steps)} thoughts, "
                    f"{len(trajectory.steps)} actions, "
                    f"{len(trajectory.steps)} results"
                ),
            },
            {
                "Task": "Labeling relationships",
                "Status": "running",
                "Detail": f"{stats.labeled_count} of {stats.candidate_count} edges labeled",
            },
        ]
    )

    with st.container(border=True):
        st.dataframe(progress_rows, hide_index=True, width="stretch")
        if st.button("Cancel"):
            st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_INGEST
            st.rerun()

    if not st.session_state.get(LABELER_PROGRESS_ADVANCED_STATE_KEY, False):
        st.session_state[LABELER_PROGRESS_ADVANCED_STATE_KEY] = True
        time.sleep(0.8)
        st.session_state[LABELER_STAGE_STATE_KEY] = LABELER_STAGE_COMPLETE
        st.rerun()
