# Evaluation Samples

These `.traj` files are 8-step SWE-agent trajectory windows selected for TraceView evaluation.
They are meant to keep labeling work reasonable while preserving realistic trajectory structure.

Selection signals are heuristic counts over each sampled window.

| Sample | Kind | Source task | Original steps | Signals |
| --- | --- | --- | --- | --- |
| django__django-10924__eval_01_localization.traj | localization | django__django-10924 | 6-13 | edits: 0, tests: 0, failures: 2, exploration: 8, files: 7, action_variety: 4 |
| pytest-dev__pytest-5692__eval_02_fix-and-test.traj | fix-and-test | pytest-dev__pytest-5692 | 26-33 | edits: 4, tests: 8, failures: 0, exploration: 0, files: 1, action_variety: 2 |
| pytest-dev__pytest-8906__eval_03_failure-recovery.traj | failure-recovery | pytest-dev__pytest-8906 | 20-27 | edits: 6, tests: 8, failures: 3, exploration: 0, files: 1, action_variety: 3 |
| pylint-dev__pylint-6506__eval_04_fix.traj | fix | pylint-dev__pylint-6506 | 36-43 | edits: 8, tests: 0, failures: 5, exploration: 0, files: 0, action_variety: 2 |
| sphinx-doc__sphinx-11445__eval_05_mixed.traj | mixed | sphinx-doc__sphinx-11445 | 38-45 | edits: 0, tests: 8, failures: 4, exploration: 0, files: 23, action_variety: 1 |

Use these files from the TraceView `Labeling` page by uploading one `.traj` file.
The original SWE-agent step index is preserved in each step's `extra_info.original_step_index`.
