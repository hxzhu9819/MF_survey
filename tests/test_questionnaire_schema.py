from pathlib import Path

from mf_registry.derived import derive_variables
from mf_registry.questionnaire_schema import load_questionnaire


def test_baseline_questionnaire_loads():
    bundle = load_questionnaire(Path("questionnaires/mf_baseline_2026_05_11.yaml"))

    assert bundle.questionnaire_id == "mf_baseline"
    assert bundle.version == "2026.05.11.4"
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
