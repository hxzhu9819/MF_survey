create table if not exists participants (
  id uuid primary key,
  public_code text unique not null,
  created_at timestamptz not null default now(),
  status text not null default 'active',
  duplicate_of uuid null references participants(id),
  notes text null
);

create table if not exists consents (
  id uuid primary key,
  participant_id uuid not null references participants(id),
  consent_version text not null,
  accepted_at timestamptz not null default now(),
  ip_hash text null,
  user_agent_hash text null
);

create table if not exists participant_followup_keys (
  id uuid primary key,
  participant_id uuid not null references participants(id),
  public_key text unique not null,
  retrieval_key_hash text unique not null,
  contact_type text not null,
  contact_hash text not null,
  consent_to_followup boolean not null default false,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz null
);

create table if not exists questionnaire_versions (
  id uuid primary key,
  questionnaire_id text not null,
  version text not null,
  yaml_sha256 text not null unique,
  yaml_body jsonb not null,
  status text not null default 'published',
  published_at timestamptz null,
  created_at timestamptz not null default now()
);

create table if not exists survey_sessions (
  id uuid primary key,
  participant_id uuid not null references participants(id),
  questionnaire_version_id uuid not null references questionnaire_versions(id),
  survey_type text not null,
  started_at timestamptz not null default now(),
  submitted_at timestamptz null,
  completion_percent numeric null
);

create table if not exists answers (
  id uuid primary key,
  session_id uuid not null references survey_sessions(id),
  question_id text not null,
  export_name text not null,
  value jsonb null,
  answered_at timestamptz not null default now(),
  source text not null default 'patient_reported'
);

create table if not exists derived_variables (
  id uuid primary key,
  session_id uuid not null references survey_sessions(id),
  variable_name text not null,
  value jsonb null,
  algorithm_version text not null,
  created_at timestamptz not null default now()
);
