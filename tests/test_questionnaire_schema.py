from pathlib import Path
import os
import sqlite3

from mf_registry.db import export_rows, find_participant_by_retrieval_key, init_db, save_submission
from mf_registry.derived import derive_variables
from mf_registry.identity import FollowupIdentityInput
from mf_registry.questionnaire_schema import load_questionnaire


NON_DATA_TYPES = {"info_text", "subsection"}


def test_baseline_questionnaire_loads():
    bundle = load_questionnaire(Path("questionnaires/mf_baseline_2026_05_11.yaml"))

    assert bundle.questionnaire_id == "mf_baseline"
    assert bundle.version == "2026.05.11.5"
    assert len(bundle.questions) > 20


def test_followup_template_loads():
    bundle = load_questionnaire(Path("questionnaires/mf_followup_3m_template.yaml"))

    assert bundle.questionnaire_id == "mf_followup_3m"
    assert len(bundle.questions) >= 6


def test_mswat_and_skin_t_stage_derivation():
    derived = derive_variables(
        {
            "mswat_patch_bsa_percent": 8,
            "mswat_plaque_bsa_percent": 6,
            "mswat_tumor_bsa_percent": 0,
            "current_lesion_types": ["patch", "plaque"],
        }
    )

    assert derived["patient_mswat_estimate"] == 20
    assert derived["patient_skin_t_stage_hint"] == "t2_patch_plaque_gte_10"
    assert derived["patient_tnmb_t_hint"] == "t2"


def test_tnmb_stage_hint_derivation():
    derived = derive_variables(
        {
            "mswat_patch_bsa_percent": 3,
            "mswat_plaque_bsa_percent": 2,
            "mswat_tumor_bsa_percent": 0,
            "tnmb_node_status_self_reported": "no_abnormal_nodes",
            "tnmb_visceral_status_self_reported": "no",
            "tnmb_blood_status_self_reported": "no_or_b0",
        }
    )

    assert derived["patient_tnmb_t_hint"] == "t1"
    assert derived["patient_tnmb_n_hint"] == "n0"
    assert derived["patient_tnmb_m_hint"] == "m0"
    assert derived["patient_tnmb_b_hint"] == "b0"
    assert derived["patient_tnmb_stage_hint"] == "ia_hint"


def test_tnmb_m1_is_ivb_even_with_limited_other_information():
    derived = derive_variables(
        {
            "tnmb_visceral_status_self_reported": "confirmed",
        }
    )

    assert derived["patient_tnmb_m_hint"] == "m1"
    assert derived["patient_tnmb_stage_hint"] == "ivb_hint"


def test_all_tnmb_yaml_options_map_to_component_hints():
    bundle = load_questionnaire(Path("questionnaires/mf_baseline_2026_05_11.yaml"))
    options_by_export = {
        question["export_name"]: [option["value"] for option in question.get("options", [])]
        for question in bundle.questions
    }
    expected_mappings = {
        "tnmb_node_status_self_reported": {
            "no_abnormal_nodes": ("patient_tnmb_n_hint", "n0"),
            "enlarged_not_biopsied": ("patient_tnmb_n_hint", "nx"),
            "reactive_or_dermatopathic": ("patient_tnmb_n_hint", "n1_or_n2"),
            "involved_no_architecture_loss": ("patient_tnmb_n_hint", "n2"),
            "involved_architecture_loss_or_n3": ("patient_tnmb_n_hint", "n3"),
            "not_checked": ("patient_tnmb_n_hint", "nx"),
            "unknown": ("patient_tnmb_n_hint", "nx"),
        },
        "tnmb_visceral_status_self_reported": {
            "no": ("patient_tnmb_m_hint", "m0"),
            "suspected_only": ("patient_tnmb_m_hint", "mx"),
            "confirmed": ("patient_tnmb_m_hint", "m1"),
            "not_checked": ("patient_tnmb_m_hint", "mx"),
            "unknown": ("patient_tnmb_m_hint", "mx"),
        },
        "tnmb_blood_status_self_reported": {
            "no_or_b0": ("patient_tnmb_b_hint", "b0"),
            "low_or_b1": ("patient_tnmb_b_hint", "b1"),
            "high_or_b2": ("patient_tnmb_b_hint", "b2"),
            "abnormal_uncertain": ("patient_tnmb_b_hint", "bx_abnormal"),
            "not_checked": ("patient_tnmb_b_hint", "bx"),
            "unknown": ("patient_tnmb_b_hint", "bx"),
        },
    }

    for export_name, mapping in expected_mappings.items():
        assert set(options_by_export[export_name]) == set(mapping)
        for option_value, (derived_key, expected_value) in mapping.items():
            derived = derive_variables({export_name: option_value})
            assert derived[derived_key] == expected_value


def test_submission_roundtrip_records_every_user_input_and_skips_info_text():
    bundle = load_questionnaire(Path("questionnaires/mf_baseline_2026_05_11.yaml"))
    answers = {
        question["id"]: sample_answer_for_question(question)
        for question in bundle.questions
        if question["type"] not in NON_DATA_TYPES
    }

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    init_db(connection)
    saved = save_submission(connection, bundle, answers, completion_percent=100)

    stored_answers = connection.execute(
        "select question_id, export_name, value from answers where session_id = ?",
        (saved.session_id,),
    ).fetchall()
    stored_question_ids = {row["question_id"] for row in stored_answers}
    info_text_ids = {question["id"] for question in bundle.questions if question["type"] in NON_DATA_TYPES}

    assert len(stored_answers) == len(answers)
    assert stored_question_ids == set(answers)
    assert not stored_question_ids.intersection(info_text_ids)

    exported = export_rows(connection)
    assert len(exported) == 1
    exported_row = exported[0]
    questions_by_id = {question["id"]: question for question in bundle.questions}
    for question_id, value in answers.items():
        export_name = questions_by_id[question_id]["export_name"]
        assert exported_row[export_name] == value


def test_partial_submission_preserves_current_questionnaire_columns_as_nulls():
    bundle = load_questionnaire(Path("questionnaires/mf_baseline_2026_05_11.yaml"))
    user_questions = [question for question in bundle.questions if question["type"] not in NON_DATA_TYPES]
    answers = {
        user_questions[0]["id"]: sample_answer_for_question(user_questions[0]),
        user_questions[1]["id"]: sample_answer_for_question(user_questions[1]),
    }

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    init_db(connection)
    saved = save_submission(connection, bundle, answers, completion_percent=10)

    answer_count = connection.execute(
        "select count(*) as count from answers where session_id = ?",
        (saved.session_id,),
    ).fetchone()["count"]
    assert answer_count == len(user_questions)

    exported_row = export_rows(connection)[0]
    assert exported_row[user_questions[0]["export_name"]] == answers[user_questions[0]["id"]]
    assert exported_row[user_questions[-1]["export_name"]] is None


def test_followup_identity_stores_hashes_but_never_exports_raw_contact():
    old_pepper = os.environ.get("MF_REGISTRY_IDENTITY_PEPPER")
    os.environ["MF_REGISTRY_IDENTITY_PEPPER"] = "test-pepper-for-roundtrip"
    try:
        bundle = load_questionnaire(Path("questionnaires/mf_baseline_2026_05_11.yaml"))
        answers = {
            question["id"]: sample_answer_for_question(question)
            for question in bundle.questions
            if question["type"] not in NON_DATA_TYPES
        }
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        init_db(connection)
        saved = save_submission(
            connection,
            bundle,
            answers,
            completion_percent=100,
            followup_identity=FollowupIdentityInput(
                contact_type="wechat",
                contact_value="Raw_Wechat_ID_123",
                consent_to_followup=True,
            ),
        )

        followup_row = connection.execute(
            "select public_key, retrieval_key_hash, contact_type, contact_hash from participant_followup_keys"
        ).fetchone()
        assert followup_row["contact_type"] == "wechat"
        assert followup_row["public_key"] == saved.followup_public_key
        assert "Raw_Wechat_ID_123" not in dict(followup_row).values()
        assert find_participant_by_retrieval_key(connection, saved.retrieval_key)["public_code"] == saved.public_code
        assert "Raw_Wechat_ID_123" not in str(export_rows(connection)[0])
    finally:
        if old_pepper is None:
            os.environ.pop("MF_REGISTRY_IDENTITY_PEPPER", None)
        else:
            os.environ["MF_REGISTRY_IDENTITY_PEPPER"] = old_pepper


def sample_answer_for_question(question: dict):
    question_type = question["type"]
    if question_type in {"text", "textarea"}:
        return "beta sample"
    if question_type == "integer":
        return question.get("min", 1) or 1
    if question_type == "decimal":
        return float(question.get("min", 1) or 1)
    if question_type == "date":
        return "2026-05-12"
    if question_type == "month":
        return "2026-05"
    if question_type == "year":
        return 2026
    if question_type == "single_select":
        return question["options"][0]["value"]
    if question_type == "multiselect":
        return [question["options"][0]["value"]]
    if question_type == "boolean":
        return True
    if question_type in {"slider_nrs_0_10", "body_area_percent"}:
        return 3
    if question_type == "region_select":
        return {"province": "北京市", "city": "北京市"}
    if question_type == "repeatable_misdiagnosis":
        return [
            {
                "visit_month": "2024-03",
                "care_region": {"province": "上海市", "city": "上海市"},
                "hospital_level": "tertiary",
                "misdiagnosis": "parapsoriasis",
                "misdiagnosis_other": None,
            }
        ]
    raise AssertionError(f"Unhandled question type: {question_type}")
