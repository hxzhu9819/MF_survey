# MF Patient Registry and Questionnaire System Engineering Doc

Last updated: 2026-05-11

## 1. Goal

Build a low-cost, versioned online questionnaire and registry for ~300 people with mycosis fungoides (MF, 蕈样肉芽肿), starting as a patient-facing pilot and evolving into a research-grade longitudinal cohort.

The scientific goal is not only to collect "300 forms", but to create a reusable dataset that can answer questions under-represented in current MF literature: diagnostic delay, patient journey, real-world treatment patterns, symptom burden, quality of life, access to expert care, and longitudinal change.

This document is not medical advice or an ethics approval document. Because the project collects health information from humans, publication-oriented research should involve a dermatologist/hematologist familiar with CTCL, a statistician, and an ethics/IRB route before real identifiable patient data are collected.

## 2. Current MF Research Context

MF is the most common cutaneous T-cell lymphoma (CTCL). Diagnosis usually requires integration of clinical appearance, histopathology, immunophenotype, and sometimes T-cell receptor clonality. Early disease is often indolent and skin-limited, but diagnosis is difficult because it can mimic eczema, psoriasis, dermatitis, hypopigmented disorders, folliculitis, and other chronic inflammatory dermatoses.

Key current themes from recent literature and guidelines:

- Staging remains central: TNMB staging captures skin tumor burden, lymph nodes, visceral metastasis, and blood involvement. For patient questionnaires, this means we need to collect approximate BSA, lesion type, erythroderma, tumors, palpable nodes, blood/flow cytometry results, imaging, and pathology features.
- Diagnostic delay is a major scientific and patient-care issue. Studies report multi-year delays; PROCLIPI reported substantial delay in early-stage MF, and one retrospective study found a median histopathologic diagnostic delay of 2.3 years.
- Early-stage treatment is usually skin-directed: topical steroids, phototherapy, topical nitrogen mustard/chlormethine, topical retinoids, localized radiotherapy, and observation in selected patients. Advanced/refractory disease often needs systemic therapy or extracorporeal photopheresis.
- Quality of life and itch are scientifically important. CTCL studies often use Skindex-29, DLQI, itch VAS/NRS, FACT-G, RAND-12/SF-12, EQ-5D, and treatment satisfaction measures. Itch correlates strongly with quality-of-life impairment.
- Prognostic work is active. CLIPi/CLIPI and PROCLIPI-style efforts emphasize age, sex, plaques, folliculotropism, nodal class, blood involvement, LDH, large-cell transformation, and visceral disease.
- Asian and Chinese real-world MF data remain relatively limited compared with Western cohorts. A well-designed Chinese-language patient registry could be valuable if data quality and ethics are strong.

## 3. Highest-Value Scientific Questions for 300 Patients

With ~300 patients, the strongest first paper is likely a descriptive, patient-reported registry paper rather than a causal treatment-comparison paper. The cohort can still produce meaningful science if the dataset is structured carefully.

Primary paper candidate:

"Patient-reported diagnostic journey, treatment patterns, and quality-of-life burden in a Chinese-language mycosis fungoides cohort."

Core questions:

1. Diagnostic delay
   - Time from first skin symptom to first dermatology visit.
   - Time from first symptom to first biopsy.
   - Time from first biopsy to confirmed MF diagnosis.
   - Number of biopsies before diagnosis.
   - Common initial misdiagnoses and treatments.

2. Disease phenotype and stage approximation
   - Self-reported current and worst-ever lesion type: patches, plaques, tumors, erythroderma.
   - Approximate involved BSA using palm method or body map.
   - Histologic subtype: classic, folliculotropic, hypopigmented, poikilodermatous, pagetoid reticulosis, granulomatous slack skin, large-cell transformation, uncertain.
   - Available pathology/IHC/TCR/flow cytometry results.

3. Treatment patterns and access
   - Topical therapies, phototherapy type and frequency, radiotherapy, retinoids, interferon, methotrexate, HDAC inhibitors, brentuximab vedotin, mogamulizumab, extracorporeal photopheresis, chemotherapy, clinical trials.
   - Treatment availability, affordability, insurance burden, travel distance, and CTCL expert consultation.
   - Response and discontinuation reasons: ineffective, relapse, adverse effects, access/cost, pregnancy planning, other.

4. Symptom and QoL burden
   - Itch NRS 0-10, sleep disturbance, pain/burning, fatigue.
   - DLQI or Skindex-29 if licensing/permission allows. If not, use a short custom burden module plus itch/sleep/fatigue NRS and clearly label it non-validated.
   - Anxiety/depression screen can be considered, but keep mental health handling careful and include support resources.

5. Longitudinal change
   - Follow-up every 3 months for symptoms, BSA/lesion status, treatments, adverse events, and new test results.
   - Paper 1 can be baseline cross-sectional; paper 2 can analyze longitudinal symptom and treatment trajectories.

Secondary analyses:

- Compare early vs advanced self-reported stage groups.
- Compare folliculotropic vs non-folliculotropic MF.
- Identify factors associated with diagnostic delay using regression.
- Identify factors associated with severe itch/QoL impairment.
- Explore how well patient-entered medical-report fields allow approximate CLIPi/CLIPI risk grouping.

Analyses to avoid in the first paper unless physician-validated data become available:

- Claiming one treatment is superior to another.
- Survival/progression modeling without verified diagnosis dates, staging, and outcomes.
- Molecular/pathology conclusions from patient-entered text alone.

## 4. Data Collection Principles

Collect data in layers so patients can complete the core survey quickly and motivated patients can add detail.

Minimum viable baseline modules:

- Consent and eligibility.
- Demographics: age range or birth year, sex assigned at birth, gender optional, province/city tier, ethnicity optional.
- Diagnosis basics: diagnosis year/month, hospital department, diagnosis method, number of biopsies.
- Diagnostic journey: first symptom date, first doctor visit, first biopsy, confirmed diagnosis, earlier diagnoses.
- Current disease state: lesion types, approximate BSA, itch, sleep, pain, fatigue.
- Pathology/lab summary: subtype, IHC markers, CD30, TCR clonality, flow cytometry, LDH, CBC/lymphocytes if available.
- Treatment history: therapies tried, start/stop dates or year/month, response, side effects.
- Current treatment and satisfaction.
- Care access and cost burden.
- Contact preference for follow-up, stored separately from research answers.

Optional modules:

- Upload medical report/photos after explicit consent.
- Body map.
- Family/caregiver impact.
- Fertility/pregnancy considerations.
- Work/school impact.
- Open-ended patient priorities.

Follow-up modules:

- Since-last-survey treatments and dose/frequency.
- Current lesion status and BSA.
- Itch/sleep/pain/fatigue.
- New biopsy, imaging, blood flow, LDH, diagnosis or stage change.
- Hospitalization, infection, adverse events.
- Patient-reported progression/response.

## 5. Ethics, Privacy, and Publication Readiness

Health data are sensitive personal information. For China-based research, the 2023 Measures for Ethical Review of Life Science and Medical Research Involving Humans explicitly include research using human information data, including health records and behavior data. Before collecting identifiable data for publication, obtain or partner for ethics review.

Beta mode should use de-identified or minimally identifiable data:

- Do not collect real name, national ID, exact address, phone number, or raw medical record uploads in beta.
- Use participant-generated codes or random UUIDs.
- Store contact info, if needed, in a separate table with separate access control.
- Display clear consent: research purpose, voluntary participation, ability to withdraw, data use, risks, benefits, privacy measures, contact person, and whether data may be published in aggregate.
- Avoid minors in the first pilot unless a formal guardian-consent process is reviewed.
- Treat free-tier hosting as testing infrastructure, not production-grade medical research infrastructure.

Publication readiness requirements:

- Predefine inclusion/exclusion criteria.
- Keep questionnaire versions immutable.
- Track consent version.
- Export reproducible analysis datasets.
- Keep a data dictionary and codebook.
- Record missingness explicitly instead of silently coercing unknown values.
- Separate patient-reported data from clinician-verified data.

## 6. Product Requirements

User-facing pages:

- Landing page: project purpose, who can participate, privacy summary, team/contact, start button.
- Consent page: must accept before survey.
- Survey page: generated dynamically from YAML.
- Save/resume: magic link or anonymous resume code for MVP.
- Optional long-term follow-up identity: patient-consented WeChat-based public key plus participant-held retrieval key, stored separately from research answers.
- Completion page: thank-you message and optional follow-up opt-in.
- Admin page: survey version preview, response count, export, follow-up schedule view.

Researcher-facing features:

- YAML questionnaire upload or version registration.
- Preview questionnaire before publish.
- Response export to CSV/Parquet.
- Data dictionary export from YAML.
- Basic dashboard: completion rate, missingness, patient count by module.
- Manual flagging: suspected duplicate, test entry, needs clinician verification.

Non-goals for beta:

- Full EHR integration.
- Patient forum/community functions.
- Medical advice chatbot.
- Treatment recommendation engine.
- Raw image AI analysis.

## 7. Recommended Architecture

For beta, prefer Streamlit + PostgreSQL/Supabase because it is fastest to build and deploy for a small patient-facing trial. FastAPI can be introduced when the app needs a stable API, richer auth, background jobs, or a separate frontend.

Suggested beta stack:

- Frontend/app: Streamlit.
- Questionnaire definition: YAML files in repo.
- Database: Supabase Postgres or Neon Postgres.
- ORM/data access: SQLAlchemy or direct psycopg with Pydantic validation.
- Secrets: Streamlit secrets management.
- Deployment: Streamlit Community Cloud for app; Supabase/Neon free tier for database.
- Analysis: Jupyter notebooks or Python scripts exporting de-identified analysis datasets.

Suggested v0.2 stack:

- FastAPI backend for survey schema, responses, exports, auth, and follow-up scheduling.
- Streamlit remains admin/analysis dashboard, or a small React frontend can be added later.
- Background job for follow-up reminders.

Free deployment caveat:

- Streamlit Community Cloud is free and GitHub-based, suitable for prototypes.
- Supabase free plan currently provides a small Postgres database and auth/storage limits; free projects may pause after inactivity.
- Neon free plan currently provides small Postgres projects suitable for prototypes.
- Render free services are useful for FastAPI prototypes but have free-tier limitations and should not be treated as production infrastructure.

## 8. Questionnaire YAML Design

Questionnaire content and rendering must be separated. YAML defines modules, questions, validation, branching, scoring metadata, export names, and version. Rendering code only interprets the schema.

Example:

```yaml
questionnaire:
  id: mf_baseline
  version: "2026.05.11"
  language: zh-CN
  title: "蕈样肉芽肿患者基线问卷"
  consent_version: "2026.05.11"

modules:
  - id: diagnosis_journey
    title: "诊断经历"
    order: 20
    questions:
      - id: first_symptom_month
        export_name: first_symptom_month
        type: month
        label: "您最早出现可能相关皮肤症状的大约年月"
        required: true
        allow_unknown: true

      - id: confirmed_diagnosis_month
        export_name: confirmed_diagnosis_month
        type: month
        label: "首次被明确诊断为蕈样肉芽肿的大约年月"
        required: true
        allow_unknown: true

      - id: biopsy_count_before_diagnosis
        export_name: biopsy_count_before_diagnosis
        type: integer
        label: "确诊前大约做过几次皮肤活检？"
        min: 0
        max: 30
        required: false

      - id: initial_misdiagnoses
        export_name: initial_misdiagnoses
        type: multiselect
        label: "确诊前曾被认为是什么疾病？"
        options:
          - eczema
          - psoriasis
          - dermatitis
          - tinea
          - vitiligo_or_pigment_disorder
          - allergy
          - unknown
          - other
```

Renderer-supported field types for MVP:

- text, textarea
- integer, decimal
- date, month, year
- single_select, multiselect
- boolean
- slider_nrs_0_10
- body_area_percent
- file_upload_later_disabled_in_v0_1
- info_text

Schema rules:

- Every question has a stable `id`.
- Every exported variable has a stable `export_name`.
- Never change meaning of an existing question id. Add a new version instead.
- Use `allow_unknown` and `prefer_not_to_answer` explicitly.
- Branching is declarative using `visible_if`.
- Scoring is metadata only; scoring functions live in code and are versioned.

## 9. Database Design

Use an append-friendly schema so future questionnaire changes do not require altering one giant responses table.

Core tables:

```sql
participants (
  id uuid primary key,
  public_code text unique,
  created_at timestamptz,
  status text,
  duplicate_of uuid null,
  notes text null
)

participant_contacts (
  id uuid primary key,
  participant_id uuid references participants(id),
  contact_type text,
  contact_value_encrypted text,
  consent_to_followup boolean,
  created_at timestamptz
)

participant_followup_keys (
  id uuid primary key,
  participant_id uuid references participants(id),
  public_key text unique,
  retrieval_key_hash text unique,
  contact_type text,
  contact_hash text,
  consent_to_followup boolean,
  created_at timestamptz,
  last_seen_at timestamptz null
)

consents (
  id uuid primary key,
  participant_id uuid references participants(id),
  consent_version text,
  accepted_at timestamptz,
  ip_hash text null,
  user_agent_hash text null
)

questionnaire_versions (
  id uuid primary key,
  questionnaire_id text,
  version text,
  yaml_sha256 text,
  yaml_body jsonb,
  status text,
  published_at timestamptz,
  created_at timestamptz
)

survey_sessions (
  id uuid primary key,
  participant_id uuid references participants(id),
  questionnaire_version_id uuid references questionnaire_versions(id),
  survey_type text,
  started_at timestamptz,
  submitted_at timestamptz null,
  completion_percent numeric
)

answers (
  id uuid primary key,
  session_id uuid references survey_sessions(id),
  question_id text,
  export_name text,
  value jsonb,
  answered_at timestamptz,
  source text
)

derived_variables (
  id uuid primary key,
  session_id uuid references survey_sessions(id),
  variable_name text,
  value jsonb,
  algorithm_version text,
  created_at timestamptz
)

data_quality_flags (
  id uuid primary key,
  participant_id uuid references participants(id),
  session_id uuid null references survey_sessions(id),
  flag_type text,
  severity text,
  message text,
  resolved_at timestamptz null
)
```

Why this design:

- `questionnaire_versions` preserves the exact YAML used for each response.
- `answers.value` as JSONB allows dynamic questions.
- `export_name` makes analysis exports stable even if UI labels change.
- `derived_variables` stores calculated fields such as diagnostic delay, approximate stage group, or score outputs without overwriting raw answers.
- Contact data are separated from research answers.
- WeChat-based follow-up identity should use HMAC with a server-side pepper; raw WeChat IDs and raw retrieval keys should not be stored.

Later optional tables:

- `medical_documents` for uploads with explicit consent.
- `clinician_verifications` for physician-reviewed stage/pathology.
- `followup_windows` for scheduled follow-up tasks.
- `audit_events` for admin actions.

## 10. Data Dictionary and Derived Variables

High-value derived variables:

- `diagnostic_delay_months`: confirmed diagnosis month - first symptom month.
- `time_to_first_biopsy_months`: first biopsy month - first symptom month.
- `biopsy_to_diagnosis_months`: confirmed diagnosis month - first biopsy month.
- `biopsy_count_category`: 0, 1, 2, 3+.
- `current_bsa_category`: <10%, 10-79%, >=80%, unknown.
- `lesion_class_patient_reported`: patch/plaque/tumor/erythroderma/mixed.
- `possible_stage_group_patient_reported`: early_skin_limited, tumor_or_erythrodermic, extracutaneous_or_blood, unknown.
- `severe_itch`: itch NRS >= 7.
- `high_sleep_disturbance`: sleep NRS >= 7.
- `treatment_count`: number of distinct therapy classes tried.
- `patient_tnmb_stage_hint`: stage hint derived from patient-entered TNMB fields.
- `patient_mswat_estimate`: patch BSA x1 + plaque BSA x2 + tumor BSA x4.
- `time_to_first_improvement`: patient-reported time to first meaningful improvement.
- `time_to_relapse_after_response`: patient-reported time from improvement to relapse/flare.

Important distinction:

- Use labels like `patient_reported` and `possible` for anything not verified by clinicians.
- For manuscripts, report the proportion of data that are physician-confirmed vs patient-reported.

## 11. Statistical Analysis Plan Draft

Baseline descriptive analysis:

- N, missingness per variable, age distribution, sex, region.
- Diagnosis timeline medians and IQRs.
- Stage/phenotype approximation.
- Treatment frequencies by disease category.
- Symptom burden: itch, sleep, pain, fatigue.
- QoL score summaries if validated scale is used.

Main associations:

- Diagnostic delay outcome:
  - Candidate predictors: age at symptom onset, sex, region/city tier, initial misdiagnosis, hypopigmented presentation, first hospital level, number of biopsies.
  - Model: median regression or linear regression on log-transformed delay; report sensitivity analyses.

- Severe itch or QoL impairment outcome:
  - Candidate predictors: current BSA category, plaques/tumors/erythroderma, stage group, treatment count, sleep disturbance, diagnosis delay.
  - Model: logistic regression for severe categories; ordinal models if appropriate.

- Treatment access outcome:
  - Candidate predictors: region, expert center access, insurance burden, diagnosis year, stage group.

Longitudinal analysis after follow-up:

- Within-person change in itch, sleep, BSA category, and treatment status.
- Mixed-effects models if repeated measures are sufficient.
- Time-to-treatment-switch can be explored but requires careful interpretation.

Minimum reporting standards:

- Show missingness.
- Separate verified from unverified data.
- Avoid overfitting: for 300 patients, keep models small and pre-specified.
- Use multiple imputation only if missingness patterns justify it.

## 12. MVP Implementation Plan

Phase 0: research and governance

- Draft protocol, consent, data dictionary.
- Recruit clinical advisor and statistics advisor.
- Decide whether beta collects only de-identified data or also optional hashed follow-up identity.

Phase 1: technical prototype

- Streamlit landing page.
- YAML-driven baseline questionnaire.
- Supabase/Neon Postgres connection.
- Create participant, consent, session, answers tables.
- Save/resume with random code.
- Admin export.

Phase 2: pilot with 10-20 testers

- Test completion time.
- Identify confusing questions.
- Validate export format.
- Confirm missingness and branch logic.
- Iterate YAML version.

Phase 3: 300-person baseline collection

- Freeze baseline questionnaire version.
- Publish project instructions.
- Monitor data quality.
- Export locked analysis dataset.

Phase 4: follow-up

- Add follow-up questionnaire.
- Schedule 3-month reminders if consented.
- Build longitudinal exports.

## 13. Repo Structure Proposal

```text
.
├── app.py
├── requirements.txt
├── README.md
├── docs/
│   ├── engineering_doc.md
│   ├── protocol_draft.md
│   └── data_dictionary.md
├── questionnaires/
│   ├── mf_baseline_2026_05_11.yaml
│   └── mf_followup_2026_05_11.yaml
├── mf_registry/
│   ├── db.py
│   ├── models.py
│   ├── questionnaire_schema.py
│   ├── renderer_streamlit.py
│   ├── export.py
│   └── derived.py
├── migrations/
│   └── 001_init.sql
└── tests/
    ├── test_questionnaire_schema.py
    ├── test_branching.py
    └── test_exports.py
```

## 14. Open Decisions

- Validated QoL instrument: DLQI is shorter; Skindex-29 is common in CTCL literature but longer and may have licensing/permission considerations.
- Contact strategy: anonymous resume code only vs email/WeChat follow-up. For publication-grade follow-up, contact storage requires stronger consent and security.
- Uploads: defer medical report/photo uploads until ethics/privacy workflow is mature.
- Language: start zh-CN; keep YAML language-aware for later English export.
- Clinician verification: optional subset review would greatly increase scientific value.
- Hosting: free services for pilot; production should be reconsidered before real sensitive data collection.

## 15. References and Useful Sources

- NCI PDQ Health Professional Version, "Mycosis Fungoides and Other Cutaneous T-Cell Lymphomas Treatment", updated 2025-02-19: https://www.cancer.gov/types/lymphoma/hp/mycosis-fungoides-treatment-pdq
- Hristov, Tejasvi, Wilcox. "Mycosis Fungoides, Sézary Syndrome, and Cutaneous B-Cell Lymphomas: 2025 Update on Diagnosis, Risk-Stratification, and Management." PubMed: https://pubmed.ncbi.nlm.nih.gov/40495407/
- Lee H. "Mycosis fungoides and Sézary syndrome." Blood Research, 2023: https://pmc.ncbi.nlm.nih.gov/articles/PMC10133849/
- Benton et al. "A cutaneous lymphoma international prognostic index (CLIPi) for mycosis fungoides and Sezary syndrome." European Journal of Cancer, 2013: https://www.sciencedirect.com/science/article/pii/S0959804913003523
- Quaglino et al. "Treatment of early-stage mycosis fungoides: results from the PROCLIPI study." British Journal of Dermatology, 2021: https://academic.oup.com/bjd/article/184/4/722/6603051
- Scarisbrick et al. "The PROCLIPI international registry of early-stage mycosis fungoides identifies substantial diagnostic delay in most patients." PubMed: https://pubmed.ncbi.nlm.nih.gov/30267549/
- Skov and Gniadecki. "Delay in the histopathologic diagnosis of mycosis fungoides." Acta Dermato-Venereologica, 2015: https://research.regionh.dk/en/publications/delay-in-the-histopathologic-diagnosis-of-mycosis-fungoides
- Wright et al. "Prevalence and Severity of Pruritus and Quality of Life in Patients With Cutaneous T-Cell Lymphoma." Journal of Pain and Symptom Management, 2013: https://www.sciencedirect.com/science/article/pii/S0885392412002540
- Vermeer/Leiden group, "Evaluation of Quality of Life and Treatment Satisfaction in Newly Diagnosed Cutaneous T-Cell Lymphoma Patients", 2024: https://www.mdpi.com/2072-6694/16/5/937
- SEER-based incidence/survival review, "Mycosis fungoides: developments in incidence, treatment and survival": https://pmc.ncbi.nlm.nih.gov/articles/PMC7733543/
- 中国国家卫健委，《涉及人的生命科学和医学研究伦理审查办法》文件解读，2023-02-27: https://www.nhc.gov.cn/qjjys/c100015/202302/687d51e0d215464590b87d7e2246c720.shtml
- 中国政府网，《涉及人的生命科学和医学研究伦理审查办法》文件解读，2023-02-28: https://www.gov.cn/zhengce/2023-02/28/content_5743660.htm
- Streamlit Community Cloud docs: https://docs.streamlit.io/deploy/streamlit-community-cloud
- Supabase pricing/free plan: https://supabase.com/pricing
- Neon pricing/free plan: https://neon.com/pricing
- Render free deployment docs: https://render.com/docs/free
