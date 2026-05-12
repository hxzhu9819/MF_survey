from __future__ import annotations

from datetime import date
import html
from typing import Any

import streamlit as st

from mf_registry.derived import estimate_mswat, estimate_skin_t_stage, estimate_tnmb_hint
from mf_registry.regions import REGIONS


ANSWER_STATE_KEY = "survey_answers"
STEP_STATE_KEY = "survey_step"
NON_DATA_QUESTION_TYPES = {"info_text", "subsection"}
MISDIAGNOSIS_OPTIONS = [
    ("parapsoriasis", "副银屑病/副银"),
    ("eczema", "湿疹/皮炎"),
    ("psoriasis", "银屑病"),
    ("tinea", "真菌感染/癣"),
    ("allergy", "过敏"),
    ("vitiligo_or_pigment", "白癜风或色素异常"),
    ("folliculitis", "毛囊炎"),
    ("drug_eruption", "药疹"),
    ("other", "其他"),
    ("unknown", "不确定"),
]
HOSPITAL_LEVEL_OPTIONS = [
    ("tertiary", "三级医院/大型综合医院"),
    ("dermatology_specialty", "皮肤专科医院"),
    ("secondary", "二级医院"),
    ("primary_or_clinic", "基层医院/诊所"),
    ("online", "线上问诊"),
    ("unknown", "不确定"),
]


def render_questionnaire_wizard(body: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    modules = sorted(body.get("modules", []), key=lambda item: item.get("order", 0))
    if ANSWER_STATE_KEY not in st.session_state:
        st.session_state[ANSWER_STATE_KEY] = {}
    if STEP_STATE_KEY not in st.session_state:
        st.session_state[STEP_STATE_KEY] = 0

    max_step = len(modules)
    current_step = min(max(st.session_state[STEP_STATE_KEY], 0), max_step)
    st.session_state[STEP_STATE_KEY] = current_step

    answers = st.session_state[ANSWER_STATE_KEY]
    sync_answers_from_widgets(body, answers)
    current_module = modules[current_step] if current_step < max_step else None
    navigation_enabled = current_module is None or not should_use_deferred_form(current_module)
    render_level_map(modules, current_step, answers, navigation_enabled=navigation_enabled)
    completion = completion_percent(body, answers)
    st.progress(completion / 100, text=f"已完成 {completion}%")

    if current_step == max_step:
        return render_review_step(body, answers)

    module = modules[current_step]
    if should_use_deferred_form(module):
        render_module_form(module, answers, current_step, max_step, body)
    else:
        with st.container(border=True):
            render_module_intro(module)
            st.caption(f"第 {current_step + 1} 关 / 共 {len(modules)} 关")
            st.divider()
            render_module_questions(module, answers)
            if module.get("id") == "staging_skin_burden":
                render_tnmb_helper_board(answers, module)

        st.session_state[ANSWER_STATE_KEY] = answers
        missing = missing_required_questions(body, answers)
        st.caption(f"当前总完成度 {completion_percent(body, answers)}%。必填未完成：{len(missing)} 项。")
        render_step_controls(current_step, max_step)
    return answers, False


def should_use_deferred_form(module: dict[str, Any]) -> bool:
    if module.get("id") == "staging_skin_burden":
        return False
    unsupported_types = {"repeatable_misdiagnosis"}
    return not any(question.get("type") in unsupported_types for question in module.get("questions", []))


def render_module_form(
    module: dict[str, Any],
    answers: dict[str, Any],
    current_step: int,
    max_step: int,
    body: dict[str, Any],
) -> None:
    with st.container(border=True):
        render_module_intro(module)
        st.caption(f"第 {current_step + 1} 关 / 共 {max_step} 关")
        st.divider()
        with st.form(f"survey_step_form_{module['id']}"):
            st.caption("本关填写过程中不会反复刷新；完成后请点击下方保存按钮。")
            render_module_questions(module, answers)
            missing = missing_required_questions(body, answers)
            st.caption(f"当前总完成度 {completion_percent(body, answers)}%。必填未完成：{len(missing)} 项。")
            back_col, next_col = st.columns([1, 1], gap="small")
            with back_col:
                previous_clicked = st.form_submit_button("保存本关并返回上一关", disabled=current_step == 0, width="stretch")
            with next_col:
                label = "保存本关并进入确认页" if current_step == max_step - 1 else "保存本关并进入下一关"
                next_clicked = st.form_submit_button(label, type="primary", width="stretch")

    st.session_state[ANSWER_STATE_KEY] = answers
    if previous_clicked:
        st.session_state[STEP_STATE_KEY] = max(current_step - 1, 0)
        st.rerun()
    if next_clicked:
        st.session_state[STEP_STATE_KEY] = min(current_step + 1, max_step)
        st.rerun()


def render_module_questions(module: dict[str, Any], answers: dict[str, Any]) -> None:
    question_index = 0
    for question in module.get("questions", []):
        is_data_question = question["type"] not in NON_DATA_QUESTION_TYPES
        if is_data_question:
            question_index += 1
        value = render_question(question, index=question_index if is_data_question else None)
        if is_data_question:
            answers[question["id"]] = value


def render_tnmb_helper_board(answers: dict[str, Any], module: dict[str, Any]) -> None:
    questions_by_id = {question["id"]: question for question in module.get("questions", [])}
    patch_bsa = current_numeric_value(answers, "mswat_patch_bsa_percent")
    plaque_bsa = current_numeric_value(answers, "mswat_plaque_bsa_percent")
    tumor_bsa = current_numeric_value(answers, "mswat_tumor_bsa_percent")
    node_status = current_question_value(answers, questions_by_id, "tnmb_node_status_self_reported")
    visceral_status = current_question_value(answers, questions_by_id, "tnmb_visceral_status_self_reported")
    blood_status = current_question_value(answers, questions_by_id, "tnmb_blood_status_self_reported")
    answers["mswat_patch_bsa_percent"] = patch_bsa
    answers["mswat_plaque_bsa_percent"] = plaque_bsa
    answers["mswat_tumor_bsa_percent"] = tumor_bsa
    answers["tnmb_node_status_self_reported"] = node_status
    answers["tnmb_visceral_status_self_reported"] = visceral_status
    answers["tnmb_blood_status_self_reported"] = blood_status
    skin_t = estimate_skin_t_stage(
        current_bsa=numeric_value(answers.get("current_bsa_percent")),
        patch_bsa=patch_bsa,
        plaque_bsa=plaque_bsa,
        tumor_bsa=tumor_bsa,
        current_lesions=answers.get("current_lesion_types") or [],
        erythroderma=answers.get("erythroderma_self_reported"),
    )
    tnmb = estimate_tnmb_hint(
        skin_t_stage_hint=skin_t,
        node_status=node_status,
        visceral_status=visceral_status,
        blood_status=blood_status,
    )
    mswat = estimate_mswat(patch_bsa, plaque_bsa, tumor_bsa)
    stage_label = TNMB_STAGE_LABELS.get(tnmb["stage"], "信息不足，暂不能形成临床分期线索")
    mswat_label = "暂无法估算" if mswat is None else f"{mswat:g}"

    st.markdown(
        f"""
        <div class="mf-tnmb-board">
          <div class="mf-tnmb-title">按 TNMB / mSWAT 官方规则整理（可选）</div>
          <div class="mf-tnmb-note">这是根据自填信息按固定规则生成的估算提示，不是医生诊断；N、M、B 仍需要检查结果确认。</div>
          <div class="mf-tnmb-grid">
            <div><strong>T</strong><span>{html.escape(TNMB_COMPONENT_LABELS.get(tnmb["t"], "Tx：皮肤信息不足"))}</span></div>
            <div><strong>N</strong><span>{html.escape(TNMB_COMPONENT_LABELS.get(tnmb["n"], "Nx：淋巴结信息不足"))}</span></div>
            <div><strong>M</strong><span>{html.escape(TNMB_COMPONENT_LABELS.get(tnmb["m"], "Mx：内脏信息不足"))}</span></div>
            <div><strong>B</strong><span>{html.escape(TNMB_COMPONENT_LABELS.get(tnmb["b"], "Bx：血液信息不足"))}</span></div>
          </div>
          <div class="mf-tnmb-summary">
            <span>mSWAT 粗略值：{html.escape(mswat_label)}</span>
            <span>分期线索：{html.escape(stage_label)}</span>
          </div>
          <div class="mf-tnmb-reference">
            <div class="mf-tnmb-reference-title">官方范围速查</div>
            <div class="mf-tnmb-reference-note">用于理解缩写含义。具体分期仍需医生结合查体、病理、影像和血液检查确认。</div>
            <div class="mf-tnmb-ref-grid">
              <div><strong>mSWAT</strong><span>斑片面积 x1 + 斑块面积 x2 + 肿瘤面积 x4。主要用于量化皮肤负担和随访变化。</span></div>
              <div><strong>T 皮肤</strong><span>T1：斑片/斑块 &lt;10%；T2：斑片/斑块 >=10%；T3：至少 1 个肿瘤；T4：红皮病或约 >=80% 皮肤受累。</span></div>
              <div><strong>N 淋巴结</strong><span>N0：无异常；N1/N2：异常淋巴结但程度需病理分级；N3：明显肿瘤受累或结构破坏；Nx：信息不足。</span></div>
              <div><strong>M 内脏</strong><span>M0：无内脏受累；M1：确认内脏受累；Mx：未检查或信息不足。M1 通常对应 IVB 线索。</span></div>
              <div><strong>B 血液</strong><span>B0：无明显血液受累；B1：低水平血液受累；B2：高水平血液受累或 Sézary 相关线索；Bx：信息不足。</span></div>
              <div><strong>临床分期</strong><span>IA/IB 多为皮肤局限；IIA 有部分淋巴结线索；IIB 有皮肤肿瘤；III 为红皮病；IVA/IVB 涉及明显血液、淋巴结或内脏受累。</span></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


TNMB_COMPONENT_LABELS = {
    "tx": "Tx：皮肤信息不足，或当前 mSWAT 面积均为 0",
    "t1": "T1：斑片/斑块 <10% 体表面积",
    "t2": "T2：斑片/斑块 >=10% 体表面积",
    "t3": "T3：>=1 个肿瘤/结节线索",
    "t4": "T4：红皮病或 >=80% 皮肤受累线索",
    "n0": "N0：未见异常淋巴结线索",
    "nx": "Nx：淋巴结信息不足或未活检",
    "n1_or_n2": "N1/N2：需病理分级确认",
    "n2": "N2：有淋巴结受累线索，需医生确认",
    "n3": "N3：明显淋巴结受累线索",
    "m0": "M0：未见内脏受累线索",
    "m1": "M1：有内脏受累线索",
    "mx": "Mx：内脏信息不足",
    "b0": "B0：未见血液受累线索",
    "b1": "B1：低水平血液受累线索",
    "b2": "B2：高水平血液受累线索",
    "bx_abnormal": "Bx：血液异常但分级不清",
    "bx": "Bx：血液信息不足",
}


TNMB_STAGE_LABELS = {
    "ia_hint": "可能接近 IA 线索",
    "ib_hint": "可能接近 IB 线索",
    "iia_hint": "可能接近 IIA 线索",
    "iib_hint": "可能接近 IIB 线索",
    "iiia_hint": "可能接近 IIIA 线索",
    "iiib_hint": "可能接近 IIIB 线索",
    "stage_iii_hint": "可能接近 III 期线索，但 B 分级不足",
    "iva1_hint": "可能接近 IVA1 线索",
    "iva2_hint": "可能接近 IVA2 线索",
    "ivb_hint": "可能接近 IVB 线索",
    "insufficient_information": "信息不足，暂不能形成临床分期线索",
}


def numeric_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def current_question_value(
    answers: dict[str, Any],
    questions_by_id: dict[str, dict[str, Any]],
    question_id: str,
) -> Any:
    question = questions_by_id.get(question_id)
    key = f"q_{question_id}"
    if question and question.get("type") == "single_select" and key in st.session_state:
        current = value_from_option_label(question, st.session_state.get(key))
        if current is not None:
            return current
    return answers.get(question_id)


def current_numeric_value(answers: dict[str, Any], question_id: str) -> float | None:
    key = f"q_{question_id}"
    if key in st.session_state:
        return numeric_value(st.session_state.get(key))
    return numeric_value(answers.get(question_id))


def sync_answers_from_widgets(body: dict[str, Any], answers: dict[str, Any]) -> None:
    for module in body.get("modules", []):
        for question in module.get("questions", []):
            question_type = question["type"]
            question_id = question["id"]
            key = f"q_{question_id}"

            if st.session_state.get(f"{key}_unknown"):
                answers[question_id] = None
                continue
            if st.session_state.get(f"{key}_skip"):
                answers[question_id] = None
                continue

            if question_type in {"text", "textarea", "integer", "decimal", "boolean", "slider_nrs_0_10", "body_area_percent"}:
                if key in st.session_state:
                    answers[question_id] = st.session_state[key]
                continue

            if question_type == "year" and key in st.session_state:
                value = st.session_state[key]
                answers[question_id] = int(value) if value else None
                continue

            if question_type == "month":
                year = st.session_state.get(f"{key}_year")
                month = st.session_state.get(f"{key}_month")
                answers[question_id] = f"{int(year):04d}-{int(month):02d}" if year and month else None
                continue

            if question_type == "date" and key in st.session_state:
                value = st.session_state[key]
                answers[question_id] = value.isoformat() if value else None
                continue

            if question_type == "single_select" and key in st.session_state:
                selected = st.session_state[key]
                answers[question_id] = value_from_option_label(question, selected)
                continue

            if question_type == "multiselect" and key in st.session_state:
                selected = set(st.session_state[key])
                answers[question_id] = [
                    option["value"] for option in question["options"] if option["label"] in selected
                ]
                continue

            if question_type == "region_select":
                province = st.session_state.get(f"{key}_province")
                city = st.session_state.get(f"{key}_city")
                answers[question_id] = {"province": province, "city": city} if province and city else None


def value_from_option_label(question: dict[str, Any], selected: Any) -> str | None:
    if selected in (None, "", "请选择"):
        return None
    valid_values = {option["value"] for option in question["options"]}
    if selected in valid_values:
        return selected
    for option in question["options"]:
        if option["label"] == selected:
            return option["value"]
    return None


def restore_question_state(question: dict[str, Any], key: str, answers: dict[str, Any]) -> None:
    question_id = question["id"]
    if question_id not in answers:
        return

    value = answers.get(question_id)
    question_type = question["type"]

    if question_type in {"text", "textarea"}:
        set_state_if_absent(key, value or "")
        return

    if question_type in {"integer", "decimal"}:
        if value is None:
            return
        set_state_if_absent(key, value)
        return

    if question_type == "year":
        if value is None:
            return
        set_state_if_absent(key, int(value))
        return

    if question_type == "month":
        if value is None:
            return
        try:
            year, month = [int(part) for part in str(value).split("-")]
        except ValueError:
            return
        set_state_if_absent(f"{key}_year", year)
        set_state_if_absent(f"{key}_month", month)
        return

    if question_type == "date":
        if value:
            try:
                set_state_if_absent(key, date.fromisoformat(str(value)))
            except ValueError:
                return
        return

    if question_type == "single_select":
        restored = value_from_option_label(question, value)
        if restored is not None:
            set_state_if_absent(key, restored)
        return

    if question_type == "multiselect":
        if not isinstance(value, list):
            return
        labels_by_value = {option["value"]: option["label"] for option in question["options"]}
        valid_labels = set(labels_by_value.values())
        selected_labels = [labels_by_value[item] for item in value if item in labels_by_value]
        selected_labels.extend(item for item in value if item in valid_labels and item not in selected_labels)
        set_state_if_absent(key, selected_labels)
        return

    if question_type == "boolean":
        if value is not None:
            set_state_if_absent(key, bool(value))
        return

    if question_type in {"slider_nrs_0_10", "body_area_percent"}:
        if value is None:
            return
        set_state_if_absent(key, int(value))
        return

    if question_type == "region_select":
        if isinstance(value, dict):
            set_state_if_absent(f"{key}_province", value.get("province"))
            set_state_if_absent(f"{key}_city", value.get("city"))
        return

    if question_type == "repeatable_misdiagnosis":
        restore_repeatable_misdiagnosis_state(key, value)


def restore_repeatable_misdiagnosis_state(key: str, value: Any) -> None:
    if not isinstance(value, list):
        return
    count_key = f"{key}_count"
    set_state_if_absent(count_key, len(value))
    hospital_label_by_value = dict(HOSPITAL_LEVEL_OPTIONS)
    disease_label_by_value = dict(MISDIAGNOSIS_OPTIONS)
    for index, event in enumerate(value):
        if not isinstance(event, dict):
            continue
        visit_month = event.get("visit_month")
        if visit_month:
            try:
                year, month = [int(part) for part in str(visit_month).split("-")]
            except ValueError:
                year = month = None
            set_state_if_absent(f"{key}_{index}_year", year)
            set_state_if_absent(f"{key}_{index}_month", month)
        region = event.get("care_region")
        if isinstance(region, dict):
            set_state_if_absent(f"{key}_{index}_region_province", region.get("province"))
            set_state_if_absent(f"{key}_{index}_region_city", region.get("city"))
        set_state_if_absent(
            f"{key}_{index}_hospital_level",
            hospital_label_by_value.get(event.get("hospital_level")),
        )
        set_state_if_absent(
            f"{key}_{index}_disease",
            disease_label_by_value.get(event.get("misdiagnosis")),
        )
        set_state_if_absent(f"{key}_{index}_disease_other", event.get("misdiagnosis_other") or "")


def set_state_if_absent(key: str, value: Any) -> None:
    if value is not None and key not in st.session_state:
        st.session_state[key] = value


def render_level_map(
    modules: list[dict[str, Any]],
    current_step: int,
    answers: dict[str, Any],
    navigation_enabled: bool = True,
) -> None:
    levels: list[dict[str, Any]] = []
    for index, module in enumerate(modules):
        module_questions = [
            question for question in module.get("questions", []) if question["type"] not in NON_DATA_QUESTION_TYPES
        ]
        answered = sum(1 for question in module_questions if is_answered(answers.get(question["id"]), question))
        total = len(module_questions) or 1
        percent = round(answered / total * 100)
        state = "current" if index == current_step else "done" if percent == 100 else "open"
        levels.append(
            {
                "label": f"{index + 1}\n{module['title']}\n{answered}/{total}",
                "percent": percent,
                "state": state,
                "target": index,
            }
        )

    review_state = "current" if current_step == len(modules) else "open"
    levels.append(
        {
            "label": "终\n确认提交\nFinal",
            "percent": 0,
            "state": review_state,
            "target": len(modules),
        }
    )

    row_size = 4
    render_level_map_styles(levels, row_size)
    for row_index, start in enumerate(range(0, len(levels), row_size)):
        row_levels = levels[start : start + row_size]
        st.markdown(
            f'<div class="mf-level-map-native-start mf-level-map-row-{row_index}"></div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(len(row_levels), gap="small")
        for column_index, level in enumerate(row_levels):
            level_index = start + column_index
            with columns[column_index]:
                if st.button(
                    level["label"],
                    key=f"level_map_{level_index}",
                    width="stretch",
                    disabled=not navigation_enabled,
                ):
                    st.session_state[STEP_STATE_KEY] = level["target"]
                    st.rerun()
    st.markdown('<div class="mf-level-map-native-end"></div>', unsafe_allow_html=True)
    if not navigation_enabled:
        st.caption("本关正在填写中。请先点击本关底部的保存按钮，再通过进度地图跳转到其他章节。")


def render_level_map_styles(levels: list[dict[str, Any]], row_size: int) -> None:
    rules = []
    for index, level in enumerate(levels, start=1):
        fill = min(max(int(level["percent"]), 0), 100)
        tint = "rgba(47, 125, 104, 0.34)"
        if level["state"] == "done":
            tint = "rgba(47, 125, 104, 0.5)"
        selector = f'.st-key-level_map_{index - 1} button[data-testid^="stBaseButton"]'
        rules.append(
            f"{selector} {{"
            f"background: linear-gradient(0deg, {tint} 0 {fill}%, rgba(255, 255, 255, 0.78) {fill}% 100%) !important;"
            "}"
        )
        if level["state"] == "current":
            rules.append(
                f"{selector} {{"
                "border-color: rgba(47, 125, 104, 0.62) !important;"
                "box-shadow: inset 0 0 0 1px rgba(47, 125, 104, 0.2) !important;"
                "}"
            )
    st.markdown(f"<style>{''.join(rules)}</style>", unsafe_allow_html=True)


def render_step_controls(current_step: int, max_step: int) -> None:
    back_col, next_col = st.columns([1, 1], gap="small")
    with back_col:
        if st.button("上一关", disabled=current_step == 0, width="stretch"):
            st.session_state[STEP_STATE_KEY] = max(current_step - 1, 0)
            st.rerun()
    with next_col:
        label = "进入确认页" if current_step == max_step - 1 else "下一关"
        if st.button(label, type="primary", width="stretch"):
            st.session_state[STEP_STATE_KEY] = min(current_step + 1, max_step)
            st.rerun()


def render_review_step(body: dict[str, Any], answers: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    st.markdown("### 确认提交")
    st.markdown(
        """
        请在这里停一下，确认是否提交。提交后，本次问卷会生成一条新的匿名记录；
        当前 Beta 版本暂不支持在页面内直接修改已提交答案。若发现明显错误，可以重新提交一份，
        后续整理数据时会结合匿名编号、随访身份和提交时间进行去重或保留最新版。
        """
    )

    missing = missing_required_questions(body, answers)
    completion = completion_percent(body, answers)
    st.metric("完成度", f"{completion}%")
    if missing:
        st.warning("还有必填项未完成：" + "、".join(item["label"] for item in missing))
    else:
        st.success("必填项已完成，可以提交。")

    with st.expander("查看各章节完成情况", expanded=True):
        for module in sorted(body.get("modules", []), key=lambda item: item.get("order", 0)):
            questions = [
                question for question in module.get("questions", []) if question["type"] not in NON_DATA_QUESTION_TYPES
            ]
            answered = sum(1 for question in questions if is_answered(answers.get(question["id"]), question))
            st.write(f"{module['title']}：{answered}/{len(questions)}")

    back_col, submit_col = st.columns([1, 1], gap="small")
    with back_col:
        if st.button("返回上一关", width="stretch"):
            st.session_state[STEP_STATE_KEY] = max(len(body.get("modules", [])) - 1, 0)
            st.rerun()
    confirmed = st.checkbox("我已检查答案，并确认提交本次问卷。当前 Beta 版本提交后不能在页面内直接修改。")
    with submit_col:
        submitted = st.button("确认并提交问卷", type="primary", disabled=bool(missing) or not confirmed, width="stretch")
    return answers, submitted


def render_module_intro(module: dict[str, Any]) -> None:
    title = html.escape(str(module["title"]))
    description = html.escape(str(module.get("description", ""))).replace("\n", "<br>")
    why = html.escape(str(module.get("why_we_ask", ""))).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="mf-intro">
          <div class="mf-intro-title">{title}</div>
          <div class="mf-intro-body">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if why:
        st.markdown(
            f"""
            <div class="mf-why">
              <strong>为什么问：</strong>{why}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_question(question: dict[str, Any], index: int | None = None) -> Any:
    question_type = question["type"]
    label = question["label"]
    key = f"q_{question['id']}"
    help_text = question.get("help")
    if question_type == "info_text":
        render_info_text(label)
        return None
    if question_type == "subsection":
        render_subsection(question)
        return None

    restore_question_state(question, key, st.session_state.get(ANSWER_STATE_KEY, {}))
    render_question_header(question, index)

    if question_type == "text":
        return st.text_input("填写内容", key=key, help=help_text, label_visibility="collapsed")

    if question_type == "textarea":
        return st.text_area("填写内容", key=key, help=help_text, label_visibility="collapsed")

    if question_type == "integer":
        value = st.number_input(
            "填写数字",
            min_value=question.get("min"),
            max_value=question.get("max"),
            value=None,
            step=1,
            key=key,
            help=help_text,
            label_visibility="collapsed",
        )
        if question.get("allow_unknown") and st.checkbox("我不确定，先留空", key=f"{key}_unknown"):
            return None
        return value

    if question_type == "decimal":
        return st.number_input(
            "填写数字",
            min_value=question.get("min"),
            max_value=question.get("max"),
            value=None,
            key=key,
            help=help_text,
            label_visibility="collapsed",
        )

    if question_type == "year":
        max_year = min(int(question.get("max", date.today().year)), date.today().year)
        min_year = int(question.get("min", 1920))
        years = [None, *range(max_year, min_year - 1, -1)]
        value = st.selectbox(
            "年份",
            options=years,
            format_func=lambda item: "请选择" if item is None else str(item),
            key=key,
            help=help_text,
        )
        if question.get("allow_unknown") and st.checkbox("我不确定，先留空", key=f"{key}_unknown"):
            return None
        return int(value) if value else None

    if question_type == "month":
        year_col, month_col = st.columns(2, gap="small")
        with year_col:
            year = st.selectbox(
                "年",
                options=[None, *range(date.today().year, 1949, -1)],
                format_func=lambda value: "请选择年份" if value is None else f"{value}年",
                key=f"{key}_year",
                help=help_text,
            )
        with month_col:
            month = st.selectbox(
                "月",
                options=[None, *range(1, 13)],
                format_func=lambda value: "请选择月份" if value is None else f"{value:02d}月",
                key=f"{key}_month",
            )
        if question.get("allow_unknown") and st.checkbox("我不确定，先留空", key=f"{key}_unknown"):
            return None
        if year and month:
            return f"{int(year):04d}-{int(month):02d}"
        return None

    if question_type == "date":
        value = st.date_input("日期", value=None, key=key, help=help_text, label_visibility="collapsed")
        return value.isoformat() if value else None

    if question_type == "single_select":
        options = question["options"]
        if key in st.session_state:
            st.session_state[key] = value_from_option_label(question, st.session_state.get(key))
        label_by_value = {option["value"]: option["label"] for option in options}
        selected = st.selectbox(
            "请选择",
            options=[None, *label_by_value.keys()],
            format_func=lambda value: "请选择" if value is None else label_by_value[value],
            key=key,
            help=help_text,
            label_visibility="collapsed",
        )
        return selected

    if question_type == "multiselect":
        options = question["options"]
        selected = st.multiselect(
            "可多选",
            options=[option["label"] for option in options],
            key=key,
            help=help_text,
            label_visibility="collapsed",
        )
        return [option["value"] for option in options if option["label"] in selected]

    if question_type == "boolean":
        checkbox_label = question.get("checkbox_label", label)
        return st.checkbox(str(checkbox_label), key=key, help=help_text)

    if question_type == "slider_nrs_0_10":
        anchors = question.get("anchors", {})
        value = render_nrs_buttons(key, anchors, help_text)
        if not question.get("required") and st.checkbox("暂时无法判断，先留空", key=f"{key}_skip"):
            return None
        return value

    if question_type == "body_area_percent":
        value = st.slider("百分比", min_value=0, max_value=100, value=0, key=key, help=help_text)
        if not question.get("required") and st.checkbox("暂时无法判断，先留空", key=f"{key}_skip"):
            return None
        return value

    if question_type == "region_select":
        province_col, city_col = st.columns(2, gap="small")
        provinces = [None, *REGIONS.keys()]
        with province_col:
            province = st.selectbox(
                "省/直辖市/自治区/特别行政区",
                options=provinces,
                format_func=lambda item: "请选择" if item is None else item,
                key=f"{key}_province",
                help=help_text,
            )
        cities = [None, *REGIONS.get(province, [])] if province else [None]
        current_city = st.session_state.get(f"{key}_city")
        if current_city not in cities:
            st.session_state[f"{key}_city"] = None
        with city_col:
            city = st.selectbox(
                "城市/地区",
                options=cities,
                format_func=lambda item: "请选择" if item is None else item,
                key=f"{key}_city",
            )
        if province and city:
            return {"province": province, "city": city}
        return None

    if question_type == "repeatable_misdiagnosis":
        return render_repeatable_misdiagnosis(question, key)

    raise ValueError(f"Unsupported question type: {question_type}")


def render_info_text(label: str) -> None:
    st.markdown(
        f"""
        <div class="mf-inline-note">
          <strong>提示</strong>
          <span>{html.escape(label)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_subsection(question: dict[str, Any]) -> None:
    title = html.escape(str(question["label"]))
    description = html.escape(str(question.get("description", ""))).replace("\n", "<br>")
    body = f"<span>{description}</span>" if description else ""
    st.markdown(
        f"""
        <div class="mf-subsection">
          <strong>{title}</strong>
          {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_nrs_buttons(key: str, anchors: dict[str, str], help_text: str | None) -> int | None:
    if help_text:
        st.caption(help_text)
    st.markdown(
        f"""
        <div class="mf-nrs-anchors">
          <span>{html.escape(anchors.get("low", "0"))}</span>
          <span>{html.escape(anchors.get("high", "10"))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected = st.radio(
        "0-10 分",
        options=list(range(11)),
        index=None,
        key=key,
        horizontal=True,
        label_visibility="collapsed",
    )
    if selected is None:
        st.caption("请选择一个分数；如果暂时无法判断，可以在下方选择先留空。")
        return None
    st.markdown(
        f"""
        <div class="mf-nrs-current">
          当前选择：<strong>{int(selected)}</strong> 分
        </div>
        """,
        unsafe_allow_html=True,
    )
    return int(selected)


def render_repeatable_misdiagnosis(question: dict[str, Any], key: str) -> list[dict[str, Any]]:
    count_key = f"{key}_count"
    if count_key not in st.session_state:
        st.session_state[count_key] = 0

    add_col, clear_col = st.columns([1, 1], gap="small")
    with add_col:
        if st.button("添加一段误诊经历", key=f"{key}_add"):
            st.session_state[count_key] += 1
            st.rerun()
    with clear_col:
        if st.button("清空误诊经历", key=f"{key}_clear", disabled=st.session_state[count_key] == 0):
            st.session_state[count_key] = 0
            st.rerun()

    events: list[dict[str, Any]] = []
    if st.session_state[count_key] == 0:
        st.caption("如果没有误诊经历，或暂时不想填写，可以直接进入下一关。")
        return events

    for index in range(st.session_state[count_key]):
        with st.container(border=True):
            st.markdown(f"**误诊经历 {index + 1}**")
            year_col, month_col = st.columns(2, gap="small")
            with year_col:
                year = st.selectbox(
                    "就诊年",
                    options=[None, *range(date.today().year, 1949, -1)],
                    format_func=lambda value: "请选择年份" if value is None else f"{value}年",
                    key=f"{key}_{index}_year",
                )
            with month_col:
                month = st.selectbox(
                    "就诊月",
                    options=[None, *range(1, 13)],
                    format_func=lambda value: "请选择月份" if value is None else f"{value:02d}月",
                    key=f"{key}_{index}_month",
            )

            region_value = render_region_inline(f"{key}_{index}_region")
            level_label_by_value = dict(HOSPITAL_LEVEL_OPTIONS)
            disease_label_by_value = dict(MISDIAGNOSIS_OPTIONS)
            hospital_level_label = st.selectbox(
                "医院/就诊机构类型",
                options=["请选择", *level_label_by_value.values()],
                key=f"{key}_{index}_hospital_level",
            )
            disease_label = st.selectbox(
                "当时被认为是什么疾病？",
                options=["请选择", *disease_label_by_value.values()],
                key=f"{key}_{index}_disease",
            )
            disease_other = ""
            if disease_label == "其他":
                disease_other = st.text_input(
                    "其他误诊疾病（可不填）",
                    key=f"{key}_{index}_disease_other",
                    help="如填写，请避免加入可识别个人身份的信息。",
                )

            events.append(
                {
                    "visit_month": f"{int(year):04d}-{int(month):02d}" if year and month else None,
                    "care_region": region_value,
                    "hospital_level": _value_from_label(hospital_level_label, level_label_by_value),
                    "misdiagnosis": _value_from_label(disease_label, disease_label_by_value),
                    "misdiagnosis_other": disease_other or None,
                }
            )
    return events


def render_region_inline(key: str) -> dict[str, str] | None:
    province_col, city_col = st.columns(2, gap="small")
    provinces = [None, *REGIONS.keys()]
    with province_col:
        province = st.selectbox(
            "就医省/区",
            options=provinces,
            format_func=lambda item: "请选择" if item is None else item,
            key=f"{key}_province",
        )
    cities = [None, *REGIONS.get(province, [])] if province else [None]
    if st.session_state.get(f"{key}_city") not in cities:
        st.session_state[f"{key}_city"] = None
    with city_col:
        city = st.selectbox(
            "就医城市/地区",
            options=cities,
            format_func=lambda item: "请选择" if item is None else item,
            key=f"{key}_city",
        )
    if province and city:
        return {"province": province, "city": city}
    return None


def _value_from_label(label: str, value_to_label: dict[str, str]) -> str | None:
    if label == "请选择":
        return None
    for value, option_label in value_to_label.items():
        if option_label == label:
            return value
    return None


def render_question_header(question: dict[str, Any], index: int | None) -> None:
    required = "必填" if question.get("required") else "可跳过"
    prefix = f"第 {index} 题" if index is not None else "问题"
    st.markdown(
        f"""
        <div class="mf-question-head">
          <span>{prefix}</span>
          <strong>{html.escape(question["label"])}</strong>
          <em>{required}</em>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if question.get("help"):
        st.caption(question["help"])


def completion_percent(body: dict[str, Any], answers: dict[str, Any]) -> float:
    questions = [
        question
        for module in body.get("modules", [])
        for question in module.get("questions", [])
        if question["type"] not in NON_DATA_QUESTION_TYPES
    ]
    if not questions:
        return 0.0
    answered = 0
    for question in questions:
        value = answers.get(question["id"])
        if is_answered(value, question):
            answered += 1
    return round(answered / len(questions) * 100, 1)


def missing_required_questions(body: dict[str, Any], answers: dict[str, Any]) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for module in body.get("modules", []):
        for question in module.get("questions", []):
            if question.get("required") and not is_answered(answers.get(question["id"]), question):
                missing.append(question)
    return missing


def is_answered(value: Any, question: dict[str, Any]) -> bool:
    if question["type"] == "boolean":
        return value is True
    return value not in (None, "", [])
