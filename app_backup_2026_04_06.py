"""
app.py —— Streamlit Web UI 入口
运行方式：streamlit run app.py

页面结构：
  - 顶部：平台头部与状态
  - 中部左侧：问题历史
  - 中部右侧：结果主屏
  - 底部：统一输入入口
"""

from __future__ import annotations

import html
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from src import db
from src.workflow import router


PAGE_TITLE = "Data Analyze Agent"


def inject_styles(layout: dict) -> None:
    """注入编辑型分析助手首页样式。"""
    css = """
        <style>
        :root {
          --bg: #f5f7fb;
          --bg-accent:
            radial-gradient(circle at top right, rgba(47, 92, 243, 0.10), transparent 24%),
            radial-gradient(circle at top left, rgba(17, 24, 39, 0.05), transparent 28%),
            linear-gradient(180deg, #f8faff 0%, #f3f6fc 52%, #f7f9fd 100%);
          --surface: rgba(255, 251, 247, 0.94);
          --surface-strong: #fffdf9;
          --surface-muted: #edf2fb;
          --surface-soft: #f3f7ff;
          --text: #111827;
          --text-soft: #5f6b7b;
          --line: rgba(17, 24, 39, 0.10);
          --line-strong: rgba(17, 24, 39, 0.18);
          --accent: #2F5CF3;
          --accent-soft: #e9efff;
          --accent-ink: #1838b8;
          --accent-secondary: #1f2a44;
          --success: #2f6b57;
          --danger: #8b4b4b;
          --shadow-lg: 0 28px 64px rgba(17, 24, 39, 0.10);
          --shadow-md: 0 18px 38px rgba(17, 24, 39, 0.08);
          --shadow-sm: 0 10px 24px rgba(17, 24, 39, 0.05);
          --radius-2xl: 28px;
          --radius-xl: 22px;
          --radius-lg: 18px;
          --radius-md: 14px;
          --workspace-title-size: __WORKSPACE_TITLE_SIZE__rem;
          --summary-title-size: __SUMMARY_TITLE_SIZE__rem;
          --summary-copy-size: __SUMMARY_COPY_SIZE__rem;
          --summary-hero-padding: __SUMMARY_HERO_PADDING__rem;
          --metric-card-padding-y: __METRIC_CARD_PADDING_Y__rem;
          --metric-card-padding-x: __METRIC_CARD_PADDING_X__rem;
          --metric-value-size: __METRIC_VALUE_SIZE__rem;
        }

        .stApp {
          background: var(--bg-accent);
          color: var(--text);
        }

        div[data-testid="stHeader"] {
          background: transparent;
        }

        .block-container {
          max-width: 1080px;
          padding-top: 1.42rem;
          padding-bottom: 1.2rem;
          margin-left: auto;
          margin-right: auto;
        }

        .top-shell {
          width: 100%;
          max-width: none;
          padding: 0.25rem 0 0.15rem;
          margin-top: 0.06rem;
          border-radius: 0;
          background: transparent;
          border: none;
          box-shadow: none;
        }

        .shell-title {
          margin: 0;
          color: var(--text);
          font-family: "Iowan Old Style", "Palatino Linotype", "Songti SC", "PingFang SC", serif;
          font-size: 2.18rem;
          font-weight: 700;
          letter-spacing: -0.02em;
        }

        .shell-copy {
          margin: 0.34rem 0 0;
          max-width: 30rem;
          color: var(--text-soft);
          line-height: 1.55;
          font-size: 0.88rem;
        }

        .header-meta-card {
          display: flex;
          flex-direction: column;
          gap: 0;
          padding: 0.42rem 0.58rem;
          border-radius: 16px;
          min-width: 176px;
          max-width: 220px;
          margin-left: auto;
          background: rgba(255, 251, 246, 0.7);
          border: 1px solid rgba(82, 67, 52, 0.08);
          box-shadow: none;
          overflow: hidden;
        }

        .header-meta-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.42rem;
          width: 100%;
        }

        .header-meta-title {
          margin: 0;
          color: var(--text-soft);
          font-size: 0.72rem;
          font-weight: 600;
          line-height: 1.3;
          white-space: nowrap;
        }

        .header-status {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          min-height: 24px;
          padding: 0.08rem 0.58rem;
          border-radius: 999px;
          background: rgba(40, 64, 92, 0.08);
          color: #28405c;
          font-size: 0.7rem;
          font-weight: 700;
          white-space: nowrap;
          flex-shrink: 0;
        }

        .header-status.is-error {
          background: #f8ecec;
          color: var(--danger);
        }

        .conversation-panel,
        .workspace-panel {
          background: transparent;
          border: none;
          box-shadow: none;
          border-radius: 0;
          padding: 0;
          min-height: 100%;
        }

        .conversation-panel {
          padding: 0;
        }

        .conversation-panel.process-shell {
          padding: 0.9rem 1rem 0.95rem;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.5);
          border: 1px solid rgba(17, 24, 39, 0.06);
          box-shadow: none;
        }

        .workspace-panel {
          padding: 0;
        }

        .input-caption {
          margin: 0 0 0.26rem;
          color: var(--text);
          font-size: 1.08rem;
          font-weight: 700;
          letter-spacing: -0.01em;
        }

        .panel-kicker,
        .shell-eyebrow {
          text-transform: uppercase;
        }

        .panel-kicker {
          margin: 0;
          color: var(--accent);
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.06em;
        }

        .panel-title {
          margin: 0.35rem 0 0;
          color: var(--text);
          font-family: "Iowan Old Style", "Palatino Linotype", "Songti SC", "PingFang SC", serif;
          font-size: 1.55rem;
          font-weight: 700;
          letter-spacing: -0.01em;
        }

        .panel-copy {
          margin: 0.34rem 0 0;
          color: var(--text-soft);
          line-height: 1.7;
          font-size: 0.9rem;
        }

        .conversation-panel .panel-title {
          font-size: 1.38rem;
        }

        .workspace-panel .panel-title {
          margin-top: 0.22rem;
          font-size: var(--workspace-title-size);
        }

        .waterfall-gap {
          height: 0.9rem;
        }

        .content-divider {
          height: 1px;
          margin: 1.5rem 0 0;
          background: linear-gradient(90deg, rgba(17, 24, 39, 0), rgba(17, 24, 39, 0.12), rgba(17, 24, 39, 0));
        }

        .panel-helper,
        .microcopy,
        .input-copy,
        .input-hint {
          color: rgba(93, 100, 112, 0.88);
          font-size: 0.75rem;
          line-height: 1.45;
        }

        .panel-helper {
          margin: 0.22rem 0 0;
          max-width: 30rem;
        }

        .stream-headline {
          margin: 0 0 0.32rem;
          color: var(--accent-secondary);
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }

        .header-action-stack {
          margin-top: 0.2rem;
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.9rem;
        }

        .conversation-thread {
          display: grid;
          gap: 1rem;
          margin-top: 0.65rem;
        }

        .thread-item,
        .empty-card,
        .metric-card,
        .insight-card,
        .follow-card,
        .section-card {
          border-radius: 0;
          border: none;
          background: transparent;
          box-shadow: none;
        }

        .thread-item,
        .empty-card,
        .insight-card,
        .follow-card,
        .section-card {
          padding: 0;
        }

        .thread-item.user {
          background: transparent;
          border-color: transparent;
        }

        .thread-item.assistant {
          background: transparent;
        }

        .thread-label,
        .history-tag,
        .summary-status {
          display: inline-flex;
          align-items: center;
          min-height: 26px;
          padding: 0;
          border-radius: 999px;
          background: transparent;
          color: #28405c;
          font-size: 0.72rem;
          font-weight: 700;
        }

        .thread-content,
        .thread-content p,
        .thread-content li {
          color: var(--text);
          line-height: 1.72;
        }

        .thread-content p,
        .thread-content ul {
          margin: 0.3rem 0 0;
        }

        .thread-content h2,
        .thread-content h3 {
          margin: 0.6rem 0 0.5rem;
          color: var(--accent-secondary);
          font-size: 1rem;
        }

        .example-grid,
        .follow-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 0.52rem;
          margin-top: 0.42rem;
        }

        .example-card,
        .follow-card {
          height: 100%;
        }

        .example-card-title,
        .follow-card-title {
          margin: 0;
          color: var(--text);
          font-size: 0.94rem;
          font-weight: 700;
        }

        .example-card-copy,
        .follow-card-copy {
          margin: 0.18rem 0 0;
          color: var(--text-soft);
          line-height: 1.55;
          font-size: 0.82rem;
        }

        .summary-hero {
          padding: 0;
          border-radius: 0;
          border: none;
          background: transparent;
          box-shadow: none;
        }

        .summary-hero.results-shell {
          margin-bottom: 0.95rem;
          padding: 0.95rem 1.05rem 1rem;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.56);
          border: 1px solid rgba(17, 24, 39, 0.06);
          box-shadow: none;
        }

        .summary-title {
          margin: 0.38rem 0 0;
          color: var(--text);
          font-size: 1.18rem;
          font-weight: 700;
          letter-spacing: -0.01em;
          line-height: 1.2;
        }

        .summary-copy {
          margin: 0.28rem 0 0;
          color: var(--text-soft);
          line-height: 1.58;
          font-size: 0.84rem;
        }

        .metric-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 0.8rem;
          margin-top: 0.78rem;
        }

        .metric-card {
          padding: 0;
          background: transparent;
          border-color: transparent;
          box-shadow: none;
        }

        .metric-label {
          margin: 0;
          color: var(--text-soft);
          font-size: 0.72rem;
        }

        .metric-value {
          margin: 0.18rem 0 0;
          color: var(--accent-secondary);
          font-size: 0.9rem;
          font-weight: 700;
        }

        .section-heading {
          margin: 0 0 0.38rem;
          color: var(--accent-secondary);
          font-size: 1rem;
          font-weight: 700;
        }

        .insight-card h1,
        .insight-card h2,
        .insight-card h3,
        .insight-card p,
        .insight-card li {
          color: var(--text);
        }

        .insight-card.insight-shell {
          padding: 0.95rem 1.05rem 1rem;
          border-radius: 20px;
          background: rgba(255, 251, 247, 0.88);
          border: 1px solid rgba(17, 24, 39, 0.06);
          box-shadow: none;
          margin-bottom: 0.95rem;
        }

        .insight-card h2,
        .insight-card h3 {
          margin: 0.2rem 0 0.6rem;
          font-size: 1.28rem;
          font-weight: 800;
          line-height: 1.35;
        }

        .insight-card p,
        .insight-card ul {
          margin: 0.42rem 0 0;
          line-height: 1.75;
        }

        .empty-copy {
          margin: 0.35rem 0 0;
          color: var(--text-soft);
          line-height: 1.7;
          font-size: 0.9rem;
        }

        .preview-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 0.55rem;
          margin-top: 0.85rem;
        }

        .preview-item {
          display: flex;
          align-items: flex-start;
          gap: 0.45rem;
          color: var(--text-soft);
          font-size: 0.79rem;
          line-height: 1.55;
        }

        .preview-dot {
          width: 6px;
          height: 6px;
          margin-top: 0.4rem;
          border-radius: 999px;
          background: rgba(40, 64, 92, 0.45);
          flex: 0 0 auto;
        }

        .preview-title {
          color: #28405c;
          font-weight: 700;
        }

        .input-headline {
          margin: 0;
          color: var(--text-soft);
          font-size: 0.78rem;
          font-weight: 500;
        }

        div[data-testid="stForm"] {
          margin-top: 0.82rem !important;
          padding: 2rem 2rem 1.9rem !important;
          background:
            radial-gradient(circle at top right, rgba(47, 92, 243, 0.07), transparent 26%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(246, 249, 255, 0.97) 100%);
          border: 1px solid rgba(47, 92, 243, 0.10);
          box-shadow: 0 28px 56px rgba(17, 24, 39, 0.10);
          border-radius: 34px !important;
        }

        div[data-testid="stForm"] > div:first-child {
          border: none !important;
          padding: 0 !important;
          background: transparent !important;
        }

        div[data-testid="stForm"] div[data-testid="column"] {
          position: relative;
        }

        div[data-testid="stFormSubmitButton"] {
          position: relative;
          z-index: 5;
        }

        .input-shell {
          margin: 0;
        }

        .input-caption {
          margin: 0 0 0.36rem;
          color: var(--text);
          font-size: 1.05rem;
          font-weight: 700;
          letter-spacing: -0.01em;
          line-height: 1.3;
        }

        .input-copy {
          margin: 0 0 0.9rem;
          color: var(--text-soft);
          font-size: 0.84rem;
          line-height: 1.55;
          max-width: 34rem;
        }

        .input-shell div[data-testid="stTextInput"] input {
          min-height: 78px;
          border-radius: 22px;
          border: 1px solid rgba(17, 24, 39, 0.12);
          background: rgba(255, 255, 255, 0.98);
          color: var(--text);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
          font-size: 1.08rem;
          padding-left: 1rem;
        }

        .input-shell div[data-testid="stTextInput"] input::placeholder {
          color: #7a8597;
        }

        .input-shell .stButton > button,
        .input-shell button[kind="primaryFormSubmit"] {
          min-height: 78px;
          border-radius: 22px;
          border: 1px solid rgba(47, 92, 243, 0.16);
          background: linear-gradient(180deg, #2F5CF3 0%, #2347cd 100%);
          color: #ffffff;
          font-weight: 800;
          font-size: 1rem;
          letter-spacing: 0.01em;
          box-shadow: 0 18px 34px rgba(47, 92, 243, 0.28);
        }

        .secondary-action .stButton > button {
          min-height: 44px;
          min-width: 176px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 252, 247, 0.8);
          color: var(--text);
          font-size: 0.86rem;
          font-weight: 600;
          box-shadow: none;
          white-space: nowrap;
        }

        .sample-result-card {
          margin-top: 0.85rem;
          padding: 1.2rem 1.2rem;
          border-radius: 24px;
          background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(245, 248, 255, 0.96) 100%);
          border: 1px solid rgba(17, 24, 39, 0.08);
          box-shadow: 0 18px 36px rgba(17, 24, 39, 0.07);
        }

        .sample-result-row {
          display: grid;
          grid-template-columns: 88px 1fr;
          gap: 0.8rem;
          padding: 0.68rem 0;
          border-top: 1px solid rgba(17, 24, 39, 0.08);
        }

        .sample-result-row:first-of-type {
          border-top: none;
        }

        .sample-label {
          color: var(--accent);
          font-size: 0.8rem;
          font-weight: 700;
        }

        .sample-value {
          color: var(--text);
          font-size: 0.86rem;
          line-height: 1.7;
        }

        .sample-result-row.emphasis .sample-value {
          font-size: 0.98rem;
          font-weight: 700;
          line-height: 1.55;
        }

        .sample-result-row.highlight {
          margin-top: 0.2rem;
          padding: 0.8rem 0.82rem;
          border-radius: 16px;
          background: rgba(47, 92, 243, 0.07);
          border-top: none;
        }

        .plain-section {
          margin-top: 1rem;
        }

        .plain-section.suggested-questions {
          margin: 0.15rem 0 0.95rem;
          padding: 0.9rem 1rem 0.95rem;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.52);
          border: 1px solid rgba(17, 24, 39, 0.06);
          box-shadow: none;
        }

        .plain-section.suggested-questions .section-heading {
          margin-bottom: 0.3rem;
          font-size: 0.98rem;
        }

        .plain-section.follow-up-shell {
          margin-top: 0.95rem;
          padding: 0.9rem 1rem 0.95rem;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.48);
          border: 1px solid rgba(17, 24, 39, 0.06);
          box-shadow: none;
        }

        .plain-list {
          display: grid;
          gap: 0.7rem;
          margin-top: 0.48rem;
        }

        .plain-list-item {
          padding-left: 0.95rem;
          position: relative;
        }

        .plain-list-item::before {
          content: "";
          position: absolute;
          left: 0;
          top: 0.62rem;
          width: 6px;
          height: 6px;
          border-radius: 999px;
          background: rgba(17, 24, 39, 0.32);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stPlotlyChart"] {
          border-radius: var(--radius-lg);
          padding: 0.35rem;
          overflow: hidden;
          background: rgba(255, 251, 247, 0.88);
          border: 1px solid var(--line);
          box-shadow: var(--shadow-sm);
        }

        @media (max-width: 1200px) {
          .metric-grid,
          .example-grid,
          .follow-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 880px) {
          .metric-grid,
          .example-grid,
          .follow-grid {
            grid-template-columns: 1fr;
          }

          .shell-title {
            font-size: 1.5rem;
          }

          .input-caption {
            font-size: 0.98rem;
          }

          .top-shell,
          .header-meta-card {
            max-width: none;
          }
        }
        </style>
        """
    replacements = {
        "__WORKSPACE_TITLE_SIZE__": str(layout["workspace_title_size_rem"]),
        "__SUMMARY_TITLE_SIZE__": str(layout["summary_title_size_rem"]),
        "__SUMMARY_COPY_SIZE__": str(layout["summary_copy_size_rem"]),
        "__SUMMARY_HERO_PADDING__": str(layout["summary_hero_padding_rem"]),
        "__METRIC_CARD_PADDING_Y__": str(layout["metric_card_padding_y_rem"]),
        "__METRIC_CARD_PADDING_X__": str(layout["metric_card_padding_x_rem"]),
        "__METRIC_VALUE_SIZE__": str(layout["metric_value_size_rem"]),
    }
    for token, value in replacements.items():
        css = css.replace(token, value)
    st.markdown(
        css,
        unsafe_allow_html=True,
    )


@st.cache_resource
def load_schema() -> tuple[str | None, str | None]:
    """加载数据库结构，失败时返回错误信息。"""
    try:
        return db.get_schema(), None
    except Exception as exc:  # pragma: no cover
        return None, str(exc)


def build_layout_config() -> dict:
    """集中维护首页关键布局占比，便于定向收口页面主次。"""
    return {
        "header_columns": [0.82, 0.18],
        "header_gap": "small",
        "header_action_offset_rem": 0.2,
        "content_mode": "waterfall",
        "content_max_width_px": 1080,
        "content_section_gap_rem": 0.92,
        "workspace_density": "compact",
        "workspace_title_size_rem": 1.22,
        "summary_title_size_rem": 0.94,
        "summary_copy_size_rem": 0.76,
        "summary_hero_padding_rem": 0.62,
        "metric_card_padding_y_rem": 0.46,
        "metric_card_padding_x_rem": 0.54,
        "metric_value_size_rem": 0.82,
        "input_columns": [0.78, 0.22],
    }


def build_result_panel(answer: str, chart_config: dict | None, raw_rows: list[dict]) -> dict:
    """根据返回内容判断右侧结果区的展示模式。"""
    if answer:
        return {
            "mode": "analysis",
            "title": "本轮分析结果",
            "summary": "系统已经把问题整理成可阅读的判断，并保留了支撑这次判断的关键数据。",
            "has_chart": bool(chart_config and raw_rows),
            "row_count": len(raw_rows),
        }
    if raw_rows:
        return {
            "mode": "table",
            "title": "已拿到关键数据",
            "summary": f"系统先返回了 {len(raw_rows)} 行数据，你可以继续追问原因、对比和异常点。",
            "has_chart": False,
            "row_count": len(raw_rows),
        }
    return {
        "mode": "empty",
        "title": "你会先看到什么",
        "summary": "输入一个业务问题后，页面会先给出判断，再把关键数据和下一步问题接出来。",
        "has_chart": False,
        "row_count": 0,
    }


def build_example_questions() -> list[dict]:
    """提供首页空状态和推荐追问共用的示例问题。"""
    return [
        {"title": "看增长质量", "question": "哪些城市在增长，哪些城市在明显下滑？"},
        {"title": "看优先级", "question": "Top10 城市里，谁的增长质量最好，谁最值得优先跟进？"},
        {"title": "看异常结构", "question": "哪些城市结构异常，值得重点分析？"},
    ]


def build_workspace_preview_items() -> list[dict]:
    """提供空状态下右侧结果区的展示预期。"""
    return [
        {"title": "核心判断", "copy": "直接回答问题里最值得先做的业务判断。"},
        {"title": "关键数据", "copy": "把最能支撑判断的数据和差异先摆出来。"},
        {"title": "推荐追问", "copy": "顺手给出下一步最值得继续拆的问题。"},
    ]


def build_thread_preview(role: str, content: str) -> str:
    """把对话内容压缩成适合左侧线程展示的短摘要。"""
    text = str(content or "").strip()
    if not text:
        return ""

    unescaped_text = html.unescape(text)
    has_thread_markup = any(
        marker in unescaped_text for marker in ("thread-item", "thread-label", "thread-content", "conversation-thread")
    )
    looks_like_html = bool(
        re.search(r"</?(div|p|span|section|article|ul|li|h[1-6])\b", unescaped_text, flags=re.I)
        or "&lt;" in text
        or "class=" in unescaped_text
    )
    if role != "assistant" and not has_thread_markup and not looks_like_html:
        return text

    text = unescaped_text
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        if line in {"分析助手", "你"} or "thread-item" in line or "thread-label" in line or "thread-content" in line:
            continue
        lines.append(line)

    if not lines:
        return "这一轮结果已更新，请查看右侧工作区。" if role == "assistant" or has_thread_markup else text

    preview = re.sub(r"\s+", " ", " ".join(lines[:2])).strip()
    if any(token in preview for token in ("<", ">", "&lt;", "&gt;", "class=")):
        return "这一轮结果已更新，请查看右侧工作区。"
    if len(preview) > 96:
        return preview[:93].rstrip() + "..."
    return preview


def build_header_model(db_error: str | None, latest_result: dict | None) -> dict:
    """构造顶部头部需要的业务状态。"""
    if db_error:
        return {
            "title": PAGE_TITLE,
            "subtitle": "输入业务问题，直接获得核心判断、关键数据和推荐追问。",
            "status_label": "数据源状态",
            "status_tone": "is-error",
            "status_value": "未在线",
            "status_detail": "",
        }

    return {
        "title": PAGE_TITLE,
        "subtitle": "输入业务问题，直接获得核心判断、关键数据和推荐追问。",
        "status_label": "数据源状态",
        "status_tone": "",
        "status_value": "在线",
        "status_detail": "",
    }


def _extract_question_pairs(messages: list[dict]) -> list[dict]:
    """把消息流整理成问答对，便于按问题维度展示历史。"""
    pairs: list[dict] = []
    current_question = ""
    current_answer = ""

    for message in messages:
        role = message.get("role")
        content = str(message.get("content", "")).strip()
        if not content:
            continue

        if role == "user":
            if current_question:
                pairs.append({"question": current_question, "answer": current_answer})
            current_question = content
            current_answer = ""
        elif role == "assistant" and current_question:
            current_answer = content

    if current_question:
        pairs.append({"question": current_question, "answer": current_answer})

    return pairs


def build_conversation_panel(messages: list[dict], latest_result: dict | None) -> dict:
    """把消息流整理成首页左侧的分析协作线程。"""
    items: list[dict] = []
    for message in messages:
        role = message.get("role")
        content = str(message.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        items.append(
            {
                "role": role,
                "label": "你" if role == "user" else "分析助手",
                "content": build_thread_preview(role, content),
            }
        )

    has_items = bool(items)
    if not has_items:
        return {
            "title": "",
            "helper_text": "",
            "examples_title": "",
            "examples": [],
            "items": [],
            "status_label": "等待提问",
        }

    return {
        "title": "分析过程",
        "helper_text": "保留本轮分析过程，方便继续追问、补充维度或回看判断依据。",
        "examples_title": "建议先问",
        "examples": build_example_questions(),
        "items": items,
        "status_label": "已生成结果" if latest_result else "等待提问",
    }


def build_workspace_sections(latest_result: dict | None) -> dict:
    """根据最新结果决定工作区各区块是否展示。"""
    result = latest_result or {}
    answer = result.get("answer", "")
    chart_config = result.get("chart_config")
    raw_rows = result.get("raw_rows", [])
    panel = build_result_panel(answer, chart_config, raw_rows)
    mode = panel["mode"]
    examples = build_example_questions()
    preview_items = build_workspace_preview_items()
    mode_label = "分析中" if mode == "analysis" else "已返回数据" if mode == "table" else "等待提问"

    if mode == "analysis":
        description = f"当前已经整理出核心判断，并保留了 {len(raw_rows)} 行支撑数据。"
        follow_ups = [
            {"title": "继续拆维度", "question": "把当前判断按城市、月份或渠道再拆开看。"},
            {"title": "补一个对比", "question": "和上月或去年同期相比，差异主要来自哪里？"},
            {"title": "确认优先级", "question": "如果只看影响最大的三个城市，问题最严重的是谁？"},
        ]
    elif mode == "table":
        description = f"当前拿到了 {len(raw_rows)} 行关键数据，可以继续追问原因、对比和异常点。"
        follow_ups = [
            {"title": "找异常城市", "question": "哪些城市的指标变化最异常，值得重点关注？"},
            {"title": "看增长质量", "question": "这些城市里，谁的增长质量最好，谁只是短期波动？"},
            {"title": "补充筛选", "question": "把时间范围缩小到最近一个季度，再看结果是否还成立。"},
        ]
    else:
        description = ""
        follow_ups = []

    summary = {
        "mode_label": "示例预览" if mode == "empty" else mode_label,
        "title": "你将得到什么" if mode == "empty" else panel["title"],
        "summary": panel["summary"],
        "description": description,
        "row_count": panel["row_count"],
        "chart_label": "已生成" if panel["has_chart"] else "待生成",
        "metric_items": [
            {"label": "结果结构", "value": "核心判断" if mode == "analysis" else "关键数据"},
            {"label": "数据行数", "value": str(panel["row_count"]) if panel["row_count"] else "0"},
            {"label": "图表预览", "value": "已生成" if panel["has_chart"] else "待生成"},
            {"label": "下一步", "value": "推荐追问" if mode != "empty" else "输入问题"},
        ],
    }

    workspace = {
        "mode": mode,
        "summary": summary,
        "insight_title": "核心判断",
        "chart_title": "关键图表",
        "table_title": "关键数据",
        "follow_up_title": "推荐追问",
        "sections": {
            "show_insight": bool(answer),
            "show_chart": bool(chart_config and raw_rows),
            "show_table": bool(raw_rows),
        },
        "follow_ups": follow_ups,
        "examples": examples,
        "preview_items": preview_items,
    }

    if mode == "empty":
        workspace["empty_hint"] = ""
        workspace["summary"]["metric_items"] = []

    return workspace


def build_input_model(db_error: str | None, latest_result: dict | None) -> dict:
    """构造底部统一输入条的文案。"""
    result = latest_result or {}
    has_result = bool(result.get("answer") or result.get("raw_rows"))

    if db_error:
        return {
            "title": "数据库暂时不可用",
            "copy": "数据库恢复之前，这里不会真正发起分析请求。",
            "placeholder": "请先修复数据库连接后再提问",
            "button_label": "数据库不可用",
            "hint": "当前无法发起分析，请先恢复数据库连接。",
            "disabled": True,
            "status_label": "数据库异常",
        }

    return {
        "title": "从一个业务判断开始" if not has_result else "继续补充这轮判断",
        "copy": ""
        if not has_result
        else "",
        "placeholder": "输入一个业务问题，例如：为什么某些城市收入下滑？"
        if not has_result
        else "例如：这些下滑城市中，哪些是订单量下降导致的？",
        "button_label": "继续生成结论" if has_result else "生成分析结论",
        "hint": "",
        "disabled": False,
        "status_label": "数据库在线",
    }


def build_assistant_message(answer: str, raw_rows: list[dict]) -> str:
    """为消息历史生成适合展示的结果摘要。"""
    if answer:
        return answer
    if raw_rows:
        return f"查询已完成，结果工作区展示了 {len(raw_rows)} 行数据。"
    return "本轮没有命中结果，可以调整时间范围、指标口径或筛选条件。"


def _render_simple_markdown_html(text: str) -> str:
    """把简单 markdown 转成适合放进卡片的 HTML。"""
    blocks: list[str] = []
    bullet_items: list[str] = []
    ordered_items: list[str] = []
    table_rows: list[list[str]] = []

    def render_inline(content: str) -> str:
        escaped = html.escape(content)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        return escaped

    def flush_table() -> None:
        nonlocal table_rows
        if not table_rows:
            return
        if len(table_rows) == 1:
            blocks.append(
                "<p>" + " | ".join(render_inline(cell) for cell in table_rows[0]) + "</p>"
            )
            table_rows = []
            return

        header = table_rows[0]
        body = table_rows[1:]
        blocks.append(
            "<table><thead><tr>"
            + "".join(f"<th>{render_inline(cell)}</th>" for cell in header)
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join(f"<td>{render_inline(cell)}</td>" for cell in row) + "</tr>"
                for row in body
            )
            + "</tbody></table>"
        )
        table_rows = []

    def flush_bullets() -> None:
        nonlocal bullet_items
        if bullet_items:
            blocks.append("<ul>" + "".join(bullet_items) + "</ul>")
            bullet_items = []

    def flush_ordered() -> None:
        nonlocal ordered_items
        if ordered_items:
            blocks.append("<ol>" + "".join(ordered_items) + "</ol>")
            ordered_items = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush_table()
            flush_bullets()
            flush_ordered()
            continue

        is_table_line = line.startswith("|") and line.endswith("|") and line.count("|") >= 3
        if is_table_line:
            stripped_cells = [cell.strip() for cell in line.strip("|").split("|")]
            is_separator = all(re.fullmatch(r":?-{3,}:?", cell) for cell in stripped_cells)
            if is_separator:
                continue
            table_rows.append(stripped_cells)
            continue

        flush_table()
        escaped = render_inline(line.lstrip("#").strip())
        if line.startswith("### "):
            flush_bullets()
            flush_ordered()
            blocks.append(f"<h3>{escaped}</h3>")
        elif line.startswith("## ") or line.startswith("# "):
            flush_bullets()
            flush_ordered()
            blocks.append(f"<h2>{escaped}</h2>")
        elif line.startswith("- ") or line.startswith("* "):
            flush_ordered()
            bullet_items.append(f"<li>{render_inline(line[2:].strip())}</li>")
        elif re.match(r"^\d+\.\s+", line):
            flush_bullets()
            ordered_text = re.sub(r"^\d+\.\s+", "", line)
            ordered_items.append(f"<li>{render_inline(ordered_text)}</li>")
        else:
            flush_bullets()
            flush_ordered()
            blocks.append(f"<p>{render_inline(line)}</p>")

    flush_table()
    flush_bullets()
    flush_ordered()
    return "".join(blocks)


def render_chart(chart_config: dict, raw_rows: list[dict]) -> None:
    """根据 Report Agent 输出的图表配置，用 Plotly 渲染图表。"""
    if not chart_config or not raw_rows:
        return

    df = pd.DataFrame(raw_rows)
    chart_type = chart_config.get("type")
    x_col = chart_config.get("x")
    y_cols = [col for col in chart_config.get("y", []) if col in df.columns]
    title = chart_config.get("title", "")

    if x_col not in df.columns or not y_cols:
        return

    common_layout = dict(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#ffffff",
        font=dict(color="#162535"),
        title=dict(font=dict(size=18, color="#17324b")),
        margin=dict(l=24, r=24, t=64, b=20),
        xaxis=dict(gridcolor="rgba(22,37,53,0.08)", zeroline=False),
        yaxis=dict(gridcolor="rgba(22,37,53,0.08)", zeroline=False),
    )

    if chart_type == "line":
        fig = px.line(
            df,
            x=x_col,
            y=y_cols,
            title=title,
            markers=True,
            color_discrete_sequence=["#234766", "#5d7d99", "#8fa7bb"],
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=8))
        fig.update_layout(**common_layout)
        st.plotly_chart(fig, use_container_width=True)
    elif chart_type == "bar":
        fig = px.bar(
            df,
            x=x_col,
            y=y_cols[0],
            title=title,
            color_discrete_sequence=["#234766"],
        )
        fig.update_layout(**common_layout)
        st.plotly_chart(fig, use_container_width=True)


def render_header(db_error: str | None, latest_result: dict | None) -> None:
    """渲染顶部平台头部。"""
    model = build_header_model(db_error, latest_result)
    layout = build_layout_config()
    info_col, action_col = st.columns(layout["header_columns"], gap=layout["header_gap"])

    with info_col:
        st.markdown(
            f"""
            <div class="top-shell">
              <h1 class="shell-title">{html.escape(model["title"])}</h1>
              <p class="shell-copy">{html.escape(model["subtitle"])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action_col:
        st.markdown(
            f'<div class="header-action-stack" style="margin-top:{layout["header_action_offset_rem"]}rem;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="header-meta-card">
              <div class="header-meta-row">
                <p class="header-meta-title">{html.escape(model["status_label"])}</p>
                <div class="header-status {html.escape(model['status_tone'])}">{html.escape(model['status_value'])}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="secondary-action">', unsafe_allow_html=True)
        if st.button("清空当前会话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.latest_result = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def _render_example_cards(examples: list[dict], title: str, compact: bool = False, tone: str = "") -> None:
    """渲染轻量示例问题列表。"""
    section_class = "plain-section"
    if tone:
        section_class += f" {tone}"
    items = "".join(
        f"""
        <div class="plain-list-item">
          <p class="example-card-title">{html.escape(item["title"])}</p>
          <p class="example-card-copy">{html.escape(item["question"])}</p>
        </div>
        """
        for item in examples
    )
    st.markdown(
        f"""
        <div class="{section_class}">
          <p class="section-heading">{html.escape(title)}</p>
          <div class="plain-list">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_conversation_thread_html(items: list[dict]) -> str:
    """把协作线程拼成一整块 HTML，避免 Streamlit 拆分渲染后留下空框。"""
    thread_items = "".join(
        f'<div class="thread-item {html.escape(item["role"])}">'
        f'<div class="thread-label">{html.escape(item["label"])}</div>'
        f'<div class="thread-content">{_render_simple_markdown_html(item["content"])}</div>'
        "</div>"
        for item in items
    )
    return (
        '<p class="stream-headline">分析过程</p>'
        f'<div class="conversation-panel process-shell"><div class="conversation-thread">{thread_items}</div></div>'
    )


def render_conversation_panel(messages: list[dict], latest_result: dict | None) -> None:
    """渲染左侧分析协作线程。"""
    panel = build_conversation_panel(messages, latest_result)
    if not panel["items"]:
        return
    if panel["helper_text"]:
        st.markdown(f'<p class="microcopy" style="margin:0 0 0.45rem;">{html.escape(panel["helper_text"])}</p>', unsafe_allow_html=True)
    st.markdown(_build_conversation_thread_html(panel["items"]), unsafe_allow_html=True)


def _render_summary_hero(summary: dict) -> None:
    """渲染结果摘要头图。"""
    metric_cards = "".join(
        f"""
        <div class="metric-card">
          <p class="metric-label">{html.escape(item["label"])}</p>
          <p class="metric-value">{html.escape(item["value"])}</p>
        </div>
        """
        for item in summary["metric_items"]
    )
    st.markdown(
        f"""
        <div class="summary-hero results-shell">
          <div class="summary-status">{html.escape(summary["mode_label"])}</div>
          <h3 class="summary-title">{html.escape(summary["title"])}</h3>
          <p class="summary-copy">{html.escape(summary["summary"])}</p>
          {'<p class="summary-copy">' + html.escape(summary["description"]) + '</p>' if summary["description"] else ''}
          {'<div class="metric-grid">' + metric_cards + '</div>' if summary["metric_items"] else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_follow_up_cards(follow_ups: list[dict], title: str) -> None:
    """渲染轻量推荐追问。"""
    items = "".join(
        f"""
        <div class="plain-list-item">
          <p class="follow-card-title">{html.escape(item["title"])}</p>
          <p class="follow-card-copy">{html.escape(item["question"])}</p>
        </div>
        """
        for item in follow_ups
    )
    st.markdown(
        f"""
        <div class="plain-section follow-up-shell">
          <p class="section-heading">{html.escape(title)}</p>
          <div class="plain-list">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_workspace_preview(previews: list[dict]) -> None:
    """渲染空状态下的结果区占位说明。"""
    cards = "".join(
        f"""
        <div class="preview-item">
          <span class="preview-dot"></span>
          <div>
            <span class="preview-title">{html.escape(item["title"])}</span>
            <span>：{html.escape(item["copy"])}</span>
          </div>
        </div>
        """
        for item in previews
    )
    st.markdown(
        f"""
        <div style="margin-top:0.55rem;">
          <div class="preview-grid">{cards}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sample_result_card() -> None:
    """渲染空状态下的示例结果卡片，帮助用户预期输出质量。"""
    st.markdown(
        """
        <div class="section-card sample-result-card">
          <p class="section-heading">示例结果</p>
          <div class="sample-result-row emphasis">
            <span class="sample-label">核心判断</span>
            <span class="sample-value">某些城市收入下降，主要由订单量减少导致。</span>
          </div>
          <div class="sample-result-row">
            <span class="sample-label">关键数据</span>
            <span class="sample-value">A 城市 -15%<br>B 城市 -22%<br>两地活跃用户同步下滑。</span>
          </div>
          <div class="sample-result-row highlight">
            <span class="sample-label">推荐追问</span>
            <span class="sample-value">这些城市的用户活跃度变化如何？是否集中在某些区域或时段？</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace(latest_result: dict | None) -> None:
    """渲染右侧结果工作区。"""
    result = latest_result or {}
    answer = result.get("answer", "")
    chart_config = result.get("chart_config")
    raw_rows = result.get("raw_rows", [])
    workspace = build_workspace_sections(latest_result)
    mode = workspace["mode"]
    sections = workspace["sections"]

    if mode == "empty":
        return
    else:
        if sections["show_insight"] and answer:
            st.markdown(
                f"""
                <div class="insight-card insight-shell">
                  {_render_simple_markdown_html(answer)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        if sections["show_chart"] and chart_config and raw_rows:
            st.markdown(
                f"""
                <div class="section-card">
                  <p class="section-heading">{html.escape(workspace["chart_title"])}</p>
                """,
                unsafe_allow_html=True,
            )
            render_chart(chart_config, raw_rows)
            st.markdown("</div>", unsafe_allow_html=True)

        if sections["show_table"] and raw_rows:
            st.markdown(
                f"""
                <div class="section-card">
                  <p class="section-heading">{html.escape(workspace["table_title"])}</p>
                """,
                unsafe_allow_html=True,
            )
            st.dataframe(pd.DataFrame(raw_rows), width="stretch")
            st.markdown("</div>", unsafe_allow_html=True)

        if workspace["follow_ups"]:
            _render_follow_up_cards(workspace["follow_ups"], workspace["follow_up_title"])


def render_input_bar(schema: str | None, db_error: str | None, latest_result: dict | None) -> None:
    """渲染底部统一输入条。"""
    model = build_input_model(db_error, latest_result)
    layout = build_layout_config()
    if not latest_result and not db_error:
        _render_example_cards(build_example_questions(), "建议先问", compact=True, tone="suggested-questions")
    with st.form("analysis_input_bar", clear_on_submit=True):
        st.markdown(
            f"""
            <div class="input-shell">
              <p class="input-caption">{html.escape(model["title"])}</p>
              {'<p class="input-copy">' + html.escape(model["copy"]) + '</p>' if model["copy"] else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )
        input_col, button_col = st.columns(layout["input_columns"], gap="medium", vertical_alignment="bottom")
        with input_col:
            question = st.text_input(
                "业务问题",
                value="",
                placeholder=model["placeholder"],
                label_visibility="collapsed",
                disabled=bool(model["disabled"]),
            )
        with button_col:
            submitted = st.form_submit_button(
                model["button_label"],
                use_container_width=True,
                disabled=bool(model["disabled"]),
            )

    if submitted:
        handle_question(schema, db_error, question.strip())


def init_state() -> None:
    """初始化页面会话状态。"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "latest_result" not in st.session_state:
        st.session_state.latest_result = None


def handle_question(schema: str | None, db_error: str | None, question: str | None) -> None:
    """处理用户提问，并把结果写入 session_state。"""
    if not question:
        return

    if db_error or not schema:
        st.error("数据库未连接，无法处理问题。")
        return

    st.session_state.messages.append({"role": "user", "content": question})
    history = st.session_state.messages[:-1]
    try:
        with st.spinner("正在理解问题、查询数据并整理本轮结果..."):
            answer, chart_config, raw_rows = router.run(schema, question, history)
    except Exception as exc:  # pragma: no cover
        answer, chart_config, raw_rows = f"出错了：{exc}", None, []

    assistant_text = build_assistant_message(answer, raw_rows)
    st.session_state.messages.append({"role": "assistant", "content": assistant_text})
    if len(st.session_state.messages) > 20:
        st.session_state.messages = st.session_state.messages[-20:]

    st.session_state.latest_result = {
        "answer": answer,
        "chart_config": chart_config,
        "raw_rows": raw_rows,
    }
    st.rerun()


def render_app() -> None:
    """渲染双区 Copilot 首页。"""
    st.set_page_config(page_title=PAGE_TITLE, page_icon="📊", layout="wide")
    layout = build_layout_config()
    inject_styles(layout)
    init_state()

    schema, db_error = load_schema()
    latest_result = st.session_state.latest_result

    render_header(db_error, latest_result)
    st.markdown(f'<div class="waterfall-gap" style="height:{layout["content_section_gap_rem"]}rem;"></div>', unsafe_allow_html=True)
    render_input_bar(schema, db_error, latest_result)
    if latest_result:
        st.markdown('<div class="content-divider"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="waterfall-gap" style="height:{layout["content_section_gap_rem"] + 0.2}rem;"></div>', unsafe_allow_html=True)
        render_conversation_panel(st.session_state.messages, latest_result)
        st.markdown(f'<div class="waterfall-gap" style="height:{layout["content_section_gap_rem"]}rem;"></div>', unsafe_allow_html=True)
        render_workspace(latest_result)
    else:
        st.markdown(f'<div class="waterfall-gap" style="height:{layout["content_section_gap_rem"]}rem;"></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    render_app()
