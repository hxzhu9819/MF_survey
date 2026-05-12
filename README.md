# MF Patient Registry

Streamlit app for a YAML-driven mycosis fungoides (MF, 蕈样肉芽肿) patient questionnaire and registry.

This app is being prepared for beta usability and workflow testing. Do not collect identifiable real patient data until ethics review, consent, security, durable storage, and access control are ready.

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

By default, the local prototype stores submissions in:

```text
data/mf_registry.sqlite3
```

Override it with:

```bash
export MF_REGISTRY_SQLITE_PATH=/path/to/mf_registry.sqlite3
```

To use Supabase/Postgres instead, set a Postgres connection URL:

```bash
export MF_REGISTRY_DATABASE_URL="postgresql://..."
```

## Current Features

- Landing page for the pilot project.
- Patient resource library with FAQ, visit-preparation checklists, TNMB/mSWAT explanations, and curated external links.
- Participation explanation and consent gate.
- YAML-defined baseline questionnaire.
- Dynamic Streamlit rendering.
- Versioned questionnaire registration.
- Local SQLite persistence by default, with optional Supabase/Postgres persistence via `MF_REGISTRY_DATABASE_URL`.
- Optional long-term follow-up identity using hashed WeChat ID plus a participant-held retrieval key.
- Derived variables for diagnostic delay, BSA category, possible patient-reported stage group, severe itch, and treatment count.
- Researcher CSV export.
- Postgres/Supabase-oriented migration SQL in `migrations/001_init.sql`.

## Key Files

- `docs/engineering_doc.md`: research and engineering design.
- `docs/beta_launch_checklist.md`: beta readiness checklist.
- `docs/questionnaire_maintenance.md`: how to change YAML and add follow-up questionnaires.
- `docs/deployment_notes.md`: Streamlit/Supabase deployment notes.
- `docs/protocol_draft.md`: first protocol draft.
- `questionnaires/mf_baseline_2026_05_11.yaml`: baseline questionnaire.
- `questionnaires/mf_followup_3m_template.yaml`: draft 3-month follow-up questionnaire.
- `app.py`: Streamlit entry point.
- `mf_registry/`: schema parsing, rendering, storage, derived variables, export helpers.

## Free Deployment Path

For beta UI review:

1. Push this repo to GitHub.
2. Create a Streamlit Community Cloud app pointing to `app.py`.
3. Configure `MF_REGISTRY_ADMIN_PASSWORD`.
4. Configure `MF_REGISTRY_IDENTITY_PEPPER` before enabling long-term follow-up identity.
5. Use local SQLite only for dry runs and non-sensitive UI checks.

For beta data collection:

1. Create a managed Postgres project such as Supabase.
2. Copy the Postgres connection string into Streamlit secrets as `MF_REGISTRY_DATABASE_URL`.
3. Store admin password and pepper in Streamlit secrets, never in the repo.
4. Freeze questionnaire and consent versions before recruitment.
5. Test mainland China access from several networks before broad invitation.

## Follow-Up Identity

The prototype keeps follow-up identity separate from research answers.

- The participant may optionally enter a WeChat ID after explicit consent.
- The app normalizes the WeChat ID and creates an HMAC hash using `MF_REGISTRY_IDENTITY_PEPPER`.
- The raw WeChat ID is not stored and is not exported to CSV.
- The participant receives a `public_key` for research matching and a `retrieval_key` for future lookup.
- Only the hash of the retrieval key is stored, so the original retrieval key cannot be recovered by the research team.

Set a real pepper before enabling long-term follow-up identity:

```bash
export MF_REGISTRY_IDENTITY_PEPPER="long-random-secret"
```
