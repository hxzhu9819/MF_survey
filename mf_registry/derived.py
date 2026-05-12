from __future__ import annotations

from datetime import date
from typing import Any


ALGORITHM_VERSION = "derived_v2026_05_11_4"


def month_delta(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        start_year, start_month = [int(part) for part in start.split("-")]
        end_year, end_month = [int(part) for part in end.split("-")]
    except ValueError:
        return None
    return (end_year - start_year) * 12 + (end_month - start_month)


def category_bsa(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric < 10:
        return "lt_10"
    if numeric < 80:
        return "10_to_79"
    return "gte_80"


def derive_variables(answers_by_export: dict[str, Any]) -> dict[str, Any]:
    first_symptom = answers_by_export.get("first_symptom_month")
    first_biopsy = answers_by_export.get("skin_biopsy_month") or answers_by_export.get("first_biopsy_month")
    confirmed = answers_by_export.get("confirmed_diagnosis_month")
    current_bsa = answers_by_export.get("current_bsa_percent")
    current_lesions = answers_by_export.get("current_lesion_types") or []
    lymph_or_visceral = answers_by_export.get("lymph_node_or_visceral") or []
    blood = answers_by_export.get("blood_involvement")
    itch = answers_by_export.get("itch_nrs")
    sleep = answers_by_export.get("sleep_disturbance_nrs")
    treatments = answers_by_export.get("treatments_ever") or []
    patch_bsa = _numeric(answers_by_export.get("mswat_patch_bsa_percent"))
    plaque_bsa = _numeric(answers_by_export.get("mswat_plaque_bsa_percent"))
    tumor_bsa = _numeric(answers_by_export.get("mswat_tumor_bsa_percent"))
    erythroderma = answers_by_export.get("erythroderma_self_reported")
    mswat_estimate = estimate_mswat(patch_bsa, plaque_bsa, tumor_bsa)
    skin_t_stage_hint = estimate_skin_t_stage(
        current_bsa=_numeric(current_bsa),
        patch_bsa=patch_bsa,
        plaque_bsa=plaque_bsa,
        tumor_bsa=tumor_bsa,
        current_lesions=current_lesions,
        erythroderma=erythroderma,
    )
    tnmb_hint = estimate_tnmb_hint(
        skin_t_stage_hint=skin_t_stage_hint,
        node_status=answers_by_export.get("tnmb_node_status_self_reported"),
        visceral_status=answers_by_export.get("tnmb_visceral_status_self_reported"),
        blood_status=answers_by_export.get("tnmb_blood_status_self_reported"),
    )

    possible_stage = "unknown"
    if tnmb_hint["m"] == "m1" or "visceral_involvement" in lymph_or_visceral or "node_biopsy_positive" in lymph_or_visceral:
        possible_stage = "extracutaneous_or_blood"
    elif tnmb_hint["b"] == "b2" or tnmb_hint["n"] == "n3" or blood == "yes":
        possible_stage = "extracutaneous_or_blood"
    elif skin_t_stage_hint in {"t3_tumor", "t4_erythroderma"}:
        possible_stage = "tumor_or_erythrodermic"
    elif skin_t_stage_hint in {"t1_patch_plaque_lt_10", "t2_patch_plaque_gte_10"} or current_lesions:
        possible_stage = "early_skin_limited"

    return {
        "diagnostic_delay_months": month_delta(first_symptom, confirmed),
        "time_to_first_biopsy_months": month_delta(first_symptom, first_biopsy),
        "biopsy_to_diagnosis_months": month_delta(first_biopsy, confirmed),
        "current_bsa_category": category_bsa(current_bsa),
        "patient_mswat_estimate": mswat_estimate,
        "patient_skin_t_stage_hint": skin_t_stage_hint,
        "patient_tnmb_t_hint": tnmb_hint["t"],
        "patient_tnmb_n_hint": tnmb_hint["n"],
        "patient_tnmb_m_hint": tnmb_hint["m"],
        "patient_tnmb_b_hint": tnmb_hint["b"],
        "patient_tnmb_stage_hint": tnmb_hint["stage"],
        "possible_stage_group_patient_reported": possible_stage,
        "severe_itch": _gte(itch, 7),
        "high_sleep_disturbance": _gte(sleep, 7),
        "treatment_count": len(treatments) if isinstance(treatments, list) else None,
        "derived_on": date.today().isoformat(),
    }


def _gte(value: Any, threshold: float) -> bool | None:
    if value in (None, ""):
        return None
    try:
        return float(value) >= threshold
    except (TypeError, ValueError):
        return None


def estimate_mswat(patch_bsa: float | None, plaque_bsa: float | None, tumor_bsa: float | None) -> float | None:
    if patch_bsa is None and plaque_bsa is None and tumor_bsa is None:
        return None
    score = (patch_bsa or 0) + 2 * (plaque_bsa or 0) + 4 * (tumor_bsa or 0)
    return round(score, 1)


def estimate_skin_t_stage(
    *,
    current_bsa: float | None,
    patch_bsa: float | None,
    plaque_bsa: float | None,
    tumor_bsa: float | None,
    current_lesions: list[str],
    erythroderma: str | None,
) -> str:
    patch_plaque_bsa = (patch_bsa or 0) + (plaque_bsa or 0)
    total_skin_bsa = max(current_bsa or 0, patch_plaque_bsa + (tumor_bsa or 0))

    if erythroderma in {"yes_current", "yes_past"} or "erythroderma" in current_lesions or total_skin_bsa >= 80:
        return "t4_erythroderma"
    if (tumor_bsa or 0) > 0 or "tumor" in current_lesions:
        return "t3_tumor"
    if patch_plaque_bsa >= 10 or (total_skin_bsa >= 10 and current_lesions):
        return "t2_patch_plaque_gte_10"
    if patch_plaque_bsa > 0 or (0 < total_skin_bsa < 10 and current_lesions):
        return "t1_patch_plaque_lt_10"
    if total_skin_bsa == 0:
        return "no_visible_skin_involvement"
    return "unknown"


def estimate_tnmb_hint(
    *,
    skin_t_stage_hint: str,
    node_status: str | None,
    visceral_status: str | None,
    blood_status: str | None,
) -> dict[str, str]:
    t_value = {
        "no_visible_skin_involvement": "tx",
        "t1_patch_plaque_lt_10": "t1",
        "t2_patch_plaque_gte_10": "t2",
        "t3_tumor": "t3",
        "t4_erythroderma": "t4",
    }.get(skin_t_stage_hint, "tx")
    n_value = {
        "no_abnormal_nodes": "n0",
        "enlarged_not_biopsied": "nx",
        "reactive_or_dermatopathic": "n1_or_n2",
        "involved_no_architecture_loss": "n2",
        "involved_architecture_loss_or_n3": "n3",
        "not_checked": "nx",
        "unknown": "nx",
    }.get(node_status or "", "nx")
    m_value = {
        "no": "m0",
        "suspected_only": "mx",
        "confirmed": "m1",
        "not_checked": "mx",
        "unknown": "mx",
    }.get(visceral_status or "", "mx")
    b_value = {
        "no_or_b0": "b0",
        "low_or_b1": "b1",
        "high_or_b2": "b2",
        "abnormal_uncertain": "bx_abnormal",
        "not_checked": "bx",
        "unknown": "bx",
    }.get(blood_status or "", "bx")
    return {
        "t": t_value,
        "n": n_value,
        "m": m_value,
        "b": b_value,
        "stage": estimate_stage_from_tnmb(t_value, n_value, m_value, b_value),
    }


def estimate_stage_from_tnmb(t_value: str, n_value: str, m_value: str, b_value: str) -> str:
    if m_value == "m1":
        return "ivb_hint"
    if n_value == "n3":
        return "iva2_hint"
    if b_value == "b2":
        return "iva1_hint"
    if t_value == "t4":
        if b_value == "b1":
            return "iiib_hint"
        if b_value == "b0":
            return "iiia_hint"
        return "stage_iii_hint"
    if t_value == "t3" and n_value in {"n0", "n1_or_n2", "n2"} and m_value == "m0" and b_value in {"b0", "b1"}:
        return "iib_hint"
    if t_value in {"t1", "t2"} and n_value in {"n1_or_n2", "n2"} and m_value == "m0" and b_value in {"b0", "b1"}:
        return "iia_hint"
    if t_value == "t2" and n_value == "n0" and m_value == "m0" and b_value in {"b0", "b1"}:
        return "ib_hint"
    if t_value == "t1" and n_value == "n0" and m_value == "m0" and b_value in {"b0", "b1"}:
        return "ia_hint"
    return "insufficient_information"


def _numeric(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
