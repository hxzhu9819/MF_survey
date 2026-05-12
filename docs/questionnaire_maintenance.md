# Questionnaire Maintenance

## Design Rule

Questionnaire content lives in YAML. Rendering, storage, and export code should remain generic unless a new question type is truly needed.

## How To Modify A Questionnaire

1. Copy the current YAML or edit it directly during beta.
2. Bump `questionnaire.version`.
3. Keep old `id` and `export_name` values stable for questions whose meaning has not changed.
4. Add new questions with new `id` and `export_name`.
5. Do not reuse an old `export_name` for a different concept.
6. Mark removed questions as absent in the new YAML; old submissions remain linked to the old questionnaire version.
7. Run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/mf_pycache .venv/bin/python -m compileall app.py mf_registry tests
.venv/bin/python -c "from pathlib import Path; from mf_registry.questionnaire_schema import load_questionnaire; print(load_questionnaire(Path('questionnaires/mf_baseline_2026_05_11.yaml')).version)"
```

## Adding A New Question Type

Only add a new renderer when existing types cannot express the question.

Files to update:

- `mf_registry/questionnaire_schema.py`: add the type to `SUPPORTED_TYPES`.
- `mf_registry/renderer_streamlit.py`: render the widget and sync its state in `sync_answers_from_widgets`.
- `tests/test_questionnaire_schema.py`: add at least one schema or derived-variable test.

## Follow-Up Questionnaires

Recommended pattern:

- Keep baseline YAML as `questionnaires/mf_baseline_*.yaml`.
- Add follow-up YAML as `questionnaires/mf_followup_3m_*.yaml`.
- Use the same participant identity tables.
- Save follow-up sessions with a distinct `questionnaire_id`, for example `mf_followup_3m`.
- Reuse stable export names for repeated concepts such as itch, sleep, current BSA, treatment changes, and disease status.

Follow-up modules should be shorter:

- Current skin burden and mSWAT-like fields.
- Current symptoms: itch, sleep, pain/burning, fatigue.
- Treatment changes since last questionnaire.
- New biopsy, blood, imaging, or staging updates.
- Care access and cost changes.
- Patient-priority free text.

## Data Analysis Principle

Exports should keep raw answers and derived variables separate. Derived variables can change as the analysis plan improves; raw answers and questionnaire YAML should remain immutable for each submission.
