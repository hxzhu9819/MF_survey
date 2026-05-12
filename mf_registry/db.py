from __future__ import annotations

import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Iterator

from mf_registry.derived import ALGORITHM_VERSION, derive_variables
from mf_registry.identity import FollowupIdentityInput, build_followup_identity, hash_retrieval_key

if TYPE_CHECKING:
    from mf_registry.questionnaire_schema import QuestionnaireBundle

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - local SQLite-only installs can still run.
    psycopg = None
    dict_row = None
    Jsonb = None


DEFAULT_DB_PATH = Path("data/mf_registry.sqlite3")
_POSTGRES_SCHEMA_READY_KEYS: set[str] = set()
_POSTGRES_SCHEMA_READY_LOCK = Lock()


@dataclass(frozen=True)
class SavedSubmission:
    participant_id: str
    public_code: str
    session_id: str
    followup_public_key: str | None = None
    retrieval_key: str | None = None


@dataclass(frozen=True)
class DatabaseStatus:
    backend: str
    configured: bool
    target: str
    healthy: bool
    message: str


def get_database_path() -> Path:
    configured = os.getenv("MF_REGISTRY_SQLITE_PATH")
    return Path(configured) if configured else DEFAULT_DB_PATH


def get_database_url() -> str | None:
    return os.getenv("MF_REGISTRY_DATABASE_URL") or None


def connect():
    database_url = get_database_url()
    if database_url:
        if psycopg is None:
            raise RuntimeError("MF_REGISTRY_DATABASE_URL is set but psycopg is not installed.")
        return psycopg.connect(
            database_url,
            row_factory=dict_row,
            prepare_threshold=None,
            connect_timeout=5,
        )

    db_path = get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma foreign_keys = on")
    return connection


def describe_connection(connection) -> DatabaseStatus:
    if is_postgres_connection(connection):
        target = mask_database_url(get_database_url() or "")
        try:
            row = execute(connection, "select current_database() as database_name").fetchone()
            database_name = row["database_name"] if row else "postgres"
            return DatabaseStatus(
                backend="Supabase/Postgres",
                configured=True,
                target=target,
                healthy=True,
                message=f"已连接到数据库 {database_name}",
            )
        except Exception as error:
            return DatabaseStatus(
                backend="Supabase/Postgres",
                configured=True,
                target=target,
                healthy=False,
                message=f"连接检查失败：{error}",
            )

    target_path = str(get_database_path())
    try:
        execute(connection, "select 1").fetchone()
        return DatabaseStatus(
            backend="本地 SQLite",
            configured=False,
            target=target_path,
            healthy=True,
            message="本地数据库可用",
        )
    except Exception as error:
        return DatabaseStatus(
            backend="本地 SQLite",
            configured=False,
            target=target_path,
            healthy=False,
            message=f"连接检查失败：{error}",
        )


def init_db(connection) -> None:
    if is_postgres_connection(connection):
        schema_key = postgres_schema_key()
        with _POSTGRES_SCHEMA_READY_LOCK:
            if schema_key in _POSTGRES_SCHEMA_READY_KEYS:
                return
            try:
                for statement in postgres_schema_sql().split(";"):
                    if statement.strip():
                        connection.execute(statement)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            _POSTGRES_SCHEMA_READY_KEYS.add(schema_key)
        return

    connection.executescript(
        """
        create table if not exists participants (
          id text primary key,
          public_code text unique not null,
          created_at text not null,
          status text not null default 'active',
          duplicate_of text null,
          notes text null
        );

        create table if not exists consents (
          id text primary key,
          participant_id text not null references participants(id),
          consent_version text not null,
          accepted_at text not null,
          ip_hash text null,
          user_agent_hash text null
        );

        create table if not exists participant_followup_keys (
          id text primary key,
          participant_id text not null references participants(id),
          public_key text unique not null,
          retrieval_key_hash text unique not null,
          contact_type text not null,
          contact_hash text not null,
          consent_to_followup integer not null default 0,
          created_at text not null,
          last_seen_at text null
        );

        create table if not exists questionnaire_versions (
          id text primary key,
          questionnaire_id text not null,
          version text not null,
          yaml_sha256 text not null unique,
          yaml_body text not null,
          status text not null default 'published',
          published_at text null,
          created_at text not null
        );

        create table if not exists survey_sessions (
          id text primary key,
          participant_id text not null references participants(id),
          questionnaire_version_id text not null references questionnaire_versions(id),
          survey_type text not null,
          started_at text not null,
          submitted_at text null,
          completion_percent real null
        );

        create table if not exists answers (
          id text primary key,
          session_id text not null references survey_sessions(id),
          question_id text not null,
          export_name text not null,
          value text null,
          answered_at text not null,
          source text not null default 'patient_reported'
        );

        create table if not exists derived_variables (
          id text primary key,
          session_id text not null references survey_sessions(id),
          variable_name text not null,
          value text null,
          algorithm_version text not null,
          created_at text not null
        );
        """
    )
    connection.commit()


def register_questionnaire(
    connection,
    bundle: "QuestionnaireBundle",
) -> str:
    existing = execute(
        connection,
        "select id from questionnaire_versions where yaml_sha256 = ?",
        (bundle.sha256,),
    ).fetchone()
    if existing:
        connection.commit()
        return str(existing["id"])

    version_id = str(uuid.uuid4())
    now = _now()
    execute(
        connection,
        """
        insert into questionnaire_versions (
          id, questionnaire_id, version, yaml_sha256, yaml_body, status, published_at, created_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            bundle.questionnaire_id,
            bundle.version,
            bundle.sha256,
            json_value(connection, bundle.body),
            "published",
            now,
            now,
        ),
    )
    connection.commit()
    return version_id


def save_submission(
    connection,
    bundle: "QuestionnaireBundle",
    answers: dict[str, Any],
    completion_percent: float,
    followup_identity: FollowupIdentityInput | None = None,
) -> SavedSubmission:
    init_db(connection)
    questionnaire_version_id = register_questionnaire(connection, bundle)
    identity_material = build_followup_identity(followup_identity) if followup_identity else None
    existing_participant = _find_participant_by_public_key(connection, identity_material.public_key) if identity_material else None
    participant_id = existing_participant["id"] if existing_participant else str(uuid.uuid4())
    public_code = existing_participant["public_code"] if existing_participant else _make_public_code(connection)
    consent_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    now = _now()

    with transaction(connection):
        if existing_participant:
            execute(
                connection,
                "update participant_followup_keys set last_seen_at = ? where public_key = ?",
                (now, identity_material.public_key if identity_material else None),
            )
        else:
            execute(
                connection,
                "insert into participants (id, public_code, created_at, status) values (?, ?, ?, ?)",
                (participant_id, public_code, now, "active"),
            )
            if identity_material:
                execute(
                    connection,
                    """
                    insert into participant_followup_keys (
                      id, participant_id, public_key, retrieval_key_hash, contact_type, contact_hash,
                      consent_to_followup, created_at, last_seen_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        participant_id,
                        identity_material.public_key,
                        identity_material.retrieval_key_hash,
                        identity_material.contact_type,
                        identity_material.contact_hash,
                        bool_value(connection, True),
                        now,
                        now,
                    ),
                )
        execute(
            connection,
            "insert into consents (id, participant_id, consent_version, accepted_at) values (?, ?, ?, ?)",
            (consent_id, participant_id, bundle.consent_version, now),
        )
        execute(
            connection,
            """
            insert into survey_sessions (
              id, participant_id, questionnaire_version_id, survey_type, started_at, submitted_at, completion_percent
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                participant_id,
                questionnaire_version_id,
                bundle.questionnaire_id,
                now,
                now,
                completion_percent,
            ),
        )

        questions_by_id = {question["id"]: question for question in bundle.questions}
        user_input_questions = [
            question for question in bundle.questions if question["type"] not in {"info_text", "subsection"}
        ]
        for question in user_input_questions:
            question_id = question["id"]
            value = answers.get(question_id)
            execute(
                connection,
                """
                insert into answers (id, session_id, question_id, export_name, value, answered_at, source)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    session_id,
                    question_id,
                    question["export_name"],
                    json_value(connection, value),
                    now,
                    "patient_reported",
                ),
            )

        export_answers = {
            questions_by_id[question_id]["export_name"]: value
            for question_id, value in answers.items()
            if question_id in questions_by_id
        }
        for name, value in derive_variables(export_answers).items():
            execute(
                connection,
                """
                insert into derived_variables (id, session_id, variable_name, value, algorithm_version, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    session_id,
                    name,
                    json_value(connection, value),
                    ALGORITHM_VERSION,
                    now,
                ),
            )

    return SavedSubmission(
        participant_id=participant_id,
        public_code=public_code,
        session_id=session_id,
        followup_public_key=identity_material.public_key if identity_material else None,
        retrieval_key=identity_material.retrieval_key if identity_material and not existing_participant else None,
    )


def find_participant_by_retrieval_key(connection, retrieval_key: str):
    init_db(connection)
    retrieval_hash = hash_retrieval_key(retrieval_key)
    return execute(
        connection,
        """
        select p.id, p.public_code, f.public_key
        from participant_followup_keys f
        join participants p on p.id = f.participant_id
        where f.retrieval_key_hash = ?
        """,
        (retrieval_hash,),
    ).fetchone()


def count_submissions(connection) -> int:
    init_db(connection)
    row = execute(connection, "select count(*) as count from survey_sessions where submitted_at is not null").fetchone()
    return int(row["count"])


def export_rows(connection) -> list[dict[str, Any]]:
    init_db(connection)
    sessions = execute(
        connection,
        """
        select
          s.id as session_id,
          p.public_code,
          s.survey_type,
          s.submitted_at,
          s.completion_percent
        from survey_sessions s
        join participants p on p.id = s.participant_id
        where s.submitted_at is not null
        order by s.submitted_at
        """
    ).fetchall()

    rows: list[dict[str, Any]] = []
    for session in sessions:
        row = dict(session)
        answers = execute(
            connection,
            "select export_name, value from answers where session_id = ?",
            (session["session_id"],),
        ).fetchall()
        for answer in answers:
            row[answer["export_name"]] = load_json_value(answer["value"])

        derived = execute(
            connection,
            "select variable_name, value from derived_variables where session_id = ?",
            (session["session_id"],),
        ).fetchall()
        for variable in derived:
            row[variable["variable_name"]] = load_json_value(variable["value"])
        rows.append(row)
    return rows


def _make_public_code(connection) -> str:
    for _ in range(20):
        code = "MF-" + secrets.token_urlsafe(5).upper().replace("_", "A").replace("-", "B")
        existing = execute(connection, "select 1 from participants where public_code = ?", (code,)).fetchone()
        if not existing:
            return code
    raise RuntimeError("Could not generate unique public code.")


def _find_participant_by_public_key(connection, public_key: str | None):
    if not public_key:
        return None
    return execute(
        connection,
        """
        select p.id, p.public_code
        from participant_followup_keys f
        join participants p on p.id = f.participant_id
        where f.public_key = ?
        """,
        (public_key,),
    ).fetchone()


def execute(connection, query: str, params: tuple[Any, ...] = ()):
    return connection.execute(sql(connection, query), params)


def sql(connection, query: str) -> str:
    return query.replace("?", "%s") if is_postgres_connection(connection) else query


def is_postgres_connection(connection) -> bool:
    return connection.__class__.__module__.startswith("psycopg")


def json_value(connection, value: Any) -> Any:
    if is_postgres_connection(connection):
        if Jsonb is None:
            raise RuntimeError("Postgres JSON support requires psycopg.")
        return Jsonb(value)
    return json.dumps(value, ensure_ascii=False)


def load_json_value(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def bool_value(connection, value: bool) -> bool | int:
    return value if is_postgres_connection(connection) else int(value)


def mask_database_url(database_url: str) -> str:
    if not database_url:
        return "未配置"
    if "@" not in database_url:
        return "已配置，格式待确认"

    scheme, _, rest = database_url.partition("://")
    _, _, host_and_path = rest.rpartition("@")
    host = host_and_path.split("/", 1)[0]
    database = host_and_path.split("/", 1)[1].split("?", 1)[0] if "/" in host_and_path else ""
    prefix = f"{scheme}://" if scheme else ""
    suffix = f"/{database}" if database else ""
    return f"{prefix}***@{host}{suffix}"


def postgres_schema_key() -> str:
    return f"postgres:{get_database_url() or 'configured'}"


@contextmanager
def transaction(connection) -> Iterator[None]:
    if is_postgres_connection(connection):
        with connection.transaction():
            yield
    else:
        with connection:
            yield


def postgres_schema_sql() -> str:
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / "001_init.sql"
    return migration_path.read_text(encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
