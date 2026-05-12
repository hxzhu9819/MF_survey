# Beta Launch Checklist

## Product Readiness

- Patient-facing pages say Beta/patient co-research, not development or local testing.
- Required questions are limited to true eligibility and consent needs.
- Each chapter has an intro explaining why the questions are asked.
- The progress map supports jumping between chapters.
- Submit page clearly says whether answers can be modified.
- Retrieval key instructions are visible only when long-term identity is enabled.

## Data Safety

- No raw name, phone, ID number, exact address, hospital record number, or report upload is requested.
- Free-text prompts explicitly discourage identifiable details.
- `MF_REGISTRY_IDENTITY_PEPPER` is configured before enabling WeChat follow-up identity.
- `MF_REGISTRY_ADMIN_PASSWORD` is configured before deployment.
- Researcher export is password-gated.
- Admin password and pepper are stored in Streamlit secrets, not Git.

## Database

- Dry run can use SQLite.
- Real beta submissions should use Supabase Postgres or another durable Postgres service.
- `migrations/001_init.sql` has been run in the remote database.
- A backup workflow is defined before recruitment.
- Export has been tested with at least one complete and one incomplete questionnaire.

## Mainland China Access

- Test the deployed URL from mainland mobile data and home broadband.
- If `streamlit.app` is slow or unreachable, switch hosting before broad invitation.
- Avoid Google-hosted assets and analytics.
- Keep the first load small.

## Before Inviting Patients

- Freeze the questionnaire version.
- Freeze the participation text shown in the expander.
- Keep a copy of the exact YAML and app commit hash used for the beta.
- Prepare a short WeChat invitation message that explains this is not medical advice.
- Prepare a feedback channel for wording problems, confusing questions, and access issues.
