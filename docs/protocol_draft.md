# Protocol Draft: Chinese-Language Patient-Reported MF Registry

Last updated: 2026-05-11

## Working Title

Patient-reported diagnostic journey, treatment patterns, and symptom burden in a Chinese-language mycosis fungoides cohort.

## Study Type

Observational patient-reported registry with a cross-sectional baseline survey and optional longitudinal follow-up every 3 months.

## Rationale

Mycosis fungoides (MF) is a rare cutaneous T-cell lymphoma with frequent diagnostic delay, heterogeneous clinical presentations, and substantial symptom and quality-of-life burden. Chinese-language patient-reported data are limited. A structured registry can describe diagnostic pathways, real-world treatment patterns, access barriers, and patient-prioritized research questions.

## Objectives

Primary objective:

- Describe diagnostic delay, treatment patterns, and current symptom burden in a Chinese-language MF patient cohort.

Secondary objectives:

- Identify patient-reported factors associated with longer diagnostic delay.
- Identify factors associated with severe itch and sleep disturbance.
- Describe access barriers, including travel time, expert-center access, and cost burden.
- Assess feasibility of repeated patient-reported follow-up.

## Population

Target sample:

- Initial baseline cohort: approximately 300 participants.
- Pilot usability test: 10-20 participants using de-identified or test data.

Inclusion criteria for research phase:

- Age 18 years or older.
- Self-reported physician diagnosis of MF or CTCL, or suspected MF subgroup if explicitly analyzed separately.
- Able to read Chinese and complete an online questionnaire.
- Provides informed consent.

Exclusion criteria:

- Under 18 years old in v1.
- Unable to provide informed consent.
- Duplicate submission that cannot be reconciled.
- Submission with clear non-MF diagnosis unless retained as a separate "suspected/non-eligible" group.

## Data Sources

Patient-reported online questionnaire:

- Demographics.
- Diagnosis timeline.
- Disease phenotype and approximate BSA.
- Pathology and laboratory result summaries.
- Treatment history.
- Symptoms and burden.
- Care access and costs.
- Patient-prioritized research questions.

Optional future data sources:

- Medical-report upload after explicit consent.
- Physician verification of stage/pathology in a subset.
- Follow-up questionnaires every 3 months.

## Outcomes

Primary descriptive outcomes:

- Diagnostic delay in months: first symptom to confirmed diagnosis.
- Time to first biopsy.
- Number of biopsies before diagnosis.
- Treatment classes ever used.
- Current itch, sleep disturbance, pain/burning, fatigue.
- Current and worst-ever BSA category.

Secondary outcomes:

- Possible patient-reported stage group.
- Severe itch, defined as itch NRS >= 7.
- High sleep disturbance, defined as sleep impact NRS >= 7.
- Expert-center access.
- Cost burden NRS.
- Willingness for longitudinal follow-up.

## Analysis Plan

Descriptive analysis:

- Summarize baseline characteristics with counts, percentages, median, IQR, and missingness.
- Report diagnosis timeline and treatment frequencies.
- Report symptoms overall and by possible patient-reported stage group.

Association analyses:

- Diagnostic delay: compare delay by sex, age group, region/city tier, initial misdiagnosis, first biopsy timing, and phenotype features.
- Severe itch: model association with BSA category, lesion types, possible stage group, treatment count, sleep disturbance, and cost burden.
- Access burden: describe travel and cost burden by region/city tier and expert-center access.

Modeling constraints:

- Keep models small because N is expected to be ~300.
- Clearly separate patient-reported variables from clinician-verified variables.
- Avoid causal treatment-effect claims in baseline data.

Longitudinal analysis after follow-up:

- Within-person change in itch, sleep, BSA category, and treatment status.
- Mixed-effects models only if follow-up completeness is sufficient.

## Data Quality

Planned checks:

- Missing required consent/eligibility fields.
- Impossible dates, such as diagnosis before symptom onset.
- Duplicate-like submissions.
- Inconsistent staging signals, such as erythroderma with very low BSA.
- Free-text review for accidental direct identifiers before analysis export.

## Ethics and Privacy

The research phase involves sensitive health information. Before collecting identifiable or publication-intended real patient data, the team should obtain ethics review or partner with an institution that can provide ethical oversight.

Participant protections:

- Voluntary participation.
- Ability to withdraw.
- Minimum necessary data collection.
- No national ID, real name, exact address, or direct contact fields in the first prototype.
- Contact/follow-up identity information stored separately from survey answers.
- Optional WeChat-based follow-up identity stored only as HMAC hashes; raw WeChat ID is not stored or exported.
- Retrieval key shown to participant and stored only as a hash.
- Aggregate reporting only.

## Current Prototype Limits

- The Streamlit admin/export page has no authentication.
- Local SQLite is for testing only.
- Medical report and photo upload are intentionally disabled.
- No clinician verification workflow yet.
- No reminder or resume workflow yet.
- Follow-up identity lookup exists as a technical prototype, but operational policy and withdrawal handling still need formal review.
