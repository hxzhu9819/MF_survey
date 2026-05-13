from __future__ import annotations

from datetime import date
import html
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from mf_registry.questionnaire_schema import SKIPPED_ANSWER
from mf_registry.regions import REGIONS


ANSWER_STATE_KEY = "survey_answers"
STEP_STATE_KEY = "survey_step"
SUBMIT_REQUESTED_STATE_KEY = "survey_submit_requested"
SUBMIT_IN_PROGRESS_STATE_KEY = "survey_submit_in_progress"
SUBMISSION_RESULT_STATE_KEY = "survey_submission_result"
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



def numeric_value(value: Any) -> float | None:
    if value in (None, "", SKIPPED_ANSWER):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def is_skipped_answer(value: Any) -> bool:
    return value == SKIPPED_ANSWER

def init_state(key: str, value: Any) -> None:
    if value is not None and key not in st.session_state:
        st.session_state[key] = value

def render_questionnaire_wizard(schema: QuestionnaireSchema, view_registry: dict[str, Callable] = None, context: dict[str, Any] = None) -> tuple[dict[str, Any], bool]:
    modules = sorted(schema.modules, key=lambda item: item.order)
    if ANSWER_STATE_KEY not in st.session_state:
        st.session_state[ANSWER_STATE_KEY] = {}
    if STEP_STATE_KEY not in st.session_state:
        st.session_state[STEP_STATE_KEY] = 0

    max_step = len(modules)
    current_step = min(max(st.session_state[STEP_STATE_KEY], 0), max_step)
    st.session_state[STEP_STATE_KEY] = current_step

    answers = st.session_state[ANSWER_STATE_KEY]
    
    if st.session_state.pop("_scroll_to_top", False):
        components.html(
            "<script>window.parent.document.querySelector('.main').scrollTop = 0;</script>",
            height=0
        )

    render_level_map(schema, modules, current_step, answers)
    completion = completion_percent(schema, answers)
    st.progress(completion / 100, text=f"已完成 {completion}%")

    if current_step == max_step:
        return render_review_step(schema, answers)

    module = modules[current_step]
    with st.container(border=True):
        render_module_intro(module)
        st.caption(f"第 {current_step + 1} 关 / 共 {len(modules)} 关")
        st.divider()
        render_module_questions(module, answers, context=context)
        if module.derived_view and view_registry and module.derived_view in view_registry:
            view_registry[module.derived_view](answers, module, context)

    st.session_state[ANSWER_STATE_KEY] = answers
    missing = missing_required_questions(schema, answers)
    st.caption(f"当前总完成度 {completion_percent(schema, answers)}%。必填未完成：{len(missing)} 项。")
    render_step_controls(current_step, max_step)
    return answers, False

def render_module_questions(module: ModuleSchema, answers: dict[str, Any], context: dict[str, Any] = None) -> None:
    question_index = 0
    for question in module.questions:
        is_data_question = question.type not in NON_DATA_QUESTION_TYPES
        if is_data_question:
            question_index += 1
        render_question(question, answers, index=question_index if is_data_question else None, context=context)

def render_question(question: QuestionSchema, answers: dict[str, Any], index: int | None = None, context: dict[str, Any] = None) -> None:
    question_type = question.type
    question_id = question.id
    label = question.label
    key = f"q_{question_id}"
    help_text = question.help

    if question_type == "info_text":
        render_info_text(label)
        return
    if question_type == "subsection":
        render_subsection(question)
        return

    render_question_header(question, index)

    value = answers.get(question_id)
    is_skipped = is_skipped_answer(value)

    def get_skip_state(suffix: str) -> bool:
        skip_key = f"{key}_{suffix}"
        init_state(skip_key, is_skipped)
        return st.session_state.get(skip_key, is_skipped)

    def render_skip_checkbox(suffix: str, skip_label: str) -> bool:
        skip_key = f"{key}_{suffix}"
        return st.checkbox(skip_label, key=skip_key)

    is_disabled = get_skip_state("skip") or get_skip_state("unknown")

    if question_type == "text":
        init_state(key, str(value) if not is_skipped and value is not None else "")
        ans = st.text_input("填写内容", key=key, help=help_text, label_visibility="collapsed", disabled=is_disabled)
        answers[question_id] = ans

    elif question_type == "textarea":
        init_state(key, str(value) if not is_skipped and value is not None else "")
        ans = st.text_area("填写内容", key=key, help=help_text, label_visibility="collapsed", disabled=is_disabled)
        answers[question_id] = ans

    elif question_type == "integer":
        init_state(key, value if not is_skipped else None)
        min_val_int = int(question.min) if question.min is not None else None
        max_val_int = int(question.max) if question.max is not None else None
        ans = st.number_input("填写数字", min_value=min_val_int, max_value=max_val_int, value=None, step=1, key=key, help=help_text, label_visibility="collapsed", disabled=is_disabled)
        if question.allow_unknown and render_skip_checkbox("unknown", "我不确定，先留空"):
            answers[question_id] = SKIPPED_ANSWER
        else:
            answers[question_id] = ans

    elif question_type == "decimal":
        init_state(key, value if not is_skipped else None)
        min_val_float = float(question.min) if question.min is not None else None
        max_val_float = float(question.max) if question.max is not None else None
        ans = st.number_input("填写数字", min_value=min_val_float, max_value=max_val_float, value=None, step=0.01, key=key, help=help_text, label_visibility="collapsed", disabled=is_disabled)
        answers[question_id] = ans

    elif question_type == "year":
        max_year = min(int(question.max if question.max is not None else date.today().year), date.today().year)
        min_year = int(question.min if question.min is not None else 1920)
        years = [None, *range(max_year, min_year - 1, -1)]
        init_state(key, value if not is_skipped else None)
        ans = st.selectbox("年份", options=years, format_func=lambda item: "请选择" if item is None else str(item), key=key, help=help_text, disabled=is_disabled)
        if question.allow_unknown and render_skip_checkbox("unknown", "我不确定，先留空"):
            answers[question_id] = SKIPPED_ANSWER
        else:
            answers[question_id] = int(ans) if ans else None

    elif question_type == "month":
        year_col, month_col = st.columns(2, gap="small")
        y_val, m_val = None, None
        if not is_skipped and value:
            try:
                y, m = str(value).split("-")
                y_val, m_val = int(y), int(m)
            except ValueError:
                pass
        init_state(f"{key}_year", y_val)
        init_state(f"{key}_month", m_val)
        
        with year_col:
            y_ans = st.selectbox("年", options=[None, *range(date.today().year, 1949, -1)], format_func=lambda v: "请选择年份" if v is None else f"{v}年", key=f"{key}_year", help=help_text, disabled=is_disabled)
        with month_col:
            m_ans = st.selectbox("月", options=[None, *range(1, 13)], format_func=lambda v: "请选择月份" if v is None else f"{v:02d}月", key=f"{key}_month", disabled=is_disabled)
            
        if question.allow_unknown and render_skip_checkbox("unknown", "我不确定，先留空"):
            answers[question_id] = SKIPPED_ANSWER
        else:
            answers[question_id] = f"{int(y_ans):04d}-{int(m_ans):02d}" if y_ans and m_ans else None

    elif question_type == "date":
        d_val = None
        if not is_skipped and value:
            try:
                d_val = date.fromisoformat(str(value))
            except ValueError:
                pass
        init_state(key, d_val)
        ans = st.date_input("日期", value=None, key=key, help=help_text, label_visibility="collapsed", disabled=is_disabled)
        answers[question_id] = ans.isoformat() if ans else None

    elif question_type == "single_select":
        options = (question.options or [])
        label_by_value = {opt.value: opt.label for opt in options}
        init_state(key, value if not is_skipped else None)
        ans = st.selectbox("请选择", options=[None, *label_by_value.keys()], format_func=lambda v: "请选择" if v is None else label_by_value[v], key=key, help=help_text, label_visibility="collapsed", disabled=is_disabled)
        answers[question_id] = ans

    elif question_type == "multiselect":
        options = (question.options or [])
        labels_by_value = {opt.value: opt.label for opt in options}
        default_labels = []
        if not is_skipped and isinstance(value, list):
            default_labels = [labels_by_value[v] for v in value if v in labels_by_value]
        init_state(key, default_labels)
        
        ans_labels = st.multiselect("可多选", options=[opt.label for opt in options], key=key, help=help_text, label_visibility="collapsed", disabled=is_disabled)
        answers[question_id] = [opt.value for opt in options if opt.label in ans_labels]

    elif question_type == "boolean":
        init_state(key, bool(value) if not is_skipped and value is not None else False)
        checkbox_label = (question.checkbox_label or label)
        ans = st.checkbox(str(checkbox_label), key=key, help=help_text, disabled=is_disabled)
        answers[question_id] = ans

    elif question_type == "slider_nrs_0_10":
        init_state(key, int(value) if not is_skipped and value is not None else None)
        anchors = (question.anchors or {})
        ans = render_nrs_buttons(key, anchors, help_text, is_disabled)
        if not question.required and render_skip_checkbox("skip", "暂时无法判断，先留空"):
            answers[question_id] = SKIPPED_ANSWER
        else:
            answers[question_id] = ans

    elif question_type == "body_area_percent":
        init_state(key, int(value) if not is_skipped and value is not None else 0)
        ans = st.slider("百分比", min_value=0, max_value=100, key=key, help=help_text, disabled=is_disabled)
        if not question.required and render_skip_checkbox("skip", "暂时无法判断，先留空"):
            answers[question_id] = SKIPPED_ANSWER
        else:
            answers[question_id] = ans

    elif question_type == "region_select":
        prov, city = None, None
        if not is_skipped and isinstance(value, dict):
            prov, city = value.get("province"), value.get("city")
        ans = render_region_inline(key, prov, city, is_disabled, context)
        answers[question_id] = ans

    elif question_type == "repeatable_misdiagnosis":
        render_repeatable_misdiagnosis(question, key, answers, context)

    else:
        raise ValueError(f"Unsupported question type: {question_type}")

def render_region_inline(key: str, default_province: str | None = None, default_city: str | None = None, is_disabled: bool = False, context: dict[str, Any] = None) -> dict[str, str] | None:
    init_state(f"{key}_province", default_province)
    
    province_col, city_col = st.columns(2, gap="small")
    regions = context.get("regions", {}) if context else {}
    provinces = [None, *regions.keys()]
    with province_col:
        province = st.selectbox("就医省/区", options=provinces, format_func=lambda item: "请选择" if item is None else item, key=f"{key}_province", disabled=is_disabled)
        
    cities = [None, *regions.get(province, [])] if province else [None]
    
    if default_city not in cities:
        default_city = None
    if st.session_state.get(f"{key}_city") not in cities:
        st.session_state[f"{key}_city"] = None
    else:
        init_state(f"{key}_city", default_city)
        
    with city_col:
        city = st.selectbox("就医城市/地区", options=cities, format_func=lambda item: "请选择" if item is None else item, key=f"{key}_city", disabled=is_disabled)
        
    if province and city:
        return {"province": province, "city": city}
    return None

def compact_misdiagnosis_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if any(event.get(field) for field in event)]

def render_repeatable_misdiagnosis(question: QuestionSchema, key: str, answers: dict[str, Any], context: dict[str, Any] = None) -> None:
    events = answers.get(question.id)
    if not isinstance(events, list):
        events = []
        
    count_key = f"{key}_count"
    init_state(count_key, len(events))

    add_col, clear_col = st.columns([1, 1], gap="small")
    with add_col:
        if st.button("添加一段误诊经历", key=f"{key}_add"):
            st.session_state[count_key] += 1
            st.rerun()
    with clear_col:
        if st.button("清空误诊经历", key=f"{key}_clear", disabled=st.session_state[count_key] == 0):
            st.session_state[count_key] = 0
            st.rerun()

    count = st.session_state[count_key]
    if count == 0:
        st.caption("如果没有误诊经历，或暂时不想填写，可以直接进入下一关。")
        answers[question.id] = []
        return

    level_label_by_value = dict(HOSPITAL_LEVEL_OPTIONS)
    disease_label_by_value = dict(MISDIAGNOSIS_OPTIONS)
    
    current_events = []
    for index in range(count):
        event = events[index] if index < len(events) else {}
        
        with st.container(border=True):
            st.markdown(f"**误诊经历 {index + 1}**")
            
            y_val, m_val = None, None
            visit_month = event.get("visit_month")
            if visit_month:
                try:
                    y, m = visit_month.split("-")
                    y_val, m_val = int(y), int(m)
                except ValueError:
                    pass
                    
            init_state(f"{key}_{index}_year", y_val)
            init_state(f"{key}_{index}_month", m_val)
            
            year_col, month_col = st.columns(2, gap="small")
            with year_col:
                year_ans = st.selectbox("就诊年", options=[None, *range(date.today().year, 1949, -1)], format_func=lambda v: "请选择年份" if v is None else f"{v}年", key=f"{key}_{index}_year")
            with month_col:
                month_ans = st.selectbox("就诊月", options=[None, *range(1, 13)], format_func=lambda v: "请选择月份" if v is None else f"{v:02d}月", key=f"{key}_{index}_month")
            
            region_val = event.get("care_region") or {}
            region_ans = render_region_inline(f"{key}_{index}_region", region_val.get("province"), region_val.get("city"), context=context)
            
            init_state(f"{key}_{index}_hospital_level", event.get("hospital_level"))
            hospital_ans = st.selectbox("医院/就诊机构类型", options=["请选择", *level_label_by_value.keys()], format_func=lambda v: "请选择" if v == "请选择" else level_label_by_value.get(v, v), key=f"{key}_{index}_hospital_level")
            
            init_state(f"{key}_{index}_disease", event.get("misdiagnosis"))
            disease_ans = st.selectbox("当时被认为是什么疾病？", options=["请选择", *disease_label_by_value.keys()], format_func=lambda v: "请选择" if v == "请选择" else disease_label_by_value.get(v, v), key=f"{key}_{index}_disease")
            
            disease_other_ans = None
            if disease_ans == "other":
                init_state(f"{key}_{index}_disease_other", event.get("misdiagnosis_other") or "")
                disease_other_ans = st.text_input("其他误诊疾病（可不填）", key=f"{key}_{index}_disease_other", help="如填写，请避免加入可识别个人身份的信息。")

            current_events.append({
                "visit_month": f"{int(year_ans):04d}-{int(month_ans):02d}" if year_ans and month_ans else None,
                "care_region": region_ans,
                "hospital_level": hospital_ans if hospital_ans != "请选择" else None,
                "misdiagnosis": disease_ans if disease_ans != "请选择" else None,
                "misdiagnosis_other": disease_other_ans or None,
            })
            
    answers[question.id] = compact_misdiagnosis_events(current_events)

def render_level_map(
    schema: QuestionnaireSchema,
    modules: list[ModuleSchema],
    current_step: int,
    answers: dict[str, Any],
) -> None:
    levels: list[dict[str, Any]] = []
    for index, module in enumerate(modules):
        module_questions = [
            question for question in module.questions if question.type not in NON_DATA_QUESTION_TYPES
        ]
        total = len(module_questions) or 1
        answered = sum(1 for question in module_questions if is_answered(answers.get(question.id), question))
        percent = round(answered / total * 100)
        state = "current" if index == current_step else "done" if percent == 100 else "open"
        levels.append(
            {
                "label": f"{index + 1}\n{module.title or f'模块 {index + 1}'}\n{answered}/{total}",
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
                st.button(
                    level["label"],
                    key=f"level_map_{level_index}",
                    use_container_width=True,
                    on_click=save_current_answers_and_jump,
                    args=(schema, answers, level["target"]),
                )

def save_current_answers_and_jump(schema: QuestionnaireSchema, answers: dict[str, Any], target_step: int) -> None:
    st.session_state[ANSWER_STATE_KEY] = answers
    st.session_state[STEP_STATE_KEY] = target_step
    st.session_state["_scroll_to_top"] = True

def render_module_intro(module: ModuleSchema) -> None:
    title = html.escape(str(module.title or ""))
    description = html.escape(str(module.description or "")).replace("\n", "<br>")
    why = html.escape(str(module.why_we_ask or "")).replace("\n", "<br>")
    why_html = f'<div class="mf-why"><strong>为什么问这个？</strong><div style="margin-top: 0.2rem;">{why}</div></div>' if why else ""
    st.markdown(
        f"""
        <div class="mf-module-intro">
          <h2>{title}</h2>
          <p>{description}</p>
          {why_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

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
            st.session_state["_scroll_to_top"] = True
            st.rerun()
    with next_col:
        label = "进入确认页" if current_step == max_step - 1 else "下一关"
        if st.button(label, type="primary", width="stretch"):
            st.session_state[STEP_STATE_KEY] = min(current_step + 1, max_step)
            st.session_state["_scroll_to_top"] = True
            st.rerun()

def render_review_step(schema: QuestionnaireSchema, answers: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    submitted = bool(st.session_state.pop(SUBMIT_REQUESTED_STATE_KEY, False))
    is_saving = bool(st.session_state.get(SUBMIT_IN_PROGRESS_STATE_KEY))

    st.markdown("### 确认提交")
    st.markdown(
        """
        请在这里停一下，确认是否提交。提交后，本次问卷会生成一条新的匿名记录；
        当前 Beta 版本暂不支持在页面内直接修改已提交答案。若发现明显错误，可以重新提交一份，
        后续整理数据时会结合匿名编号、随访身份和提交时间进行去重或保留最新版。
        """
    )

    missing = missing_required_questions(schema, answers)
    completion = completion_percent(schema, answers)
    st.metric("完成度", f"{completion}%")
    if missing:
        st.warning("还有必填项未完成：" + "、".join(item.label for item in missing))
    else:
        st.success("必填项已完成，可以提交。")

    if is_saving:
        st.info("正在安全保存您的匿名问卷，请不要关闭页面。通常需要几秒钟，网络较慢时可能更久。")

    with st.expander("查看各章节完成情况", expanded=True):
        for module in sorted(schema.modules, key=lambda item: item.order):
            questions = [
                question for question in module.questions if question.type not in NON_DATA_QUESTION_TYPES
            ]
            answered = sum(1 for question in questions if is_answered(answers.get(question.id), question))
            st.write(f"{module.title}：{answered}/{len(questions)}")

    back_col, submit_col = st.columns([1, 1], gap="small")
    with back_col:
        if st.button("返回上一关", width="stretch", disabled=is_saving):
            st.session_state[STEP_STATE_KEY] = max(len(schema.modules) - 1, 0)
            st.session_state["_scroll_to_top"] = True
            st.rerun()
    confirmed = st.checkbox(
        "我已检查答案，并确认提交本次问卷。当前 Beta 版本提交后不能在页面内直接修改。",
        disabled=is_saving,
    )
    with submit_col:
        st.button(
            "正在保存，请稍候" if is_saving else "确认并提交问卷",
            type="primary",
            disabled=bool(missing) or not confirmed or is_saving,
            width="stretch",
            on_click=request_submission,
        )
    return answers, submitted

def request_submission() -> None:
    st.session_state[SUBMIT_REQUESTED_STATE_KEY] = True
    st.session_state[SUBMIT_IN_PROGRESS_STATE_KEY] = True

def clear_submission_in_progress() -> None:
    st.session_state[SUBMIT_IN_PROGRESS_STATE_KEY] = False
    st.session_state.pop(SUBMIT_REQUESTED_STATE_KEY, None)

def reset_saved_submission() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("q_") or key in (
            ANSWER_STATE_KEY,
            STEP_STATE_KEY,
            SUBMISSION_RESULT_STATE_KEY,
        ):
            del st.session_state[key]
    clear_submission_in_progress()

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

def render_subsection(question: QuestionSchema) -> None:
    title = html.escape(str(question.label))
    description = html.escape(str((question.description or ""))).replace("\n", "<br>")
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

def render_nrs_buttons(key: str, anchors: dict[str, str], help_text: str | None, is_disabled: bool = False) -> int | None:
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
        disabled=is_disabled
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

def render_question_header(question: QuestionSchema, index: int | None) -> None:
    required = "必填" if question.required else "可跳过"
    prefix = f"第 {index} 题" if index is not None else "问题"
    st.markdown(
        f"""
        <div class="mf-question-head">
          <span>{prefix}</span>
          <strong>{html.escape(question.label)}</strong>
          <em>{required}</em>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if question.help:
        st.caption(question.help)

def completion_percent(schema: QuestionnaireSchema, answers: dict[str, Any]) -> float:
    questions = [
        question
        for module in schema.modules
        for question in module.questions
        if question.type not in NON_DATA_QUESTION_TYPES
    ]
    if not questions:
        return 0.0
    answered = 0
    for question in questions:
        value = answers.get(question.id)
        if is_answered(value, question):
            answered += 1
    return round(answered / len(questions) * 100, 1)

def missing_required_questions(schema: QuestionnaireSchema, answers: dict[str, Any]) -> list[QuestionSchema]:
    missing: list[QuestionSchema] = []
    for module in schema.modules:
        for question in module.questions:
            if question.required and not is_answered(answers.get(question.id), question):
                missing.append(question)
    return missing

def is_answered(value: Any, question: QuestionSchema) -> bool:
    if is_skipped_answer(value):
        return True
    if question.type == "boolean":
        return value is True
    return value not in (None, "", [])
