# Deployment Notes

## Beta Target

The near-term beta target is:

- UI: Streamlit Community Cloud.
- Source control: GitHub repository.
- Data: start with local SQLite only for dry runs; move beta submissions to Supabase Postgres before inviting real participants.
- Secrets: Streamlit Community Cloud secrets or local `.streamlit/secrets.toml`, never committed.

## Streamlit Community Cloud

Recommended settings:

- App entry point: `app.py`
- Python dependencies: `requirements.txt`
- Python version: 3.12 (`runtime.txt` is included for reproducibility).
- Secrets:
  - `MF_REGISTRY_ADMIN_PASSWORD`
  - `MF_REGISTRY_IDENTITY_PEPPER`
  - `MF_REGISTRY_DATABASE_URL` for Supabase/Postgres-backed beta data collection

Community Cloud is free and GitHub-based, and app changes are deployed from repository updates. It is appropriate for early beta UI work, but local files on the app host should not be treated as durable research storage.

## Current Beta Deployment Steps

Use this for a small usability test with de-identified or intentionally fake data.

1. Push the project to a GitHub repository.
2. Open Streamlit Community Cloud and choose **Create app**.
3. Select the repository, branch, and `app.py` as the entry point.
4. In **Advanced settings**, paste Streamlit secrets:

```toml
MF_REGISTRY_ADMIN_PASSWORD = "replace-with-a-strong-password"
MF_REGISTRY_DATABASE_URL = "postgresql://postgres.PROJECT_REF:password@aws-0-region.pooler.supabase.com:6543/postgres"

# Optional. Set this only when you are ready to test long-term follow-up identity.
MF_REGISTRY_IDENTITY_PEPPER = "replace-with-a-long-random-secret"
```

5. Deploy, open the generated `streamlit.app` URL, and complete one full dry-run questionnaire.
6. Test the researcher export with the admin password.
7. Test the URL from mainland mobile data and broadband before sharing broadly.

For this exact version, keep the invitation language as **Beta usability test** unless a durable database and approved study workflow are in place.

## Mainland China Access

Streamlit Community Cloud may be slow or intermittently inaccessible from mainland China because it relies on global cloud infrastructure outside the mainland network. For beta:

1. Test the final `streamlit.app` URL from at least 3 mainland networks before inviting patients.
2. Avoid external blocked assets: no Google Fonts, Google Analytics, YouTube, reCAPTCHA, or third-party widgets.
3. Keep image assets lightweight and preferably local or stable CDN-hosted.
4. If access is unreliable, keep the same Streamlit app but deploy to a mainland-accessible provider or a Hong Kong/Singapore VPS with a custom domain.

## Supabase Setup

1. Create a free Postgres project.
2. Copy the project connection string. For hosted Streamlit, prefer Supabase's pooler URL because direct database connections may be unavailable from some environments.
3. Store the URL in Streamlit secrets as `MF_REGISTRY_DATABASE_URL`.
4. Deploy or restart the app. On startup, the app creates the required tables from `migrations/001_init.sql` if they do not already exist.
5. Complete one test questionnaire, test retrieval-key lookup if follow-up identity is enabled, and test researcher export/CSV download.
6. In Supabase, confirm the rows appear in `participants`, `survey_sessions`, `answers`, and `derived_variables`.

## Streamlit Secrets Example

Do not commit this file.

```toml
MF_REGISTRY_DATABASE_URL = "postgresql://..."
MF_REGISTRY_ADMIN_PASSWORD = "replace-this"
MF_REGISTRY_IDENTITY_PEPPER = "replace-with-long-random-secret"
```

## Database Sync Strategy

Use a staged migration rather than a risky all-at-once rewrite:

1. Local dry run: SQLite only.
2. Beta rehearsal: set `MF_REGISTRY_DATABASE_URL` locally or on a staging deployment and complete dry-run submissions.
3. Beta data collection: Supabase Postgres primary. Keep SQLite only for local development.
4. Follow-up phase: Supabase primary plus scheduled CSV backups.

The current schema already stores answers in append-friendly rows with `question_id`, `export_name`, `value`, and exact `questionnaire_version_id`, so adding or retiring questions does not require altering a wide answers table.

## Follow-Up Identity Operations

Recommended v1 workflow:

1. Ask for explicit optional consent for long-term follow-up identity.
2. Accept WeChat ID only in the dedicated follow-up identity box, not in free-text research answers.
3. Generate `public_key` from HMAC-normalized WeChat ID.
4. Generate a random `retrieval_key` and show it once to the participant.
5. Store `contact_hash`, `public_key`, and `retrieval_key_hash`; do not store raw WeChat ID.
6. Use `retrieval_key` for future participant lookup.
7. Keep follow-up identity tables out of analysis exports by default.

If the pepper is lost, existing WeChat hashes and retrieval keys cannot be re-derived. Back it up like production credentials.
