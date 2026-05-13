from typing import Any
import html
import streamlit as st
from mf_registry.derived import estimate_mswat, estimate_skin_t_stage, estimate_tnmb_hint
from mf_registry.questionnaire_schema import ModuleSchema
from mf_registry.renderer_streamlit import numeric_value

TNMB_COMPONENT_LABELS = {
    "tx": "Tx：皮肤信息不足",
    "t1": "T1：斑片/斑块 <10%",
    "t2": "T2：斑片/斑块 >=10%",
    "t3": "T3：存在皮肤肿瘤",
    "t4": "T4：红皮病/极广泛受累",
    "nx": "Nx：淋巴结信息不足",
    "n0": "N0：无异常",
    "n1_or_n2": "N1/N2：未结构破坏",
    "n3": "N3：结构破坏/明显受累",
    "mx": "Mx：内脏信息不足",
    "m0": "M0：无内脏受累",
    "m1": "M1：内脏受累",
    "bx": "Bx：血液信息不足",
    "bx_abnormal": "Bx：血液异常分级不足",
    "b0": "B0：无明显血液受累",
    "b1": "B1：低水平受累",
    "b2": "B2：高水平受累",
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

def render_tnmb_helper_board(answers: dict[str, Any], module: ModuleSchema, context: dict[str, Any] = None) -> None:
    patch_bsa = numeric_value(answers.get("mswat_patch_bsa_percent"))
    plaque_bsa = numeric_value(answers.get("mswat_plaque_bsa_percent"))
    tumor_bsa = numeric_value(answers.get("mswat_tumor_bsa_percent"))
    node_status = answers.get("tnmb_node_status_self_reported")
    visceral_status = answers.get("tnmb_visceral_status_self_reported")
    blood_status = answers.get("tnmb_blood_status_self_reported")

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

