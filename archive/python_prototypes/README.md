## Python Prototype Archive

`relationship_viewer.py` is the current app.
Root-level JSON files were moved to `data/json/`.

Large raw input folders used by some archived scripts are not included in the current repo checkout. The AXE prototypes expect a local `AXE_logs/` folder, and the SWE-agent parser expects a local `sweagent_claude4_trajs/` folder. Restore those folders locally only if you need to run those archived scripts.

Archived prototypes:

- `v0_pycharm_stub.py`: original PyCharm starter file.
- `v0_axe_log_key_probe.py`: quick schema probe for AXE JSONL logs.
- `v1_axe_trace_normalizer.py`: normalizes AXE traces into graph/context JSON under `data/json/`.
- `v1_axe_trace_viewer.py`: first Streamlit viewer for the AXE-normalized output.
- `v2_sweagent_trajectory_parser.py`: parser for SWE-agent trajectory files into `data/json/agraph_graph.json`.
- `v2_sweagent_timeline_viewer.py`: second Streamlit viewer for the `agraph_graph.json` timeline.

Run the current app from the project root with:

```powershell
streamlit run relationship_viewer.py
```
