from __future__ import annotations

import html
import os
import sys
from contextlib import closing
from pathlib import Path

import streamlit as st

if sys.version_info >= (3, 14):
    st.error(
        "当前部署环境正在使用 Python 3.14。这个项目建议在 Streamlit Community Cloud 的 "
        "Advanced settings 中选择 Python 3.12 后重新部署；repo 里的 runtime.txt "
        "不会替 Cloud app 自动切换 Python 版本。"
    )
    st.stop()

from mf_registry.db import (
    connect,
    count_submissions,
    describe_connection,
    diagnose_retrieval_key,
    diagnostic_table_counts,
    export_rows,
    find_participant_by_retrieval_key,
    init_db,
    save_submission,
)
from mf_registry.export import dataframe_to_csv_bytes, rows_to_dataframe
from mf_registry.identity import FollowupIdentityInput, using_local_pepper
from mf_registry.questionnaire_schema import load_questionnaire, QuestionnaireSchema

from mf_registry.views import render_tnmb_helper_board
from mf_registry.regions import REGIONS

VIEW_REGISTRY = {
    "mf_staging": render_tnmb_helper_board
}
CONTEXT = {
    "regions": REGIONS
}

from mf_registry.renderer_streamlit import (

    SUBMISSION_RESULT_STATE_KEY,
    clear_submission_in_progress,
    completion_percent,
    reset_saved_submission,
    render_questionnaire_wizard,
)


QUESTIONNAIRE_PATH = Path("questionnaires/mf_baseline_2026_05_11.yaml")


st.set_page_config(
    page_title="MF患者共研计划",
    page_icon="MF",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource(show_spinner=False)
def cached_questionnaire(path: str, mtime: float):
    return load_questionnaire(path)


def open_database_connection():
    if postgres_required() and not os.getenv("MF_REGISTRY_DATABASE_URL"):
        raise RuntimeError("MF_REGISTRY_REQUIRE_POSTGRES=true，但未配置 MF_REGISTRY_DATABASE_URL。为避免真实问卷写入临时 SQLite，已阻止保存。")
    connection = connect()
    init_db(connection)
    return connection


def postgres_required() -> bool:
    value = os.getenv("MF_REGISTRY_REQUIRE_POSTGRES", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    configure_runtime_secrets()
    inject_style()
    bundle = cached_questionnaire(str(QUESTIONNAIRE_PATH), QUESTIONNAIRE_PATH.stat().st_mtime)
    requested_page = page_from_query()
    page_labels = ["项目首页", "资料库", "填写问卷", "诊断更新/随访", "找回随访编号", "研究者导出"]
    page = requested_page if requested_page in page_labels else "项目首页"
    apply_step_from_query()

    render_top_nav(page, bundle.version)

    if page == "项目首页":
        render_landing(bundle)
    elif page == "资料库":
        render_resources()
    elif page == "填写问卷":
        render_survey(bundle)
    elif page == "诊断更新/随访":
        render_followup_placeholder()
    elif page == "找回随访编号":
        render_retrieval()
    else:
        render_admin()


def configure_runtime_secrets() -> None:
    for name in (
        "MF_REGISTRY_IDENTITY_PEPPER",
        "MF_REGISTRY_ADMIN_PASSWORD",
        "MF_REGISTRY_SQLITE_PATH",
        "MF_REGISTRY_DATABASE_URL",
        "MF_REGISTRY_REQUIRE_POSTGRES",
    ):
        value = read_secret(name)
        if value and not os.getenv(name):
            os.environ[name] = str(value)


def read_secret(name: str, default: str | None = None) -> str | None:
    try:
        value = st.secrets.get(name, default)
    except Exception:
        return default
    return str(value) if value is not None else default


def page_from_query() -> str:
    page_key = st.query_params.get("page", "")
    return {
        "home": "项目首页",
        "resources": "资料库",
        "survey": "填写问卷",
        "followup": "诊断更新/随访",
        "retrieve": "找回随访编号",
        "admin": "研究者导出",
    }.get(page_key, "项目首页")


def apply_step_from_query() -> None:
    if st.query_params.get("page") != "survey":
        return
    step_value = st.query_params.get("step")
    if step_value is None:
        return
    try:
        st.session_state["survey_step"] = max(int(step_value), 0)
        del st.query_params["step"]
    except ValueError:
        return


def render_top_nav(current_page: str, version: str) -> None:
    nav_items = [
        ("首页", "home", "项目首页", "nav_home"),
        ("资料库", "resources", "资料库", "nav_resources"),
        ("填写问卷", "survey", "填写问卷", "nav_survey"),
        ("随访", "followup", "诊断更新/随访", "nav_followup"),
        ("找回编号", "retrieve", "找回随访编号", "nav_retrieve"),
        ("研究者导出", "admin", "研究者导出", "nav_admin"),
    ]
    nav_forms = []
    for label, key, page_name, button_key in nav_items:
        active = " active" if current_page == page_name else ""
        nav_forms.append(
            f'<form action="/" method="get" target="_self">'
            f'<button class="mf-nav-button{active}" type="submit" name="page" value="{key}">'
            f'{html.escape(label)}'
            f"</button></form>"
        )
    nav_html = (
        '<nav class="mf-top-nav" aria-label="主导航">'
        '<a class="mf-nav-brand" href="/?page=home" target="_self"><span>MF</span><strong>患者共研</strong></a>'
        f'<div class="mf-nav-links">{"".join(nav_forms)}</div>'
        f'<div class="mf-nav-meta">v{html.escape(version)}</div>'
        "</nav>"
    )
    st.markdown(nav_html, unsafe_allow_html=True)


def inject_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --mf-ink: #24313a;
            --mf-muted: #60717a;
            --mf-line: #d9e5df;
            --mf-soft: #f6faf7;
            --mf-mint: #dff2e7;
            --mf-teal: #2f7d68;
            --mf-blue: #4f6f9f;
            --mf-coral: #b65f4a;
            --mf-warm: #fff8ef;
            --mf-paper: #fffdf7;
            --mf-surface: #ffffff;
            --mf-surface-warm: #fffdfa;
            --mf-input-border: rgba(96, 113, 122, 0.42);
            --mf-input-border-strong: rgba(47, 125, 104, 0.62);
            --mf-focus: rgba(47, 125, 104, 0.18);
            --mf-shadow: 0 18px 44px rgba(47, 83, 77, 0.08);
            --mf-photo:
                radial-gradient(circle at 78% 28%, rgba(223, 242, 231, 0.9) 0 15%, transparent 31%),
                radial-gradient(circle at 88% 62%, rgba(255, 248, 239, 0.96) 0 18%, transparent 34%),
                linear-gradient(130deg, rgba(245, 250, 246, 0.95), rgba(238, 247, 241, 0.74) 46%, rgba(248, 244, 232, 0.9));
        }
        html {
            scroll-behavior: smooth;
        }
        body, .stApp {
            background:
                linear-gradient(115deg, rgba(223, 242, 231, 0.56), transparent 34rem),
                linear-gradient(180deg, #fbfcf8 0%, #f3f8f3 100%);
            color: var(--mf-ink);
            font-family: "Avenir Next", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        }
        header[data-testid="stHeader"] {
            display: none;
        }
        #MainMenu, footer {
            visibility: hidden;
        }
        .block-container {
            max-width: 1120px;
            padding-top: 0.75rem;
            padding-bottom: 4rem;
        }
        h1, h2, h3 {
            color: var(--mf-ink);
            letter-spacing: 0 !important;
            font-family: "Songti SC", "STSong", "Noto Serif CJK SC", "Iowan Old Style", Georgia, serif;
        }
        p, li, label, span {
            letter-spacing: 0 !important;
        }
        section[data-testid="stSidebar"] {
            display: none !important;
            width: 0 !important;
        }
        div[data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        div[data-testid="stSidebarContent"] {
            display: none !important;
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--mf-muted);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
            border-bottom: 1px solid var(--mf-line);
            overflow-x: auto;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 0.62rem 0.92rem;
            background: #f4f7f6;
            border: 1px solid transparent;
            color: var(--mf-muted);
            white-space: nowrap;
        }
        .stTabs [aria-selected="true"] {
            background: #ffffff;
            border-color: var(--mf-line);
            border-bottom-color: #ffffff;
            color: var(--mf-teal);
            font-weight: 650;
        }
        div[data-testid="stForm"] {
            border: 0;
            padding: 0;
        }
        div[data-testid="stExpander"] {
            border-color: rgba(217, 229, 223, 0.92);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.72);
            box-shadow: 0 12px 34px rgba(47, 83, 77, 0.04);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, 0.82);
            border-color: var(--mf-line);
            border-radius: 8px;
            box-shadow: var(--mf-shadow);
        }
        div[data-testid="stAlert"] {
            border-radius: 8px;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 8px;
            min-height: 2.75rem;
            font-weight: 650;
            box-shadow: 0 8px 18px rgba(47, 83, 77, 0.06);
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease, background 160ms ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 24px rgba(47, 83, 77, 0.1);
        }
        .stButton > button:focus, .stDownloadButton > button:focus {
            outline: 3px solid var(--mf-focus);
            outline-offset: 2px;
        }
        .stButton > button:disabled, .stDownloadButton > button:disabled {
            opacity: 0.58;
            box-shadow: none;
            transform: none;
        }
        .mf-top-nav {
            width: 100%;
            min-height: 3.45rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.35rem 0 0.7rem 0;
            margin: 0 0 0.85rem 0;
            position: relative;
            z-index: 20;
            background: transparent;
            border-bottom: 1px solid rgba(217, 229, 223, 0.86);
        }
        .mf-nav-brand {
            display: inline-flex;
            align-items: baseline;
            gap: 0.45rem;
            color: var(--mf-ink);
            text-decoration: none !important;
            letter-spacing: 0 !important;
            white-space: nowrap;
        }
        .mf-nav-brand span {
            font-family: "Iowan Old Style", Georgia, serif;
            font-size: 1.15rem;
            font-weight: 850;
            color: var(--mf-teal);
        }
        .mf-nav-brand strong {
            font-size: 0.98rem;
            font-weight: 800;
            color: var(--mf-ink);
        }
        .mf-nav-links {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1.15rem;
            overflow-x: auto;
            scrollbar-width: none;
        }
        .mf-nav-links::-webkit-scrollbar {
            display: none;
        }
        .mf-nav-links form {
            margin: 0;
            padding: 0;
        }
        .mf-nav-button {
            appearance: none;
            border: 0;
            border-radius: 0;
            background: transparent;
            color: var(--mf-muted) !important;
            padding: 0.42rem 0 0.48rem 0;
            font-size: 0.94rem;
            font-weight: 650;
            white-space: nowrap;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: color 160ms ease, border-color 160ms ease, transform 160ms ease;
        }
        .mf-nav-button:hover {
            color: var(--mf-teal) !important;
            transform: translateY(-1px);
        }
        .mf-nav-button.active {
            color: var(--mf-teal) !important;
            border-bottom-color: var(--mf-teal);
        }
        .mf-nav-meta {
            color: var(--mf-muted);
            font-size: 0.86rem;
            white-space: nowrap;
            text-align: right;
            opacity: 0.9;
        }
        .mf-sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {
            min-height: 2.72rem;
            border-radius: 8px !important;
            border: 1px solid var(--mf-input-border) !important;
            background: var(--mf-surface) !important;
            color: var(--mf-ink) !important;
            box-shadow: 0 1px 0 rgba(47, 83, 77, 0.04), 0 8px 20px rgba(47, 83, 77, 0.035);
            transition: border-color 150ms ease, box-shadow 150ms ease, background 150ms ease;
        }
        .stTextArea textarea {
            min-height: 7.5rem;
            line-height: 1.6;
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus,
        .stSelectbox [data-baseweb="select"]:focus-within > div,
        .stMultiSelect [data-baseweb="select"]:focus-within > div {
            border-color: var(--mf-input-border-strong) !important;
            box-shadow: 0 0 0 3px var(--mf-focus), 0 10px 24px rgba(47, 83, 77, 0.07) !important;
        }
        .stSelectbox [data-baseweb="select"] span,
        .stMultiSelect [data-baseweb="select"] span {
            color: var(--mf-ink);
        }
        [data-baseweb="popover"] [role="listbox"] {
            border: 1px solid rgba(96, 113, 122, 0.24);
            border-radius: 8px;
            background: var(--mf-surface);
            box-shadow: 0 18px 40px rgba(47, 83, 77, 0.12);
            overflow: hidden;
        }
        [data-baseweb="popover"] [role="option"] {
            color: var(--mf-ink);
        }
        .stCheckbox label,
        .stRadio label {
            color: var(--mf-ink);
        }
        .stCheckbox label {
            width: fit-content;
            max-width: 100%;
            border: 1px solid rgba(217, 229, 223, 0.95);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.9);
            padding: 0.42rem 0.62rem;
            transition: border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
        }
        .stCheckbox label:hover {
            border-color: rgba(47, 125, 104, 0.38);
            background: #ffffff;
            box-shadow: 0 8px 18px rgba(47, 83, 77, 0.05);
        }
        .stRadio [role="radiogroup"] {
            gap: 0.46rem 0.5rem;
            align-items: center;
        }
        .stRadio [role="radiogroup"] label {
            min-height: 2.35rem;
            border: 1px solid rgba(96, 113, 122, 0.28);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.32rem 0.58rem 0.32rem 0.5rem;
            box-shadow: 0 1px 0 rgba(47, 83, 77, 0.04);
            transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
        }
        .stRadio [role="radiogroup"] label:hover {
            transform: translateY(-1px);
            border-color: rgba(47, 125, 104, 0.42);
            box-shadow: 0 8px 16px rgba(47, 83, 77, 0.06);
        }
        .stSlider [data-baseweb="slider"] {
            padding-top: 0.35rem;
            padding-bottom: 0.55rem;
        }
        div[data-testid="stCaptionContainer"] {
            color: #51646c;
            line-height: 1.55;
        }
        .mf-landing-hero {
            min-height: min(62vh, 32rem);
            width: 100%;
            margin-left: 0;
            margin-top: 0;
            padding: clamp(2rem, 5vw, 5.25rem);
            display: flex;
            align-items: flex-start;
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(90deg, rgba(255, 253, 247, 0.97) 0%, rgba(255, 253, 247, 0.9) 43%, rgba(255, 253, 247, 0.16) 76%),
                linear-gradient(115deg, rgba(223, 242, 231, 0.72), rgba(255, 248, 239, 0.15) 50%, rgba(79, 111, 159, 0.12)),
                var(--mf-photo);
            background-size: cover;
            background-position: center center;
            isolation: isolate;
            animation: mf-photo-breathe 20s ease-in-out infinite alternate;
        }
        .mf-landing-hero::after {
            content: "";
            position: absolute;
            inset: auto 0 0 0;
            height: 34%;
            background: linear-gradient(0deg, rgba(251,252,248,1), rgba(251,252,248,0));
            z-index: -1;
        }
        .mf-landing-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background-image:
                linear-gradient(rgba(47, 125, 104, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(47, 125, 104, 0.04) 1px, transparent 1px),
                linear-gradient(130deg, transparent 51%, rgba(47, 125, 104, 0.1) 51.2%, transparent 51.6%),
                linear-gradient(132deg, transparent 60%, rgba(79, 111, 159, 0.08) 60.2%, transparent 60.7%),
                linear-gradient(126deg, transparent 70%, rgba(182, 95, 74, 0.055) 70.2%, transparent 70.6%);
            background-size: 34px 34px, 34px 34px, 100% 100%, 100% 100%, 100% 100%;
            mask-image: linear-gradient(90deg, rgba(0,0,0,0.75), rgba(0,0,0,0.25), transparent 68%);
            pointer-events: none;
            z-index: -1;
        }
        .mf-hero-copy {
            max-width: 42rem;
            color: var(--mf-ink);
            margin-top: clamp(3rem, 11vh, 6.5rem);
            animation: mf-rise-in 780ms ease-out both;
        }
        .mf-brand {
            margin: 0 0 1rem 0;
            color: var(--mf-ink);
            font-size: clamp(3.25rem, 7.6vw, 6.2rem);
            line-height: 1.02;
            font-weight: 800;
            text-wrap: balance;
            text-shadow: none;
        }
        .mf-hero-copy p {
            max-width: 34rem;
            margin: 0 0 1.6rem 0;
            color: #4b5f5a;
            font-size: clamp(1rem, 1.8vw, 1.22rem);
            line-height: 1.85;
        }
        .mf-hero-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 0.9rem;
            align-items: center;
        }
        .mf-cta-primary, .mf-cta-secondary {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 3rem;
            padding: 0 1.15rem;
            border-radius: 8px;
            text-decoration: none !important;
            font-weight: 750;
            border: 0;
            cursor: pointer;
            transition: transform 180ms ease, background 180ms ease, border-color 180ms ease;
        }
        .mf-cta-primary {
            background: var(--mf-teal);
            color: #fffaf1 !important;
            box-shadow: 0 14px 32px rgba(47, 125, 104, 0.18);
        }
        .mf-cta-secondary {
            border: 1px solid rgba(47, 125, 104, 0.28);
            color: var(--mf-teal) !important;
            background: rgba(255, 253, 247, 0.76);
        }
        .mf-cta-primary:hover, .mf-cta-secondary:hover {
            transform: translateY(-2px);
        }
        .mf-below {
            padding-top: 1.2rem;
        }
        .mf-section {
            padding: 2.2rem 0 3rem 0;
            border-bottom: 1px solid var(--mf-line);
        }
        .mf-section h2 {
            font-size: clamp(1.8rem, 3vw, 2.6rem);
            margin: 0 0 0.8rem 0;
        }
        .mf-section p {
            color: var(--mf-muted);
            line-height: 1.82;
            font-size: 1.02rem;
            margin: 0;
            max-width: 44rem;
        }
        .mf-resource-hero {
            padding: 2.4rem 0 1.6rem 0;
            border-bottom: 1px solid var(--mf-line);
        }
        .mf-resource-hero h1 {
            margin: 0 0 0.8rem 0;
            font-size: clamp(2.6rem, 5vw, 4.8rem);
            line-height: 1.05;
        }
        .mf-resource-hero p {
            color: var(--mf-muted);
            font-size: 1.05rem;
            line-height: 1.82;
            max-width: 48rem;
            margin: 0;
        }
        .mf-resource-section {
            padding: 2.1rem 0;
            border-bottom: 1px solid rgba(217, 229, 223, 0.86);
        }
        .mf-resource-section h2 {
            font-size: clamp(1.6rem, 2.5vw, 2.25rem);
            margin: 0 0 0.5rem 0;
        }
        .mf-resource-section > p {
            color: var(--mf-muted);
            line-height: 1.75;
            max-width: 50rem;
        }
        .mf-resource-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
            margin-top: 1.2rem;
        }
        .mf-resource-item {
            border-top: 2px solid rgba(47, 125, 104, 0.24);
            padding: 0.85rem 0 0 0;
        }
        .mf-resource-item strong {
            display: block;
            color: var(--mf-ink);
            margin-bottom: 0.35rem;
        }
        .mf-resource-item span,
        .mf-resource-item li {
            color: var(--mf-muted);
            line-height: 1.66;
        }
        .mf-resource-list {
            margin: 0.85rem 0 0 0;
            padding-left: 1.15rem;
            color: var(--mf-muted);
            line-height: 1.76;
        }
        .mf-resource-links {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.8rem;
            margin-top: 1.1rem;
        }
        .mf-resource-group {
            margin-top: 1.65rem;
        }
        .mf-resource-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            margin: 0 0 0.2rem 0;
            color: var(--mf-teal);
            font-weight: 760;
            font-size: 0.96rem;
        }
        .mf-resource-note {
            margin: 0;
            color: var(--mf-muted);
            line-height: 1.68;
            max-width: 54rem;
        }
        .mf-resource-link {
            border: 1px solid rgba(217, 229, 223, 0.96);
            border-radius: 8px;
            padding: 0.9rem 1rem;
            background: rgba(255, 255, 255, 0.78);
            text-decoration: none !important;
            transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
        }
        .mf-resource-link:hover {
            transform: translateY(-1px);
            border-color: rgba(47, 125, 104, 0.4);
            box-shadow: 0 10px 24px rgba(47, 83, 77, 0.06);
        }
        .mf-resource-link strong {
            display: block;
            color: var(--mf-teal);
            margin-bottom: 0.25rem;
        }
        .mf-resource-link small {
            display: block;
            color: var(--mf-coral);
            font-weight: 700;
            margin-bottom: 0.3rem;
        }
        .mf-resource-link span {
            color: var(--mf-muted);
            line-height: 1.55;
            font-size: 0.94rem;
        }
        .mf-resource-callout {
            margin-top: 1rem;
            border: 1px solid rgba(182, 95, 74, 0.2);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            background: linear-gradient(180deg, #fff9f5 0%, #fff4ee 100%);
            color: #684335;
            line-height: 1.72;
        }
        .mf-three-col {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }
        .mf-plain-item {
            padding-top: 1rem;
            border-top: 2px solid var(--mf-line);
        }
        .mf-plain-item strong {
            display: block;
            margin-bottom: 0.45rem;
            color: var(--mf-ink);
        }
        .mf-plain-item span {
            color: var(--mf-muted);
            line-height: 1.7;
        }
        .mf-panel {
            border: 1px solid var(--mf-line);
            border-radius: 8px;
            padding: 1.2rem 1.25rem;
            background: #ffffff;
            height: 100%;
        }
        .mf-panel strong {
            color: var(--mf-ink);
        }
        .mf-panel p {
            color: var(--mf-muted);
            line-height: 1.68;
            margin: 0.4rem 0 0 0;
        }
        .mf-intro {
            border: 1px solid var(--mf-line);
            border-left: 5px solid var(--mf-teal);
            border-radius: 8px;
            padding: 1rem 1.1rem;
            background: linear-gradient(180deg, #fbfefb 0%, #f5faf6 100%);
            margin-bottom: 1rem;
        }
        .mf-intro-title {
            color: var(--mf-ink);
            font-weight: 750;
            margin-bottom: 0.3rem;
        }
        .mf-intro-body {
            color: var(--mf-muted);
            line-height: 1.72;
        }
        .mf-why {
            border: 1px solid rgba(79, 111, 159, 0.18);
            border-radius: 8px;
            padding: 0.85rem 1rem;
            background: linear-gradient(180deg, #f6f9ff 0%, #f3f7fc 100%);
            color: #415773;
            margin-bottom: 1rem;
            line-height: 1.65;
        }
        .mf-privacy-note {
            border: 1px solid rgba(182, 95, 74, 0.2);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            background: linear-gradient(180deg, #fff9f5 0%, #fff4ee 100%);
            color: #684335;
            line-height: 1.7;
        }
        .mf-small {
            color: var(--mf-muted);
            font-size: 0.92rem;
            line-height: 1.65;
        }
        .mf-inline-note {
            border: 1px solid rgba(79, 111, 159, 0.16);
            border-radius: 8px;
            padding: 0.82rem 0.95rem;
            background: linear-gradient(180deg, #f6f9ff 0%, #eef6fb 100%);
            color: #35566f;
            line-height: 1.68;
            margin: 1rem 0;
        }
        .mf-inline-note strong {
            display: inline-block;
            color: var(--mf-blue);
            margin-right: 0.45rem;
        }
        .mf-inline-note span {
            color: #35566f;
        }
        .mf-submit-success {
            margin: 1.25rem 0;
            padding: clamp(1rem, 2.2vw, 1.35rem);
            border: 1px solid rgba(47, 125, 104, 0.24);
            border-left: 5px solid var(--mf-teal);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(223, 242, 231, 0.78), rgba(255, 253, 247, 0.95) 56%),
                #ffffff;
            box-shadow: 0 18px 44px rgba(47, 83, 77, 0.08);
        }
        .mf-submit-success h2 {
            margin: 0 0 0.45rem 0;
            color: var(--mf-ink);
            font-size: clamp(1.45rem, 3vw, 2rem);
            line-height: 1.25;
        }
        .mf-submit-success p {
            max-width: 50rem;
            margin: 0;
            color: var(--mf-muted);
            line-height: 1.7;
        }
        .mf-credential-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
            gap: 0.8rem;
            margin-top: 1rem;
        }
        .mf-credential {
            border: 1px solid rgba(96, 113, 122, 0.22);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.85rem;
            box-shadow: 0 8px 20px rgba(47, 83, 77, 0.045);
        }
        .mf-credential.important {
            border-color: rgba(182, 95, 74, 0.38);
            background: linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
        }
        .mf-credential small {
            display: block;
            color: var(--mf-muted);
            font-size: 0.78rem;
            font-weight: 750;
            margin-bottom: 0.25rem;
        }
        .mf-credential strong {
            display: block;
            color: var(--mf-ink);
            font-size: 1rem;
            margin-bottom: 0.55rem;
        }
        .mf-credential code {
            display: block;
            width: 100%;
            border: 1px solid rgba(47, 125, 104, 0.22);
            border-radius: 8px;
            background: #f6faf7;
            color: var(--mf-ink);
            font-size: 1rem;
            line-height: 1.5;
            padding: 0.65rem;
            overflow-wrap: anywhere;
            white-space: pre-wrap;
        }
        .mf-credential.important code {
            border-color: rgba(182, 95, 74, 0.36);
            background: #fffaf4;
        }
        .mf-submit-reminder {
            margin-top: 0.85rem;
            color: #684335;
            font-size: 0.92rem;
            line-height: 1.65;
        }
        .mf-tnmb-board {
            border: 1px solid rgba(79, 111, 159, 0.2);
            border-radius: 8px;
            padding: 1rem;
            margin: 1.25rem 0 0.35rem 0;
            background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
            box-shadow: 0 12px 32px rgba(47, 83, 77, 0.05);
        }
        .mf-tnmb-title {
            color: var(--mf-ink);
            font-weight: 800;
            margin-bottom: 0.25rem;
        }
        .mf-tnmb-note {
            color: var(--mf-muted);
            font-size: 0.9rem;
            line-height: 1.55;
            margin-bottom: 0.85rem;
        }
        .mf-tnmb-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.7rem;
        }
        .mf-tnmb-grid div {
            border-top: 2px solid rgba(79, 111, 159, 0.22);
            padding-top: 0.55rem;
            min-height: 4.2rem;
        }
        .mf-tnmb-grid strong {
            display: block;
            color: var(--mf-blue);
            font-size: 1.05rem;
            margin-bottom: 0.25rem;
        }
        .mf-tnmb-grid span {
            color: var(--mf-ink);
            font-size: 0.9rem;
            line-height: 1.45;
        }
        .mf-tnmb-summary {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-top: 0.85rem;
            color: #415773;
            font-weight: 650;
        }
        .mf-tnmb-summary span {
            border: 1px solid rgba(79, 111, 159, 0.18);
            border-radius: 999px;
            padding: 0.28rem 0.65rem;
            background: rgba(255, 255, 255, 0.72);
        }
        .mf-tnmb-reference {
            margin-top: 1rem;
            border-top: 1px solid rgba(217, 229, 223, 0.9);
            padding-top: 0.95rem;
        }
        .mf-tnmb-reference-title {
            color: var(--mf-ink);
            font-weight: 800;
            margin-bottom: 0.25rem;
        }
        .mf-tnmb-reference-note {
            color: var(--mf-muted);
            font-size: 0.9rem;
            line-height: 1.55;
            margin-bottom: 0.8rem;
        }
        .mf-tnmb-ref-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
        }
        .mf-tnmb-ref-grid div {
            border: 1px solid rgba(217, 229, 223, 0.85);
            border-radius: 8px;
            padding: 0.7rem 0.8rem;
            background: rgba(255, 255, 255, 0.72);
        }
        .mf-tnmb-ref-grid strong {
            display: block;
            color: var(--mf-blue);
            margin-bottom: 0.28rem;
        }
        .mf-tnmb-ref-grid span {
            color: var(--mf-muted);
            font-size: 0.88rem;
            line-height: 1.52;
        }
        .mf-level-map {
            display: grid;
            grid-template-columns: repeat(9, minmax(112px, 1fr));
            gap: 0.5rem;
            overflow-x: auto;
            padding: 0.2rem 0 0.8rem 0;
            margin-bottom: 0.6rem;
        }
        .mf-level-form {
            margin: 0;
            padding: 0;
        }
        .mf-level-fill {
            width: 100%;
            min-height: 4.7rem;
            border: 1px solid var(--mf-line);
            border-radius: 8px;
            padding: 0.62rem 0.62rem;
            text-align: left;
            cursor: pointer;
            position: relative;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.78);
            transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
        }
        .mf-level-fill::before {
            content: "";
            position: absolute;
            inset: auto 0 0 0;
            height: var(--fill);
            background:
                linear-gradient(180deg, rgba(47, 125, 104, 0.12), rgba(47, 125, 104, 0.34));
            border-top: 1px solid rgba(47, 125, 104, 0.18);
            transition: height 220ms ease;
            z-index: 0;
        }
        .mf-level-fill:hover {
            transform: translateY(-2px);
            border-color: rgba(47, 125, 104, 0.42);
            box-shadow: 0 10px 24px rgba(47, 83, 77, 0.08);
        }
        .mf-level-fill.current {
            border-color: rgba(47, 125, 104, 0.62);
            box-shadow: inset 0 0 0 1px rgba(47, 125, 104, 0.2);
        }
        .mf-level-fill.done::before {
            background:
                linear-gradient(180deg, rgba(47, 125, 104, 0.2), rgba(47, 125, 104, 0.52));
        }
        .mf-level-fill span {
            display: inline-flex;
            width: 1.45rem;
            height: 1.45rem;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.76);
            color: var(--mf-teal);
            font-size: 0.78rem;
            font-weight: 850;
            margin-bottom: 0.34rem;
            position: relative;
            z-index: 1;
        }
        .mf-level-fill strong {
            display: block;
            color: var(--mf-ink);
            font-size: 0.88rem;
            white-space: nowrap;
            position: relative;
            z-index: 1;
        }
        .mf-level-fill em {
            display: block;
            margin-top: 0.25rem;
            color: var(--mf-muted);
            font-size: 0.78rem;
            font-style: normal;
            position: relative;
            z-index: 1;
        }
        .mf-level {
            border: 1px solid var(--mf-line);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.66);
            padding: 0.62rem 0.62rem;
            min-height: 4.2rem;
        }
        .mf-level span {
            display: inline-flex;
            width: 1.45rem;
            height: 1.45rem;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: #edf3ef;
            color: var(--mf-muted);
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 0.34rem;
        }
        .mf-level strong {
            display: block;
            color: var(--mf-ink);
            font-size: 0.9rem;
            white-space: nowrap;
        }
        .mf-level em {
            display: block;
            margin-top: 0.25rem;
            color: var(--mf-muted);
            font-size: 0.78rem;
            font-style: normal;
        }
        .mf-level.current {
            border-color: rgba(47, 125, 104, 0.45);
            background: #f4fbf7;
            box-shadow: inset 0 0 0 1px rgba(47, 125, 104, 0.12);
        }
        .mf-level.current span,
        .mf-level.done span {
            background: var(--mf-teal);
            color: #fffaf1;
        }
        .mf-level.done {
            background: rgba(223, 242, 231, 0.55);
        }
        .mf-level-map-native-start + div {
            overflow-x: auto;
            flex-wrap: nowrap !important;
            padding-bottom: 0.65rem;
            margin-bottom: 0.15rem;
        }
        .mf-level-map-native-start + div [data-testid="column"] {
            min-width: 118px;
        }
        .mf-level-map-native-start + div [data-testid="stButton"] > button {
            min-height: 4.5rem;
            white-space: pre-line;
            font-size: 0.86rem;
            line-height: 1.25;
            padding: 0.5rem 0.45rem;
            border-radius: 8px;
            box-shadow: none;
        }
        [class*="st-key-level_map_"] button[data-testid^="stBaseButton"] {
            min-height: 3.95rem;
            white-space: pre-line;
            font-size: 0.94rem;
            line-height: 1.38;
            padding: 0.62rem 0.7rem;
            border-radius: 8px;
            box-shadow: none;
            color: var(--mf-ink);
            border-color: rgba(217, 229, 223, 0.95);
            transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
        }
        [class*="st-key-level_map_"] button[data-testid^="stBaseButton"]:hover {
            transform: translateY(-1px);
            border-color: rgba(47, 125, 104, 0.42);
            box-shadow: 0 10px 24px rgba(47, 83, 77, 0.07);
        }
        .mf-level-map-native-end {
            height: 0.2rem;
        }
        .mf-question-head {
            display: grid;
            grid-template-columns: auto 1fr auto;
            align-items: center;
            gap: 0.78rem;
            margin: 1.3rem 0 0.55rem 0;
            padding: 0.82rem 0.9rem;
            border: 1px solid rgba(217, 229, 223, 0.92);
            border-left: 4px solid rgba(47, 125, 104, 0.5);
            border-radius: 8px;
            background:
                linear-gradient(90deg, rgba(223, 242, 231, 0.5), rgba(255, 255, 255, 0.92) 44%),
                #ffffff;
            box-shadow: 0 8px 20px rgba(47, 83, 77, 0.035);
        }
        .mf-question-head span {
            color: var(--mf-teal);
            font-weight: 850;
            font-size: 0.86rem;
            white-space: nowrap;
        }
        .mf-question-head strong {
            color: var(--mf-ink);
            font-size: 1.02rem;
            line-height: 1.45;
        }
        .mf-question-head em {
            border: 1px solid rgba(47, 125, 104, 0.22);
            border-radius: 999px;
            color: var(--mf-teal);
            font-size: 0.78rem;
            font-style: normal;
            padding: 0.16rem 0.5rem;
            white-space: nowrap;
            background: rgba(223, 242, 231, 0.72);
        }
        .mf-subsection {
            margin: 1.95rem 0 0.75rem;
            padding: 0.85rem 1rem;
            border: 1px solid rgba(217, 229, 223, 0.9);
            border-left: 4px solid rgba(79, 111, 159, 0.42);
            border-radius: 8px;
            background:
                linear-gradient(90deg, rgba(246, 250, 247, 0.98), rgba(255, 253, 247, 0.64)),
                var(--mf-surface-warm);
        }
        .mf-subsection strong {
            display: block;
            color: var(--mf-ink);
            font-size: 1.08rem;
            font-weight: 780;
            letter-spacing: 0 !important;
        }
        .mf-subsection span {
            display: block;
            max-width: 48rem;
            margin-top: 0.22rem;
            color: var(--mf-muted);
            line-height: 1.65;
            font-size: 0.94rem;
        }
        .mf-nrs-anchors {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            margin: 0.15rem 0 0.55rem;
            color: var(--mf-muted);
            font-size: 0.88rem;
            max-width: 44rem;
        }
        .mf-nrs-current {
            width: fit-content;
            margin-top: 0.1rem;
            padding: 0.28rem 0.55rem;
            border-radius: 8px;
            background: rgba(223, 242, 231, 0.72);
            color: var(--mf-muted);
            font-size: 0.9rem;
        }
        .mf-nrs-current strong {
            color: var(--mf-teal);
        }
        @keyframes mf-photo-breathe {
            from { background-position: center center; }
            to { background-position: 52% center; }
        }
        @keyframes mf-rise-in {
            from {
                opacity: 0;
                transform: translateY(16px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        @media (max-width: 760px) {
            .block-container {
                padding-top: 0.75rem;
            }
            .mf-top-nav {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.55rem;
            }
            .mf-nav-links {
                width: 100%;
                justify-content: flex-start;
                gap: 1rem;
            }
            .mf-nav-meta {
                text-align: left;
            }
            .mf-landing-hero {
                min-height: 72vh;
                margin-left: 0;
                padding: 5rem 1.25rem 4rem;
                background:
                    linear-gradient(180deg, rgba(255, 250, 241, 0.94) 0%, rgba(255, 250, 241, 0.82) 52%, rgba(255, 250, 241, 0.24) 100%),
                    var(--mf-photo);
                background-size: cover;
                background-position: 48% center;
            }
            .mf-brand {
                font-size: 3.15rem;
            }
            .mf-hero-copy {
                margin-top: 1.4rem;
            }
            .mf-hero-actions {
                align-items: stretch;
                flex-direction: column;
            }
            .mf-three-col {
                grid-template-columns: 1fr;
                gap: 1.35rem;
            }
            .mf-resource-grid,
            .mf-resource-links {
                grid-template-columns: 1fr;
            }
            .mf-level-map {
                grid-template-columns: repeat(9, 132px);
            }
            .mf-level-map-native-start + div [data-testid="column"] {
                min-width: 132px;
            }
            .mf-question-head {
                grid-template-columns: 1fr;
                gap: 0.3rem;
            }
            .mf-question-head em {
                width: fit-content;
            }
            .mf-tnmb-grid {
                grid-template-columns: 1fr;
            }
            .mf-tnmb-ref-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_landing(bundle) -> None:
    st.markdown(
        """
        <section class="mf-landing-hero">
          <div class="mf-hero-copy">
            <h1 class="mf-brand">MF 患者共研计划</h1>
            <p>
              用一份温和、可随访的问卷，把诊断前后的真实经历记录下来，
              让蕈样肉芽肿研究更接近患者生活。
            </p>
            <form class="mf-hero-actions" action="/" method="get" target="_self">
              <button class="mf-cta-primary" type="submit" name="page" value="survey">开始填写问卷</button>
              <button class="mf-cta-secondary" type="submit" name="page" value="resources">先看资料库</button>
              <button class="mf-cta-secondary" type="submit" name="page" value="retrieve">找回随访编号</button>
            </form>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <main class="mf-below">
          <section class="mf-section">
            <h2>这份问卷只做一件事</h2>
            <p>
              把患者自己知道的诊断时间线、TNMB/mSWAT、瘙痒睡眠负担和治疗康复节奏，
              按照可以分析、可以随访、可以被伦理审查的方式整理起来。
              当前问卷版本为 {html.escape(bundle.version)}，用于 Beta 试用和问卷流程优化。
            </p>
          </section>
          <section class="mf-section">
            <h2>保护感比完成率更重要</h2>
            <p>
              请不要填写姓名、身份证号、手机号、详细住址、医院内部编号或报告原件。
              长期随访身份完全自愿；如果开启，微信号只用于生成哈希身份，不进入研究导出表。
            </p>
            <div class="mf-three-col">
              <div class="mf-plain-item"><strong>可以不确定</strong><span>记不清年月、看不懂报告，都可以选择不确定。</span></div>
              <div class="mf-plain-item"><strong>可以跳过</strong><span>非必填题不会阻止提交，体验优先于逼迫。</span></div>
              <div class="mf-plain-item"><strong>共同完善</strong><span>Beta 试用会帮助我们发现措辞、流程和数据结构里的问题。</span></div>
            </div>
          </section>
        </main>
        """,
        unsafe_allow_html=True,
    )


def render_resources() -> None:
    st.markdown(
        """
        <section class="mf-resource-hero">
          <h1>MF 患者资料库</h1>
          <p>
            这里整理常见问题、就诊准备、分期和治疗资料。它不是医疗建议，
            也不能替代您的医生；它的作用是帮助您更安心地理解问卷、整理病情、准备复诊。
          </p>
        </section>

        <section class="mf-resource-section">
          <h2>先读这几件事</h2>
          <div class="mf-resource-grid">
            <div class="mf-resource-item">
              <strong>MF 是皮肤 T 细胞淋巴瘤的一种</strong>
              <span>它常表现为斑片、斑块、瘙痒、脱屑或结节，早期可能像湿疹、银屑病或副银屑病。</span>
            </div>
            <div class="mf-resource-item">
              <strong>确诊慢并不少见</strong>
              <span>很多患者需要反复就诊和多次皮肤活检。记不清时间不代表填错，可以选择“不确定”。</span>
            </div>
            <div class="mf-resource-item">
              <strong>分期和 mSWAT 是两件事</strong>
              <span>TNMB 用于临床分期；mSWAT 主要用于量化皮肤负担和随访变化。</span>
            </div>
            <div class="mf-resource-item">
              <strong>很多信息需要医生确认</strong>
              <span>N、M、B 分期通常需要查体、影像、病理或血液流式。自填估算只能帮助整理线索。</span>
            </div>
          </div>
          <div class="mf-resource-callout">
            如果出现快速增大的肿块、破溃感染、发热、明显淋巴结肿大、全身皮肤广泛发红脱屑、
            或症状突然明显加重，请尽快联系医生或线下就医。
          </div>
        </section>

        <section class="mf-resource-section">
          <h2>填写问卷时常见问题</h2>
          <ul class="mf-resource-list">
            <li><strong>不知道年月怎么办？</strong> 选大概年月即可；完全记不清就选“不确定”。</li>
            <li><strong>不确定自己是不是 MF？</strong> 可以按医生说法填写“怀疑/未确诊”，研究者会在分析时分层。</li>
            <li><strong>医院名称要不要写？</strong> 当前 beta 不建议写医院全名或详细个人信息，填写医院层级和地区即可。</li>
            <li><strong>活检次数怎么算？</strong> 大致计算为为了这次皮肤问题做过的皮肤活检次数，不需要精确。</li>
            <li><strong>mSWAT 面积怎么估？</strong> 一个手掌加五指约等于 1% 全身皮肤面积，粗略估算即可。</li>
            <li><strong>TNMB 不会填怎么办？</strong> 只填您知道的部分；N、M、B 不确定非常常见。</li>
            <li><strong>提交后能修改吗？</strong> 当前 beta 暂不支持直接修改。发现明显错误可以重新提交，后续导出时会去重。</li>
          </ul>
        </section>

        <section class="mf-resource-section">
          <h2>下次就诊可以带上的清单</h2>
          <div class="mf-resource-grid">
            <div class="mf-resource-item">
              <strong>时间线</strong>
              <span>第一次发现皮肤异常、第一次看皮肤科、第一次活检、首次确诊、治疗开始和复发时间。</span>
            </div>
            <div class="mf-resource-item">
              <strong>报告</strong>
              <span>皮肤活检病理、免疫组化、TCR 克隆性、血常规、流式细胞术、影像、淋巴结活检。</span>
            </div>
            <div class="mf-resource-item">
              <strong>照片</strong>
              <span>同一光线和距离下记录皮损变化，尤其是新发结节、破溃或红皮病变化。</span>
            </div>
            <div class="mf-resource-item">
              <strong>治疗表</strong>
              <span>药名、剂量/频率、开始和停止时间、多久好转、是否复发、为什么换药。</span>
            </div>
          </div>
        </section>

        <section class="mf-resource-section">
          <h2>可以问医生的问题</h2>
          <ul class="mf-resource-list">
            <li>我的诊断是 MF、Sézary 综合征，还是其他 CTCL 亚型？是否有亲毛囊型、大细胞转化、CD30 阳性等特征？</li>
            <li>我的 TNMB 分期分别是什么？T、N、M、B 哪些已经确认，哪些还需要检查？</li>
            <li>我目前的 mSWAT 或皮肤受累面积大约是多少？以后随访是否会重复记录？</li>
            <li>是否需要复查皮肤活检、TCR、血液流式、LDH、影像或淋巴结评估？</li>
            <li>当前治疗目标是什么：控制瘙痒、减少皮损、维持缓解，还是处理进展风险？</li>
            <li>治疗多久通常能判断是否有效？什么情况下需要调整方案？</li>
            <li>如果好转后复发，下一步通常如何处理？需要记录哪些复发信息？</li>
            <li>哪些症状需要尽快联系医生，而不是等到下次复诊？</li>
          </ul>
        </section>

        <section class="mf-resource-section">
          <h2>可信资料入口</h2>
          <p>优先阅读医学机构、专业组织、正式指南和登记平台资料。不同国家药物可及性、医保和临床试验不同，治疗选择仍需和本地医生讨论。</p>

          <div class="mf-resource-group">
            <div class="mf-resource-kicker">中文 · 中国大陆资料</div>
            <p class="mf-resource-note">适合了解国内临床语境、指南/共识、就医路径和正在登记的研究。正式诊疗仍以医生和原始病历为准。</p>
            <div class="mf-resource-links">
              <a class="mf-resource-link" href="https://jrd.pumch.cn/article/doi/10.12376/j.issn.2097-0501.2023.02.008" target="_blank">
                <small>专家指南</small>
                <strong>中国蕈样肉芽肿诊疗及管理专家指南</strong>
                <span>国内专家组整理的诊断、分期、治疗和长期管理建议，适合研究团队核对本土问卷术语。</span>
              </a>
              <a class="mf-resource-link" href="https://www.pumch.cn/detail/13407.html" target="_blank">
                <small>医院信息</small>
                <strong>北京协和医院皮肤肿瘤门诊介绍</strong>
                <span>帮助患者理解皮肤肿瘤/皮肤淋巴瘤相关专病门诊和就诊准备方向。</span>
              </a>
              <a class="mf-resource-link" href="https://www.chinadrugtrials.org.cn/" target="_blank">
                <small>官方登记平台</small>
                <strong>国家药物临床试验登记与信息公示平台</strong>
                <span>可检索“蕈样肉芽肿”“皮肤T细胞淋巴瘤”“CTCL”等关键词，查看国内药物临床试验登记。</span>
              </a>
              <a class="mf-resource-link" href="https://www.chictr.org.cn/" target="_blank">
                <small>研究登记</small>
                <strong>中国临床试验注册中心 ChiCTR</strong>
                <span>可检索观察性研究、真实世界研究和非药物干预研究登记，适合了解国内研究动态。</span>
              </a>
              <a class="mf-resource-link" href="https://m.dayi.org.cn/qa/01a12d9e312c43b18a9587647d58ec11" target="_blank">
                <small>患者科普</small>
                <strong>中国医学科学院健康科普：蕈样肉芽肿</strong>
                <span>中文问答式科普，适合初次了解疾病名称、常见表现和就医方向。</span>
              </a>
            </div>
          </div>

          <div class="mf-resource-group">
            <div class="mf-resource-kicker">中文 · 国际机构中文版</div>
            <p class="mf-resource-note">这些资料语言友好，但治疗可及性可能按国外语境书写；阅读时请和国内医生建议对照。</p>
            <div class="mf-resource-links">
              <a class="mf-resource-link" href="https://www.msdmanuals.cn/home/blood-disorders/lymphomas/cutaneous-t-cell-lymphomas" target="_blank">
                <small>患者版</small>
                <strong>MSD 手册：皮肤 T 细胞淋巴瘤</strong>
                <span>用中文解释 CTCL、MF 和 Sézary 综合征的症状、诊断和治疗概念。</span>
              </a>
              <a class="mf-resource-link" href="https://www.msdmanuals.cn/professional/hematology-and-oncology/lymphomas/cutaneous-t-cell-lymphomas-ctcl" target="_blank">
                <small>专业版</small>
                <strong>MSD 专业版：CTCL</strong>
                <span>更偏医生视角，适合想核对检查、分型和治疗术语的患者或志愿者。</span>
              </a>
            </div>
          </div>

          <div class="mf-resource-group">
            <div class="mf-resource-kicker">English resources</div>
            <p class="mf-resource-note">适合查 TNMB、mSWAT、国际患者组织资料和英文病历术语。英文内容不等于国内可直接获得同样治疗。</p>
            <div class="mf-resource-links">
              <a class="mf-resource-link" href="https://www.cancer.gov/types/lymphoma/patient/mycosis-fungoides-treatment-pdq" target="_blank">
                <small>Patient guideline</small>
                <strong>NCI Patient PDQ</strong>
                <span>MF / Sézary syndrome diagnosis, staging, treatment options, and clinical trial overview.</span>
              </a>
              <a class="mf-resource-link" href="https://www.clfoundation.org/mycosis-fungoides" target="_blank">
                <small>Patient foundation</small>
                <strong>Cutaneous Lymphoma Foundation：MF</strong>
                <span>Patient-friendly explanations of MF, disease course, treatment, and living with cutaneous lymphoma.</span>
              </a>
              <a class="mf-resource-link" href="https://www.clfoundation.org/modified-severity-weighted-assessment-tool-mswat" target="_blank">
                <small>Assessment tool</small>
                <strong>mSWAT explanation</strong>
                <span>Explains how patch, plaque, and tumor body-surface areas are combined into an mSWAT score.</span>
              </a>
              <a class="mf-resource-link" href="https://www.ncbi.nlm.nih.gov/books/NBK65849.2/table/CDR0000062881__216/?report=objectonly" target="_blank">
                <small>TNMB table</small>
                <strong>ISCL/EORTC TNMB classification</strong>
                <span>Useful for checking the official T/N/M/B definitions used in MF and Sézary syndrome staging.</span>
              </a>
              <a class="mf-resource-link" href="https://dermnetnz.org/topics/mycosis-fungoides" target="_blank">
                <small>Dermatology reference</small>
                <strong>DermNet：Mycosis fungoides</strong>
                <span>Dermatology-focused overview of clinical features, diagnosis, differential diagnosis, and treatment.</span>
              </a>
              <a class="mf-resource-link" href="https://www.clfoundation.org/patient-resources-0" target="_blank">
                <small>Support</small>
                <strong>Patient support resources</strong>
                <span>Patient organizations, glossaries, clinical trial resources, and community support links.</span>
              </a>
              <a class="mf-resource-link" href="https://www.lls.org/booklet/cutaneous-t-cell-lymphoma" target="_blank">
                <small>Booklet</small>
                <strong>LLS CTCL booklet</strong>
                <span>A structured patient booklet for understanding cutaneous T-cell lymphoma and treatment choices.</span>
              </a>
              <a class="mf-resource-link" href="https://med.stanford.edu/cutaneouslymphoma/education/patient-resources.html" target="_blank">
                <small>Academic center</small>
                <strong>Stanford patient resources</strong>
                <span>Lists reliable resources and reminds patients to be careful with unscreened online information.</span>
              </a>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_submission_success(saved, database_status=None) -> None:
    cards = [
        ("匿名编号", "以后与研究团队沟通、核对提交记录时使用", saved.public_code)
    ]
    reminder = "请同时保存匿名编号和找回密钥。找回密钥不会以明文保存，系统之后无法替您查看原文。"

    if saved.followup_public_key:
        cards.append(
            (
                "Public key",
                "可公开用于研究匹配，不等同于联系方式",
                saved.followup_public_key,
            )
        )
        if saved.retrieval_key:
            cards.append(
                (
                    "找回密钥",
                    "只显示这一次，请像保存密码一样保存",
                    saved.retrieval_key,
                )
            )
            reminder = "找回密钥不会以明文保存，系统之后无法替您查看原文。"
        else:
            reminder = "检测到同一随访身份已存在，本次答案已关联到原有匿名参与者。"

    st.success("感谢您完成这份问卷")
    st.write("您的回答会帮助我们把 MF 患者的诊断经历、分期线索、治疗反应和真实需求整理得更清楚。下面是本次提交后需要保存的信息。")
    columns = st.columns(len(cards), gap="small")
    for column, (title, description, value) in zip(columns, cards):
        with column:
            with st.container(border=True):
                st.caption(title)
                st.markdown(f"**{description}**")
                st.code(value)
    st.info(reminder)
    if database_status:
        if database_status.configured and database_status.healthy:
            st.caption(f"已保存到 {database_status.backend}。")
        else:
            st.warning("本次提交没有保存到 Supabase/Postgres，而是保存到了本地开发数据库。部署试用时请检查 Streamlit secrets 中的 MF_REGISTRY_DATABASE_URL。")


def render_survey(bundle) -> None:
    st.title(bundle.title)
    description = bundle.schema.questionnaire.description
    if description:
        st.caption(description)

    with st.expander("参与说明", expanded=True):
        st.markdown(
            """
            <div class="mf-privacy-note">
              请把这份问卷当成一次患者共研的 Beta 试用，而不是医疗咨询。
              任何让您不舒服、不确定或不想回答的问题，都可以先跳过。
              这份问卷不会提供诊断或治疗建议。
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            - 这是一份患者共研问卷，不提供诊断或治疗建议。
            - 请不要填写任何可直接识别个人身份的信息。
            - 系统会为每次提交生成匿名随访身份；请保存 retrieval key，用于未来诊断更新或随访。
            - Beta 阶段暂不收集微信号或其他联系方式；未来如果开放随访提醒，会单独征求同意。
            - 您可以随时停止填写。
            - 提交后，系统会保存您的匿名答案，用于完善问卷结构、导出和后续随访流程。
            - Beta 试用阶段的数据会在分析时明确标记问卷版本和收集阶段。
            """
        )
        consent = st.checkbox("我已阅读并同意参与本次问卷 Beta 试用", key="consent")

    if not consent:
        st.warning("请先阅读并勾选参与说明。")
        return

    followup_identity = render_followup_identity()

    saved_result = st.session_state.get(SUBMISSION_RESULT_STATE_KEY)
    if saved_result:
        saved, database_status = saved_result
        render_submission_success(saved, database_status)
        st.button("填写另一份问卷", on_click=reset_saved_submission)
        return

    answers, submitted = render_questionnaire_wizard(bundle.schema, view_registry=VIEW_REGISTRY, context=CONTEXT)

    if submitted:
        missing_required = find_missing_required(bundle.schema, answers)
        if missing_required:
            clear_submission_in_progress()
            st.error("以下必填问题尚未完成：" + "、".join(missing_required))
            return

        completion = completion_percent(bundle.schema, answers)
        st.info("正在安全保存您的匿名问卷，请不要关闭页面。通常需要几秒钟，网络较慢时可能更久。")
        try:
            with st.spinner("正在写入安全数据库..."):
                with closing(open_database_connection()) as connection:
                    saved = save_submission(connection, bundle, answers, completion, followup_identity=followup_identity)
                    database_status = describe_connection(connection)
        except Exception as error:
            clear_submission_in_progress()
            st.error("暂时无法保存问卷。请稍后再试，或联系研究者检查数据库连接。")
            with st.expander("技术信息"):
                st.code(str(error))
            return
        st.session_state[SUBMISSION_RESULT_STATE_KEY] = (saved, database_status)
        clear_submission_in_progress()
        st.rerun()


def render_followup_identity() -> FollowupIdentityInput | None:
    with st.container(border=True):
        st.markdown("### 匿名随访身份与提醒")
        if using_local_pepper():
            st.info("当前使用本地测试密钥。正式部署时请配置 MF_REGISTRY_IDENTITY_PEPPER，确保找回密钥哈希稳定。")
        st.markdown(
            """
            <div class="mf-intro">
              <div class="mf-intro-title">匿名随访身份会自动生成</div>
              <div class="mf-intro-body">
                提交后每位参与者都会得到 public key 和 retrieval key。
                未来填写诊断更新或随访问卷时，可以用 retrieval key 连接到同一位匿名参与者；
                这不需要提供微信号或其他联系方式。
              </div>
            </div>
            """
            ,
            unsafe_allow_html=True,
        )
        st.caption("Beta 阶段暂不收集微信号或其他联系方式。随访提醒需要单独的伦理说明、可撤回同意和安全的联系方式保存方案，之后再开放。")
        return None


def render_retrieval() -> None:
    st.title("找回随访编号")
    st.markdown(
        """
        如果您之前选择了长期随访，并保存了 retrieval key，可以在这里找回自己的匿名编号和 public key。
        retrieval key 类似密码；系统不会显示您的微信号，也不会保存明文 retrieval key。
        """
    )
    retrieval_key = st.text_input("Retrieval key", type="password")
    if st.button("查找", type="primary"):
        if not retrieval_key.strip():
            st.warning("请先输入 retrieval key。")
            return
        try:
            with closing(open_database_connection()) as connection:
                row = find_participant_by_retrieval_key(connection, retrieval_key)
        except Exception:
            st.error("暂时无法连接数据库。请稍后再试，或联系研究者检查部署配置。")
            return
        if not row:
            st.error("没有找到对应记录。请检查 retrieval key 是否完整。")
            return
        st.success("已找到您的随访身份。")
        st.write("匿名编号：")
        st.code(row["public_code"])
        st.write("Public key：")
        st.code(row["public_key"])


def render_followup_placeholder() -> None:
    st.title("诊断更新 / 随访")
    st.caption("这个入口用于未来的纵向随访和“疑似转确诊”更新。目前是 Beta 占位页，暂不提交数据。")

    st.markdown(
        """
        <div class="mf-intro">
          <div class="mf-intro-title">如果之后正式确诊，请不要重新作为新用户填写基线问卷</div>
          <div class="mf-intro-body">
            正确做法是使用第一次提交后保存的 retrieval key 找回同一位参与者，
            然后追加一份诊断更新或随访问卷。这样既保留“最初是疑似”的真实历史，
            也能记录“后来被确诊”的时间和依据。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_update, col_followup = st.columns(2, gap="medium")
    with col_update:
        st.markdown("### 诊断更新")
        st.markdown(
            """
            未来会用于记录：
            - 是否从疑似变为正式诊断
            - 首次确诊年月
            - 确诊依据和活检次数
            - 医生给出的分期或 TNMB 更新
            """
        )
    with col_followup:
        st.markdown("### 定期随访")
        st.markdown(
            """
            未来会用于记录：
            - 最近三个月病情变化
            - 皮肤面积、瘙痒和睡眠变化
            - 新治疗、停药、复发或反跳
            - 新检查或分期信息
            """
        )

    st.info("Beta 阶段请先保存好提交后的 retrieval key。正式随访入口开放后，它会用来把新记录连接到同一位匿名参与者。")
    st.link_button("先找回随访编号", "/?page=retrieve", width="stretch")


def render_admin() -> None:
    st.title("研究者导出")

    admin_password = os.getenv("MF_REGISTRY_ADMIN_PASSWORD")
    if not admin_password:
        st.warning("研究者导出暂未开放。请先配置 MF_REGISTRY_ADMIN_PASSWORD。")
        return

    if not st.session_state.get("admin_export_unlocked"):
        st.caption("登录后可查看数据库连接状态、提交数量和导出数据。")
        with st.form("admin_export_login"):
            entered = st.text_input("研究者密码", type="password")
            submitted = st.form_submit_button("查看导出", type="primary")
        if not submitted:
            st.info("请输入研究者密码后查看导出。")
            return
        if entered != admin_password:
            st.error("密码不正确，请重新输入。")
            return
        st.session_state["admin_export_unlocked"] = True
        st.rerun()

    try:
        with closing(open_database_connection()) as connection:
            render_database_status(connection)

            if st.button("锁定导出页"):
                st.session_state["admin_export_unlocked"] = False
                st.rerun()

            render_retrieval_key_diagnostic(connection)
            rows = export_rows(connection)
    except Exception as error:
        st.error("暂时无法连接数据库。请检查 Streamlit secrets、Supabase 项目状态和数据库 URL。")
        with st.expander("技术信息"):
            st.code(str(error))
        return

    dataframe = rows_to_dataframe(rows)
    st.metric("已提交问卷", len(dataframe))

    if dataframe.empty:
        st.info("目前还没有可导出的提交。")
        return

    st.dataframe(dataframe, width="stretch", hide_index=True)
    st.download_button(
        "下载 CSV",
        data=dataframe_to_csv_bytes(dataframe),
        file_name="mf_registry_export.csv",
        mime="text/csv",
    )


def render_retrieval_key_diagnostic(connection) -> None:
    with st.expander("按 retrieval key 检查一条提交", expanded=False):
        retrieval_key = st.text_input("Retrieval key", type="password", key="admin_retrieval_diagnostic")
        if not st.button("检查 retrieval key", key="admin_retrieval_diagnostic_button"):
            return
        if not retrieval_key.strip():
            st.warning("请先输入 retrieval key。")
            return
        row = diagnose_retrieval_key(connection, retrieval_key)
        if not row:
            st.error("当前数据源中没有找到这个 retrieval key。请检查提交成功页和研究者导出页是否连接到同一个数据库。")
            return
        st.success("当前数据源可以找到这个 retrieval key。")
        st.write(
            {
                "public_code": row["public_code"],
                "public_key": row["public_key"],
                "session_count": row["session_count"],
                "submitted_session_count": row["submitted_session_count"],
                "answer_count": row["answer_count"],
                "derived_count": row["derived_count"],
            }
        )


def render_database_status(connection) -> None:
    status = describe_connection(connection)
    status_label = "正常" if status.healthy else "异常"
    backend_help = "已配置 MF_REGISTRY_DATABASE_URL" if status.configured else "未配置 MF_REGISTRY_DATABASE_URL，使用本地开发数据库"
    col_backend, col_health, col_count = st.columns(3, gap="small")
    with col_backend:
        st.metric("数据后端", status.backend)
        st.caption(backend_help)
    with col_health:
        st.metric("连接状态", status_label)
        st.caption(status.message)
    with col_count:
        try:
            submission_count = count_submissions(connection)
        except Exception:
            submission_count = 0
        st.metric("当前提交数", submission_count)
        st.caption("来自当前连接的数据源")
    st.caption(f"连接目标：{status.target}")
    if not status.configured:
        st.info("当前仍在使用本地 SQLite。部署到 Supabase 时，请在 Streamlit secrets 中配置 MF_REGISTRY_DATABASE_URL。")
    elif not status.healthy:
        st.error("Supabase/Postgres 已配置，但连接检查失败。请检查数据库 URL、密码、网络和 Supabase 项目状态。")
    else:
        st.success("Supabase/Postgres 连接正常，问卷提交和导出会使用该数据源。")

    with st.expander("数据表计数", expanded=False):
        try:
            counts = diagnostic_table_counts(connection)
        except Exception as error:
            st.error(f"无法读取数据表计数：{error}")
            return
        count_cols = st.columns(4, gap="small")
        for index, (table, count) in enumerate(counts.items()):
            with count_cols[index % len(count_cols)]:
                st.metric(table, count)


def find_missing_required(schema: QuestionnaireSchema, answers: dict) -> list[str]:
    from mf_registry.renderer_streamlit import is_answered
    missing: list[str] = []
    for module in schema.modules:
        for question in module.questions:
            if not question.required:
                continue
            if not is_answered(answers.get(question.id), question):
                missing.append(question.label)
    return missing


if __name__ == "__main__":
    main()
