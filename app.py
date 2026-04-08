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
    """注入与 .pen 设计稿一致的中心瀑布式桌面端样式。"""
    css = f"""
        <style>
        :root {{
          --page-bg: #f5f7fa;
          --page-bg-accent:
            radial-gradient(circle at 16% 8%, rgba(220, 232, 245, 0.82), transparent 28%),
            radial-gradient(circle at 82% 20%, rgba(230, 238, 246, 0.68), transparent 22%),
            linear-gradient(180deg, #f8fafc 0%, #eef2f6 100%);
          --surface: #fcfdfe;
          --surface-subtle: #f7f9fb;
          --surface-accent: #dcecf8;
          --ink: #171c22;
          --ink-soft: #5e6875;
          --ink-muted: #7a8591;
          --line: #d9e1e8;
          --line-strong: #c7d2dc;
          --hero: #11161d;
          --hero-elevated: #1a212a;
          --hero-line: #2d3742;
          --hero-ink: #f5f7fa;
          --accent: #4a9fd8;
          --accent-soft: #dcecf8;
          --shadow-xl: 0 18px 42px rgba(0, 0, 0, 0.10);
          --shadow-lg: 0 14px 34px rgba(0, 0, 0, 0.08);
          --shadow-md: 0 8px 22px rgba(0, 0, 0, 0.07);
          --display: "Newsreader", "Iowan Old Style", "Palatino Linotype", "Songti SC", serif;
          --body: "Funnel Sans", "Avenir Next", "Segoe UI", "PingFang SC", sans-serif;
          --mono: "IBM Plex Mono", "SFMono-Regular", "SF Mono", monospace;
          --page-max-width: {layout["content_max_width_px"]}px;
          --section-gap: {layout["content_section_gap_rem"]}rem;
        }}

        .stApp {{
          background: var(--page-bg);
          background-image: var(--page-bg-accent);
          color: var(--ink);
          font-family: var(--body);
        }}

        header[data-testid="stHeader"],
        div[data-testid="stHeader"] {{
          background: transparent;
          height: 0;
          min-height: 0;
        }}

        .stApp > header {{
          background: transparent;
        }}

        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"] {{
          visibility: hidden;
          height: 0;
          min-height: 0;
          position: fixed;
        }}

        #MainMenu {{
          visibility: hidden;
        }}

        .block-container {{
          max-width: calc(var(--page-max-width) + 44px);
          padding-top: {layout["page_top_padding_rem"]}rem;
          padding-bottom: {layout["page_bottom_padding_rem"]}rem;
          padding-left: 0.75rem;
          padding-right: 0.75rem;
          margin-left: auto;
          margin-right: auto;
        }}

        p, li, div, span, label {{
          font-family: var(--body);
        }}

        .atelier-gap {{
          height: var(--section-gap);
        }}

        .atelier-header {{
          padding: 0 0.25rem;
        }}

        .atelier-eyebrow,
        .section-kicker,
        .hero-kicker,
        .metric-label,
        .process-meta,
        .status-pill,
        .input-ready-badge,
        .evidence-meta,
        .prompt-line {{
          font-family: var(--mono);
          text-transform: uppercase;
        }}

        .atelier-eyebrow {{
          margin: 0 0 0.35rem;
          color: var(--accent);
          font-size: 0.7rem;
          font-weight: 600;
          letter-spacing: 0.18em;
        }}

        h1.atelier-title,
        .atelier-title {{
          margin: 0;
          color: var(--ink) !important;
          font-family: var(--display) !important;
          font-size: 2.2rem !important;
          font-weight: 700 !important;
          line-height: 0.94 !important;
          letter-spacing: -0.03em !important;
        }}

        .status-pill {{
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.55rem 0.78rem;
          border-radius: 12px;
          background: var(--surface);
          border: 1px solid var(--line);
          box-shadow: 0 6px 18px rgba(0, 0, 0, 0.04);
          color: var(--ink-soft);
          font-size: 0.64rem;
          font-weight: 600;
          letter-spacing: 0.12em;
          justify-content: center;
          white-space: nowrap;
        }}

        .status-dot {{
          width: 0.38rem;
          height: 0.38rem;
          border-radius: 999px;
          background: var(--accent);
          box-shadow: 0 0 0 4px rgba(74, 159, 216, 0.12);
          flex: 0 0 auto;
        }}

        .status-dot.is-error {{
          background: #d85a5a;
          box-shadow: 0 0 0 4px rgba(216, 90, 90, 0.14);
        }}

        .entry-card {{
          padding: 1.1rem 1.35rem 0.65rem;
          border-radius: 18px 18px 0 0;
          background: var(--surface);
          border: 1px solid var(--line);
          border-bottom: 0;
          box-shadow: var(--shadow-lg);
        }}

        .entry-card .section-kicker,
        .preview-shell .section-kicker,
        .process-shell .section-kicker,
        .judgment-shell .section-kicker,
        .evidence-shell .section-kicker,
        .follow-shell .section-kicker {{
          margin: 0 0 0.42rem;
          color: var(--accent);
          font-size: 0.72rem;
          font-weight: 600;
          letter-spacing: 0.16em;
        }}

        h2.entry-title,
        .entry-title {{
          margin: 0;
          color: var(--ink) !important;
          font-family: var(--display) !important;
          font-size: 1.85rem !important;
          font-weight: 700 !important;
          line-height: 1.02 !important;
          letter-spacing: -0.024em !important;
          max-width: 22ch;
        }}

        .input-widget-row {{
          position: relative;
        }}

        .input-field-stack {{
          position: relative;
        }}

        div[data-testid="stTextInput"] {{
          margin: 0;
        }}

        div[data-testid="stTextInput"] input {{
          min-height: 54px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: var(--surface-subtle);
          color: var(--ink);
          font-family: var(--body);
          font-size: 0.95rem;
          font-weight: 500;
          padding-left: 1rem;
          padding-right: 4.4rem;
          box-shadow: none;
        }}

        div[data-testid="stTextInput"] input::placeholder {{
          color: var(--ink-muted);
          font-size: 0.82rem;
        }}

        div[data-testid="stTextInput"] input:focus {{
          border-color: rgba(74, 159, 216, 0.72);
          box-shadow: 0 0 0 3px rgba(74, 159, 216, 0.10);
        }}

        .input-ready-badge {{
          display: flex;
          justify-content: flex-end;
          margin-top: 0.18rem;
          color: var(--accent);
          font-size: 0.58rem;
          font-weight: 600;
          letter-spacing: 0.12em;
        }}

        .stButton {{
          display: flex;
          align-items: stretch;
        }}

        .stButton > button {{
          width: 100%;
          min-height: 54px;
          border-radius: 12px;
          font-family: var(--body);
          font-size: 0.88rem;
          font-weight: 600;
          border: 1px solid transparent;
          transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }}

        .stButton > button[kind="primary"] {{
          background: var(--hero);
          color: var(--hero-ink);
          box-shadow: 0 8px 22px rgba(0, 0, 0, 0.08);
        }}

        .stButton > button[kind="primary"]:hover {{
          transform: translateY(-1px);
          filter: brightness(1.02);
        }}

        .stButton > button[kind="secondary"] {{
          background: var(--surface-accent);
          color: var(--accent);
          border-color: transparent;
          box-shadow: none;
        }}

        .stButton > button[kind="secondary"]:hover {{
          transform: translateY(-1px);
          filter: brightness(0.99);
        }}

        .stElementContainer:has(.entry-card) + [data-testid="stLayoutWrapper"] {{
          margin-top: -0.28rem;
          padding: 0 1.35rem 0.1rem;
          background: var(--surface);
          border-left: 1px solid var(--line);
          border-right: 1px solid var(--line);
        }}

        .stElementContainer:has(.entry-card) + [data-testid="stLayoutWrapper"] > div {{
          gap: 0.85rem;
        }}

        .stElementContainer:has(.entry-card) + [data-testid="stLayoutWrapper"] + .stElementContainer:has(.empty-prompts) .stMarkdown {{
          margin-top: -0.08rem;
          padding: 0 1.35rem 1rem;
          background: var(--surface);
          border: 1px solid var(--line);
          border-top: 0;
          border-bottom-left-radius: 18px;
          border-bottom-right-radius: 18px;
          box-shadow: var(--shadow-lg);
        }}

        .empty-prompts {{
          display: grid;
          gap: 0.2rem;
          margin-top: 0;
        }}

        .prompt-line {{
          margin: 0;
          color: #9ca6b3;
          font-size: 0.56rem;
          font-weight: 600;
          letter-spacing: 0.04em;
        }}

        .preview-shell {{
          display: grid;
          gap: 0.7rem;
        }}

        .preview-hero {{
          padding: 1.15rem 1.25rem 1.25rem;
          border-radius: 16px;
          background: linear-gradient(180deg, #1b222b 0%, #202a35 100%);
          box-shadow: 0 12px 28px rgba(0, 0, 0, 0.08);
        }}

        h3.preview-title,
        .preview-title,
        h3.hero-title,
        .hero-title {{
          margin: 0;
          font-family: var(--display) !important;
          font-weight: 700 !important;
          line-height: 0.98 !important;
          letter-spacing: -0.025em !important;
        }}

        .preview-title {{
          color: var(--hero-ink) !important;
          font-size: 2rem !important;
          max-width: 14ch;
        }}

        .preview-metrics,
        .hero-metrics {{
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.7rem;
          margin-top: 0.9rem;
        }}

        .preview-metric,
        .hero-metric {{
          padding: 0.82rem 0.92rem;
          border-radius: 12px;
          border: 1px solid var(--hero-line);
          background: var(--hero-elevated);
        }}

        .preview-metric .metric-label,
        .hero-metric .metric-label {{
          margin: 0;
          color: rgba(245, 247, 250, 0.58);
          font-size: 0.56rem;
          font-weight: 600;
          letter-spacing: 0.12em;
        }}

        .preview-metric .metric-value,
        .hero-metric .metric-value {{
          margin: 0.24rem 0 0;
          color: var(--hero-ink);
          font-size: 0.9rem;
          font-weight: 600;
        }}

        .analysis-input-row {{
          padding-top: 0.15rem;
        }}

        .analysis-hero {{
          position: relative;
          overflow: hidden;
          padding: 1.25rem 1.35rem 1.4rem;
          border-radius: 20px;
          background: var(--hero);
          box-shadow: var(--shadow-xl);
        }}

        .analysis-hero::before {{
          content: "";
          position: absolute;
          inset: 0;
          background:
            linear-gradient(135deg, rgba(255,255,255,0.06), transparent 38%),
            radial-gradient(circle at 82% 18%, rgba(74, 159, 216, 0.10), transparent 18%);
          pointer-events: none;
        }}

        .hero-top {{
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 1.25rem;
          position: relative;
          z-index: 1;
        }}

        .hero-copy-block {{
          max-width: 33rem;
        }}

        .hero-kicker {{
          margin: 0 0 0.45rem;
          color: var(--accent);
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 0.16em;
        }}

        .analysis-hero h3.hero-title,
        .hero-title {{
          color: var(--hero-ink) !important;
          font-size: 2.55rem !important;
          max-width: 12ch;
        }}

        .hero-copy {{
          margin: 0.55rem 0 0;
          color: rgba(245, 247, 250, 0.84) !important;
          font-size: 0.92rem;
          line-height: 1.55;
          max-width: 36rem;
        }}

        .hero-side {{
          display: grid;
          justify-items: end;
          gap: 0.3rem;
          min-width: 5rem;
        }}

        .hero-plus {{
          color: var(--accent);
          font-family: var(--mono);
          font-size: 0.82rem;
          font-weight: 600;
          line-height: 1;
        }}

        .hero-side-note {{
          color: rgba(245, 247, 250, 0.36);
          font-family: var(--mono);
          font-size: 0.58rem;
          font-weight: 600;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }}

        .process-shell,
        .judgment-shell,
        .evidence-shell,
        .follow-shell {{
          position: relative;
        }}

        .process-list {{
          display: grid;
          gap: 0.72rem;
          margin-top: 0.1rem;
        }}

        .process-item {{
          padding: 0.82rem 1.1rem;
          border-left: 2px solid var(--line);
        }}

        .process-meta {{
          margin: 0;
          color: var(--ink-muted);
          font-size: 0.58rem;
          font-weight: 600;
          letter-spacing: 0.16em;
        }}

        .process-body {{
          margin: 0.34rem 0 0;
          color: var(--ink);
          font-family: var(--display);
          line-height: 1.12;
          letter-spacing: -0.015em;
        }}

        .process-body.primary {{
          font-size: 1.55rem;
          font-weight: 700;
        }}

        .process-body.secondary {{
          font-size: 1.2rem;
          font-weight: 600;
        }}

        h2.judgment-title,
        .judgment-title {{
          margin: 0.05rem 0 0.6rem;
          color: var(--ink) !important;
          font-family: var(--display) !important;
          font-size: 2.05rem !important;
          font-weight: 700 !important;
          line-height: 1.02 !important;
          letter-spacing: -0.025em !important;
          max-width: 17ch;
        }}

        .judgment-copy,
        .judgment-copy p,
        .judgment-copy li {{
          color: var(--ink-soft);
          font-size: 1rem;
          line-height: 1.7;
        }}

        .judgment-copy p {{
          margin: 0.4rem 0 0;
        }}

        .judgment-copy ul,
        .judgment-copy ol {{
          padding-left: 1.05rem;
          margin: 0.45rem 0 0;
        }}

        .evidence-card {{
          padding-top: 0.15rem;
        }}

        .evidence-title {{
          margin: 0 0 0.6rem;
          color: var(--ink);
          font-family: var(--display);
          font-size: 1.65rem;
          font-weight: 700;
          line-height: 1.08;
        }}

        .evidence-rule {{
          width: 100%;
          height: 2px;
          margin-top: 0.65rem;
          background: rgba(74, 159, 216, 0.3);
          border-radius: 999px;
        }}

        .evidence-meta-row {{
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          margin-top: 0.6rem;
        }}

        .evidence-meta {{
          margin: 0;
          color: var(--ink-muted);
          font-size: 0.62rem;
          font-weight: 600;
          letter-spacing: 0.12em;
        }}

        .evidence-note {{
          margin: 0.5rem 0 0;
          color: var(--ink-soft);
          font-family: var(--mono);
          font-size: 0.66rem;
          font-weight: 600;
          letter-spacing: 0.04em;
        }}

        div[data-testid="stPlotlyChart"] {{
          margin: 0 !important;
          padding: 0.9rem 0.95rem;
          border-radius: 10px;
          background: var(--surface-subtle);
          border: 1px solid var(--line);
          box-shadow: none;
        }}

        div[data-testid="stPlotlyChart"] > div {{
          border-radius: 8px;
          overflow: hidden;
        }}

        .table-shell {{
          border-radius: 10px;
          overflow: hidden;
          background: var(--surface-subtle);
          border: 1px solid var(--line);
        }}

        .table-scroll {{
          overflow-x: auto;
        }}

        .data-table {{
          width: 100%;
          border-collapse: collapse;
          font-family: var(--body);
          background: var(--surface-subtle);
        }}

        .data-table thead th {{
          padding: 0.82rem 0.92rem;
          text-align: left;
          background: #f2f5f8;
          color: var(--ink-soft);
          font-family: var(--mono);
          font-size: 0.64rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          border-bottom: 1px solid var(--line);
          white-space: nowrap;
        }}

        .data-table tbody td {{
          padding: 0.88rem 0.92rem;
          color: var(--ink);
          font-size: 0.84rem;
          border-bottom: 1px solid #e6edf3;
        }}

        .data-table tbody tr:last-child td {{
          border-bottom: none;
        }}

        .follow-list {{
          display: grid;
          margin-top: 0.12rem;
        }}

        .follow-item {{
          padding: 0.82rem 0;
          border-bottom: 1px solid var(--line);
        }}

        .follow-item:last-child {{
          border-bottom: none;
        }}

        .follow-question {{
          margin: 0;
          color: var(--ink);
          font-family: var(--display);
          font-size: 1.18rem;
          font-weight: 600;
          line-height: 1.15;
        }}

        @media (max-width: 900px) {{
          .block-container {{
            padding-left: 0.9rem;
            padding-right: 0.9rem;
          }}

          .atelier-title {{
            font-size: 2.45rem;
          }}

          .entry-title,
          .hero-title,
          .preview-title,
          .judgment-title {{
            max-width: none;
          }}

          .hero-top,
          .evidence-meta-row,
          .preview-metrics,
          .hero-metrics {{
            grid-template-columns: 1fr;
            display: grid;
          }}

          .hero-side {{
            justify-items: start;
          }}
        }}
        </style>
        """
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
    """集中维护新版页面的尺寸与节奏。"""
    return {
        "header_columns": [0.74, 0.26],
        "header_gap": "small",
        "header_action_offset_rem": 0.0,
        "content_columns": [1.0],
        "content_mode": "waterfall",
        "content_max_width_px": 820,
        "content_section_gap_rem": 1.6,
        "workspace_density": "editorial",
        "workspace_title_size_rem": 1.65,
        "summary_title_size_rem": 2.2,
        "summary_copy_size_rem": 0.92,
        "summary_hero_padding_rem": 1.25,
        "metric_card_padding_y_rem": 0.82,
        "metric_card_padding_x_rem": 0.92,
        "metric_value_size_rem": 0.9,
        "input_columns": [0.64, 0.22, 0.14],
        "page_top_padding_rem": 1.35,
        "page_bottom_padding_rem": 4.2,
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
    """提供分析态页尾的追问建议。"""
    return [
        {"title": "Which of the weak cities also show the sharpest order decline by district or time band?", "question": ""},
        {"title": "Compared with the previous quarter, which cities changed because of volume and which because of price?", "question": ""},
        {"title": "If we only focus on the system underperforming cities, where should the investigation start next?", "question": ""},
    ]


def build_empty_prompt_lines() -> list[str]:
    """提供空状态输入板下方的三条轻量提示。"""
    return [
        "1. Top 10 declining cities",
        "2. Order vs price mix",
        "3. Quarterly anomaly scan",
    ]


def build_quick_preview_payload() -> dict:
    """构造一份固定样例，调 UI 时直接进入结果页。"""
    raw_rows = [
        {"City": "Zhongshan", "Revenue Drop": "-16.4%", "Orders": 23822},
        {"City": "Shenzhen", "Revenue Drop": "-12.7%", "Orders": 18302},
        {"City": "Zhuhai", "Revenue Drop": "-8.5%", "Orders": 15123},
        {"City": "Foshan", "Revenue Drop": "-6.2%", "Orders": 13518},
    ]
    answer = """## Core judgment

Most underperforming cities are being dragged by order loss, not pricing.

The result flow isolates the cities with the sharpest revenue decline, then compares order volume and pricing movement to see which driver dominates. That changes the follow-up: the next move is not a pricing review first, but a deeper look into demand, activity, and location-level order concentration in the worst-performing cities."""
    chart_config = {
        "type": "bar",
        "x": "City",
        "y": ["Orders"],
        "title": "Quarterly revenue decline by city cluster",
    }
    assistant_text = build_assistant_message(answer, raw_rows)
    return {
        "messages": [
            {"role": "user", "content": "Which cities lost the most revenue momentum over the last quarter?"},
            {"role": "assistant", "content": assistant_text},
        ],
        "latest_result": {
            "answer": answer,
            "chart_config": chart_config,
            "raw_rows": raw_rows,
        },
    }


def activate_quick_preview() -> None:
    """把固定样例写入会话，跳过真实 Agent，直接预览页面。"""
    preview = build_quick_preview_payload()
    st.session_state.messages = preview["messages"]
    st.session_state.latest_result = preview["latest_result"]
    st.rerun()


def build_workspace_preview_items() -> list[dict]:
    """提供空状态下深色预期板的指标。"""
    return [
        {"label": "Judgment", "value": "One clear answer"},
        {"label": "Visuals", "value": "Chart + table"},
        {"label": "Follow-up", "value": "Next questions"},
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
    """构造顶部题签与状态胶囊。"""
    return {
        "title": PAGE_TITLE,
        "eyebrow": "+ ANALYSIS ATELIER",
        "status_text": "DATA SOURCE OFFLINE" if db_error else "DATA SOURCE ONLINE",
        "status_dot_class": "is-error" if db_error else "is-online",
    }


def summarize_answer_for_ui(answer: str) -> tuple[str, str]:
    """把 markdown 结果压成适合 Hero 与正文区的短标题和摘要。"""
    if not answer:
        return (
            "A centered result board appears first, before the detail trail begins.",
            "The first view prioritizes a single judgment, then reveals the evidence modules in the same reading path.",
        )

    text = re.sub(r"```.*?```", "", answer, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^\d+\.\s*", "", line)
        if line:
            lines.append(line)

    if not lines:
        return (
            "A centered result board appears first, before the detail trail begins.",
            "The first view prioritizes a single judgment, then reveals the evidence modules in the same reading path.",
        )

    title = lines[1] if len(lines) > 1 and lines[0].lower() in {"core judgment", "核心判断"} else lines[0]
    summary_candidates = [
        line for line in lines if line != title and line.lower() not in {"core judgment", "核心判断"}
    ]
    summary = summary_candidates[0] if summary_candidates else "The result flow keeps the judgment short first, then opens the detailed evidence below."
    if len(title) > 88:
        title = title[:85].rstrip() + "..."
    if len(summary) > 180:
        summary = summary[:177].rstrip() + "..."
    return title, summary


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
    """把消息流压成分析态里的三段式 process thread。"""
    if not latest_result:
        return {"items": []}

    latest_question = ""
    for message in reversed(messages):
        if message.get("role") == "user" and str(message.get("content", "")).strip():
            latest_question = str(message.get("content", "")).strip()
            break

    answer = str((latest_result or {}).get("answer", "")).strip()
    raw_rows = (latest_result or {}).get("raw_rows", []) or []
    has_visual = bool((latest_result or {}).get("chart_config") and raw_rows)

    items = [
        {
            "meta": "QUESTION 01 · USER",
            "content": latest_question or "Which cities lost the most revenue momentum over the last quarter?",
            "tone": "primary",
        },
        {
            "meta": "STEP 02 · ASSISTANT",
            "content": "The result flow isolates the cities with the sharpest revenue decline, then compares order volume and pricing movement to see which driver dominates."
            if answer
            else "The result board is prepared first, then the detail trail arranges the evidence in the same reading path.",
            "tone": "secondary",
        },
        {
            "meta": "STEP 03 · EVIDENCE",
            "content": f"{len(raw_rows)} row{'s' if len(raw_rows) != 1 else ''} are ready for comparison, and the current view {'includes a chart and a table' if has_visual else 'starts from the structured table first'}."
            if raw_rows
            else "Evidence will appear below the result board as soon as the first query returns rows.",
            "tone": "secondary",
        },
    ]
    return {"items": items}


def build_workspace_sections(latest_result: dict | None) -> dict:
    """根据最新结果构造分析态页面所需的区块数据。"""
    result = latest_result or {}
    answer = result.get("answer", "")
    chart_config = result.get("chart_config")
    raw_rows = result.get("raw_rows", [])
    if not latest_result:
        return {
            "mode": "empty",
            "summary": {"metric_items": []},
            "preview_items": build_workspace_preview_items(),
            "follow_ups": [],
        }

    hero_title, hero_copy = summarize_answer_for_ui(str(answer or ""))
    chart_count = 1 if chart_config and raw_rows else 0
    follow_ups = build_example_questions()

    return {
        "mode": "analysis",
        "summary": {
            "kicker": "+ RESULT PATTERN",
            "title": hero_title,
            "summary": hero_copy,
            "metric_items": [
                {"label": "Mode", "value": "Multi-step" if answer and raw_rows else "Direct"},
                {"label": "Rows", "value": str(len(raw_rows))},
                {"label": "Visuals", "value": f"{chart_count} chart" if chart_count else "Table only"},
            ],
        },
        "insight_title": "Most underperforming cities are being dragged by order loss, not pricing.",
        "chart_title": chart_config.get("title") if chart_config else "Quarterly revenue decline by city cluster",
        "table_title": "City-level revenue drop snapshot",
        "follow_up_title": "+ NEXT QUESTIONS",
        "sections": {
            "show_insight": bool(answer),
            "show_chart": bool(chart_config and raw_rows),
            "show_table": bool(raw_rows),
        },
        "follow_ups": follow_ups,
        "preview_items": build_workspace_preview_items(),
        "chart_note": "Key markets" if raw_rows else "",
        "table_note": f"{min(len(raw_rows), 3)} cities account for most of the contraction." if raw_rows else "",
    }


def build_input_model(db_error: str | None, latest_result: dict | None) -> dict:
    """构造空状态与分析态共用的输入区文案。"""
    result = latest_result or {}
    has_result = bool(result.get("answer") or result.get("raw_rows"))

    if db_error:
        return {
            "entry_kicker": "+ BEGIN WITH ONE QUESTION",
            "entry_title": "Start from a business judgment, not from a dashboard.",
            "placeholder": "请先修复数据库连接后再提问",
            "button_label": "Generate",
            "preview_label": "Preview",
            "state_badge": "OFFLINE",
            "disabled": True,
            "prompt_lines": build_empty_prompt_lines(),
        }

    return {
        "entry_kicker": "+ BEGIN WITH ONE QUESTION",
        "entry_title": "Start from a business judgment, not from a dashboard.",
        "placeholder": "Why are some cities losing revenue momentum?"
        if not has_result
        else "Which of the weak cities also show the sharpest order decline?",
        "button_label": "Generate",
        "preview_label": "Preview",
        "state_badge": "READY",
        "disabled": False,
        "prompt_lines": build_empty_prompt_lines(),
    }


def build_assistant_message(answer: str, raw_rows: list[dict]) -> str:
    """为消息历史生成适合展示的结果摘要。"""
    if answer:
        return answer
    if raw_rows:
        return f"查询已完成，结果工作区展示了 {len(raw_rows)} 行数据。"
    return "本轮没有命中结果，可以调整时间范围、指标口径或筛选条件。"


def calculate_table_height(row_count: int) -> int:
    """按结果行数压缩表格高度，避免少量数据也留下大块空白。"""
    if row_count <= 0:
        return 180
    visible_rows = min(row_count, 10)
    return min(496, 56 + visible_rows * 44)


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


def build_chart_layout() -> dict:
    """统一图表外观，使其贴合新版证据区风格。"""
    return dict(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#F7F9FB",
        font=dict(color="#171C22", family="Funnel Sans, Avenir Next, Segoe UI, PingFang SC, sans-serif"),
        margin=dict(l=12, r=12, t=10, b=28),
        xaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            zeroline=False,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(size=10, color="#7A8591"),
        ),
        yaxis=dict(
            gridcolor="rgba(217,225,232,0.65)",
            zeroline=False,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(size=10, color="#7A8591"),
        ),
        height=240,
        showlegend=False,
    )


def render_chart(chart_config: dict, raw_rows: list[dict]) -> None:
    """根据 Report Agent 输出的图表配置，用 Plotly 渲染图表。"""
    if not chart_config or not raw_rows:
        return

    df = pd.DataFrame(raw_rows)
    chart_type = chart_config.get("type")
    x_col = chart_config.get("x")
    y_cols = [col for col in chart_config.get("y", []) if col in df.columns]
    if x_col not in df.columns or not y_cols:
        return

    common_layout = build_chart_layout()
    bar_colors = ["#11161D", "#24313D", "#4A9FD8", "#9BC4E3", "#C9DCEC"]

    if chart_type == "line":
        fig = px.line(
            df,
            x=x_col,
            y=y_cols,
            markers=True,
            color_discrete_sequence=["#4A9FD8", "#11161D", "#7A8591"],
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=8))
        fig.update_layout(**common_layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
    elif chart_type == "bar":
        limited_df = df.head(5)
        fig = px.bar(
            limited_df,
            x=x_col,
            y=y_cols[0],
        )
        fig.update_traces(marker_color=bar_colors[: len(limited_df)], marker_line_width=0)
        fig.update_layout(**common_layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def render_header(db_error: str | None, latest_result: dict | None) -> None:
    """渲染顶部题签与状态。"""
    model = build_header_model(db_error, latest_result)
    layout = build_layout_config()
    info_col, action_col = st.columns(layout["header_columns"], gap=layout["header_gap"])

    with info_col:
        st.markdown(
            f"""
            <div class="atelier-header">
              <p class="atelier-eyebrow">{html.escape(model["eyebrow"])}</p>
              <h1 class="atelier-title">{html.escape(model["title"])}</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action_col:
        st.markdown(
            f'<div style="margin-top:{layout["header_action_offset_rem"]}rem;">',
            unsafe_allow_html=True,
        )
        control_spacer, control_col = st.columns([0.36, 0.64], gap="small")
        with control_col:
            st.markdown(
                f"""
                <div class="status-pill">
                  <span class="status-dot {html.escape(model['status_dot_class'])}"></span>
                  <span>{html.escape(model["status_text"])}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
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
    """把 process thread 拼成一整块 HTML。"""
    thread_items = "".join(
        f'<div class="process-item">'
        f'<p class="process-meta">{html.escape(item["meta"])}</p>'
        f'<p class="process-body {html.escape(item["tone"])}">{html.escape(item["content"])}</p>'
        "</div>"
        for item in items
    )
    return (
        '<div class="process-shell">'
        '<p class="section-kicker">+ PROCESS THREAD</p>'
        f'<div class="process-list">{thread_items}</div>'
        "</div>"
    )


def render_conversation_panel(messages: list[dict], latest_result: dict | None) -> None:
    """渲染分析态中的 process thread。"""
    panel = build_conversation_panel(messages, latest_result)
    if not panel["items"]:
        return
    st.markdown(_build_conversation_thread_html(panel["items"]), unsafe_allow_html=True)


def _render_summary_hero(summary: dict) -> None:
    """渲染分析态 Hero。"""
    metric_cards = "".join(
        f"""
        <div class="hero-metric">
          <p class="metric-label">{html.escape(item["label"])}</p>
          <p class="metric-value">{html.escape(item["value"])}</p>
        </div>
        """
        for item in summary["metric_items"]
    )
    hero_marks = "".join('<span class="hero-plus">+</span>' for _ in range(4))
    st.markdown(
        f"""
        <div class="analysis-hero">
          <div class="hero-top">
            <div class="hero-copy-block">
              <p class="hero-kicker">{html.escape(summary["kicker"])}</p>
              <h3 class="hero-title">{html.escape(summary["title"])}</h3>
              <p class="hero-copy">{html.escape(summary["summary"])}</p>
            </div>
            <div class="hero-side">
              {hero_marks}
              <span class="hero-side-note">detail trail ready</span>
            </div>
          </div>
          {'<div class="hero-metrics">' + metric_cards + '</div>' if summary["metric_items"] else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_follow_up_cards(follow_ups: list[dict], title: str) -> None:
    """渲染页尾 Next Questions。"""
    items = "".join(
        f"""
        <div class="follow-item">
          <p class="follow-question">{html.escape(item["title"])}</p>
        </div>
        """
        for item in follow_ups
    )
    st.markdown(
        f"""
        <div class="follow-shell">
          <p class="section-kicker">{html.escape(title)}</p>
          <div class="follow-list">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_data_table_shell(raw_rows: list[dict], title: str) -> None:
    """用 HTML 表格渲染 Evidence Table。"""
    if not raw_rows:
        return

    columns = list(raw_rows[0].keys())
    header_html = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    body_html = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape('' if row.get(column) is None else str(row.get(column)))}</td>"
            for column in columns
        )
        + "</tr>"
        for row in raw_rows
    )
    st.markdown(
        f"""
        <div class="evidence-shell">
          <p class="section-kicker">+ EVIDENCE TABLE</p>
          <div class="evidence-card">
            <h3 class="evidence-title">{html.escape(title)}</h3>
            <div class="table-shell">
            <div class="table-scroll">
              <table class="data-table">
                <thead><tr>{header_html}</tr></thead>
                <tbody>{body_html}</tbody>
              </table>
            </div>
            </div>
            <div class="evidence-rule"></div>
            <div class="evidence-meta-row">
              <p class="evidence-meta">Rows {len(raw_rows)}</p>
              <p class="evidence-meta">Snapshot table</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_workspace_preview(previews: list[dict]) -> None:
    """渲染空状态下的结果预期板。"""
    cards = "".join(
        f"""
        <div class="preview-metric">
          <p class="metric-label">{html.escape(item["label"])}</p>
          <p class="metric-value">{html.escape(item["value"])}</p>
        </div>
        """
        for item in previews
    )
    st.markdown(
        f"""
        <div class="preview-shell">
          <p class="section-kicker">+ WHAT ARRIVES AFTER YOU ASK</p>
          <div class="preview-hero">
            <p class="section-kicker">+ RESULT PREVIEW</p>
            <h3 class="preview-title">A centered result board appears first, before the detail trail begins.</h3>
            <div class="preview-metrics">{cards}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sample_result_card() -> None:
    """空状态不再使用旧的示例结果卡。"""
    return None


def render_workspace(latest_result: dict | None) -> None:
    """渲染分析态主瀑布内容。"""
    result = latest_result or {}
    answer = result.get("answer", "")
    chart_config = result.get("chart_config")
    raw_rows = result.get("raw_rows", [])
    workspace = build_workspace_sections(latest_result)
    sections = workspace["sections"]

    if workspace["mode"] == "empty":
        return

    _render_summary_hero(workspace["summary"])
    st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
    render_conversation_panel(st.session_state.messages, latest_result)

    if sections["show_insight"] and answer:
        insight_title, _ = summarize_answer_for_ui(answer)
        st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="judgment-shell">
              <p class="section-kicker">+ CORE JUDGMENT</p>
              <h2 class="judgment-title">{html.escape(insight_title)}</h2>
              <div class="judgment-copy">{_render_simple_markdown_html(answer)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if sections["show_chart"] and chart_config and raw_rows:
        st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="evidence-shell">
              <p class="section-kicker">+ EVIDENCE VISUAL</p>
              <div class="evidence-card">
                <h3 class="evidence-title">{html.escape(workspace["chart_title"])}</h3>
            """,
            unsafe_allow_html=True,
        )
        render_chart(chart_config, raw_rows)
        st.markdown(
            f"""
                <div class="evidence-rule"></div>
                <div class="evidence-meta-row">
                  <p class="evidence-meta">Visual cluster</p>
                  <p class="evidence-meta">Rows {len(raw_rows)}</p>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if sections["show_table"] and raw_rows:
        st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
        _render_data_table_shell(raw_rows, workspace["table_title"])
        if workspace["table_note"]:
            st.markdown(f'<p class="evidence-note">{html.escape(workspace["table_note"])}</p>', unsafe_allow_html=True)

    if workspace["follow_ups"]:
        st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
        _render_follow_up_cards(workspace["follow_ups"], workspace["follow_up_title"])


def render_input_bar(schema: str | None, db_error: str | None, latest_result: dict | None) -> None:
    """按当前状态渲染输入托盘。"""
    if st.session_state.get("pending_clear_analysis_question"):
        st.session_state.analysis_question = ""
        st.session_state.pending_clear_analysis_question = False

    model = build_input_model(db_error, latest_result)
    layout = build_layout_config()

    if latest_result:
        st.markdown('<div class="analysis-input-row">', unsafe_allow_html=True)
    else:
        st.markdown(
            f"""
            <div class="entry-card">
              <p class="section-kicker">{html.escape(model["entry_kicker"])}</p>
              <h2 class="entry-title">{html.escape(model["entry_title"])}</h2>
            """,
            unsafe_allow_html=True,
        )

    input_cols = st.columns(layout["input_columns"], gap="small", vertical_alignment="center")

    with input_cols[0]:
        st.markdown('<div class="input-field-stack">', unsafe_allow_html=True)
        question = st.text_input(
            "Business question",
            key="analysis_question",
            placeholder=model["placeholder"],
            label_visibility="collapsed",
            disabled=bool(model["disabled"]),
        )
        st.markdown(f'<div class="input-ready-badge">{html.escape(model["state_badge"])}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with input_cols[1]:
        generate_clicked = st.button(
            model["button_label"],
            key="input_generate",
            type="primary",
            use_container_width=True,
            disabled=bool(model["disabled"]),
        )

    with input_cols[2]:
        preview_clicked = st.button(
            model["preview_label"],
            key="input_preview",
            type="secondary",
            use_container_width=True,
        )

    if latest_result:
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        prompt_lines = "".join(
            f'<p class="prompt-line">{html.escape(line)}</p>' for line in model["prompt_lines"]
        )
        st.markdown(f'<div class="empty-prompts">{prompt_lines}</div></div>', unsafe_allow_html=True)

    if preview_clicked:
        activate_quick_preview()
        return

    if generate_clicked:
        handle_question(schema, db_error, question.strip())


def render_empty_state_page(schema: str | None, db_error: str | None) -> None:
    """渲染空状态整页。"""
    render_input_bar(schema, db_error, latest_result=None)
    st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
    _render_workspace_preview(build_workspace_preview_items())


def render_analysis_state_page(schema: str | None, db_error: str | None, latest_result: dict) -> None:
    """渲染分析态整页。"""
    render_input_bar(schema, db_error, latest_result)
    st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
    render_workspace(latest_result)


def init_state() -> None:
    """初始化页面会话状态。"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "latest_result" not in st.session_state:
        st.session_state.latest_result = None
    if "analysis_question" not in st.session_state:
        st.session_state.analysis_question = ""
    if "pending_clear_analysis_question" not in st.session_state:
        st.session_state.pending_clear_analysis_question = False


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
    st.session_state.pending_clear_analysis_question = True
    st.rerun()


def render_app() -> None:
    """渲染与 .pen 一致的两状态分析页面。"""
    st.set_page_config(page_title=PAGE_TITLE, page_icon="📊", layout="wide")
    layout = build_layout_config()
    inject_styles(layout)
    init_state()

    schema, db_error = load_schema()
    latest_result = st.session_state.latest_result

    render_header(db_error, latest_result)
    st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)

    if latest_result:
        render_analysis_state_page(schema, db_error, latest_result)
    else:
        render_empty_state_page(schema, db_error)


if __name__ == "__main__":
    render_app()
