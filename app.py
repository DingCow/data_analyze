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


PAGE_TITLE = "数据分析助手"


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
          --surface-soft: rgba(252, 253, 254, 0.78);
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
          --accent-deep: #2f79b0;
          --shadow-xl: 0 18px 42px rgba(0, 0, 0, 0.10);
          --shadow-lg: 0 14px 34px rgba(0, 0, 0, 0.08);
          --shadow-md: 0 8px 22px rgba(0, 0, 0, 0.07);
          --shadow-sm: 0 8px 18px rgba(17, 22, 29, 0.05);
          --display: "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", serif;
          --body: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif;
          --mono: "SF Pro Text", "PingFang SC", "Helvetica Neue", "Noto Sans SC", sans-serif;
          --title-weight: 580;
          --title-line: 1.2;
          --title-track: -0.015em;
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
          display: grid;
          gap: 1rem;
          padding: 1.2rem 1.35rem 1rem;
          border-radius: 24px 24px 0 0;
          background:
            linear-gradient(180deg, rgba(252, 253, 254, 0.98) 0%, rgba(247, 249, 251, 0.96) 100%);
          border: 1px solid rgba(217, 225, 232, 0.92);
          border-bottom: 0;
          box-shadow: var(--shadow-lg);
        }}

        .entry-copy {{
          display: grid;
          gap: 0.72rem;
        }}

        .entry-topline {{
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 1rem;
        }}

        .entry-side-note {{
          max-width: none;
          margin: 0;
          color: var(--ink-muted);
          font-family: var(--mono);
          font-size: 0.66rem;
          font-weight: 600;
          letter-spacing: 0.12em;
          line-height: 1.2;
          text-align: left;
          text-transform: uppercase;
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
          font-size: 1.95rem !important;
          font-weight: 700 !important;
          line-height: 1.08 !important;
          letter-spacing: -0.024em !important;
          max-width: 100%;
        }}

        .entry-lead {{
          margin: 0;
          max-width: 34rem;
          color: var(--ink-soft);
          font-size: 0.9rem;
          line-height: 1.72;
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

        div[data-testid="stTextInput"] [data-testid="stTextInputRootElement"],
        div[data-testid="stTextInput"] [data-baseweb="base-input"] {{
          min-height: 58px;
          height: 58px;
          overflow: visible;
          align-items: stretch;
        }}

        div[data-testid="stTextInput"] input {{
          min-height: 58px;
          height: 58px;
          border-radius: 15px;
          border: 1px solid rgba(199, 210, 220, 0.92);
          background: rgba(247, 249, 251, 0.92);
          color: var(--ink);
          font-family: var(--body);
          font-size: 0.96rem;
          font-weight: 500;
          padding-left: 1.1rem;
          padding-right: 4.4rem;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
        }}

        div[data-testid="stTextInput"] input::placeholder {{
          color: var(--ink-muted);
          font-size: 0.84rem;
        }}

        div[data-testid="stTextInput"] input:focus {{
          border-color: rgba(74, 159, 216, 0.72);
          box-shadow: 0 0 0 3px rgba(74, 159, 216, 0.10);
        }}

        .input-ready-badge {{
          display: inline-flex;
          justify-content: flex-end;
          color: var(--accent-deep);
          font-size: 0.66rem;
          font-weight: 600;
          letter-spacing: 0.12em;
          line-height: 1;
          pointer-events: none;
          white-space: nowrap;
        }}

        .stColumn:has(.input-ready-badge) [data-testid="stVerticalBlock"] {{
          position: relative;
        }}

        .stColumn:has(.input-ready-badge)
          .stElementContainer:has([data-testid="stTextInput"])
          + .stElementContainer:has(.input-ready-badge) {{
          position: absolute;
          top: 29px;
          right: 1.2rem;
          transform: translateY(-50%);
          width: auto !important;
          height: auto;
          z-index: 3;
          margin: 0;
        }}

        .stColumn:has(.input-ready-badge)
          .stElementContainer:has([data-testid="stTextInput"])
          + .stElementContainer:has(.input-ready-badge)
          .stMarkdown {{
          margin: 0;
        }}

        .stColumn:has(.input-ready-badge)
          .stElementContainer:has([data-testid="stTextInput"])
          + .stElementContainer:has(.input-ready-badge)
          [data-testid="stMarkdownContainer"] {{
          margin: 0;
          padding: 0;
        }}

        .stButton {{
          display: flex;
          align-items: stretch;
        }}

        .stButton > button {{
          width: 100%;
          min-height: 58px;
          border-radius: 15px;
          font-family: var(--body);
          font-size: 0.88rem;
          font-weight: 600;
          border: 1px solid transparent;
          transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }}

        .stButton > button[kind="primary"] {{
          background: linear-gradient(180deg, #1a212a 0%, #11161d 100%);
          color: var(--hero-ink);
          box-shadow: 0 10px 22px rgba(17, 22, 29, 0.12);
        }}

        .stButton > button[kind="primary"]:hover {{
          transform: translateY(-1px);
          filter: brightness(1.02);
        }}

        .stButton > button[kind="secondary"] {{
          background: rgba(220, 236, 248, 0.72);
          color: var(--accent-deep);
          border-color: rgba(74, 159, 216, 0.14);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45);
        }}

        .stButton > button[kind="secondary"]:hover {{
          transform: translateY(-1px);
          filter: brightness(0.99);
        }}

        .stElementContainer:has(.entry-card) + [data-testid="stLayoutWrapper"] {{
          margin-top: -0.34rem;
          padding: 0 1.35rem 0;
          background: linear-gradient(180deg, rgba(252, 253, 254, 0.98) 0%, rgba(247, 249, 251, 0.96) 100%);
          border-left: 1px solid rgba(217, 225, 232, 0.92);
          border-right: 1px solid rgba(217, 225, 232, 0.92);
          border-bottom: 1px solid rgba(217, 225, 232, 0.92);
          border-bottom-left-radius: 24px;
          border-bottom-right-radius: 24px;
          box-shadow: var(--shadow-lg);
        }}

        .stElementContainer:has(.entry-card) + [data-testid="stLayoutWrapper"] > div {{
          gap: 0.9rem;
        }}

        .empty-prompts {{
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.65rem;
          margin-top: 0.08rem;
        }}

        .prompt-line {{
          margin: 0;
          color: #6d7b8c;
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 0.04em;
          line-height: 1.45;
          padding-top: 0.7rem;
          border-top: 1px solid rgba(217, 225, 232, 0.78);
        }}

        .preview-shell {{
          display: grid;
          gap: 0.8rem;
        }}

        .preview-hero {{
          position: relative;
          overflow: hidden;
          padding: 1.35rem 1.35rem 1.4rem;
          border-radius: 22px;
          background: linear-gradient(180deg, #151b23 0%, #202a35 100%);
          box-shadow: 0 12px 28px rgba(0, 0, 0, 0.08);
        }}

        .preview-hero::before {{
          content: "";
          position: absolute;
          inset: 0;
          background:
            radial-gradient(circle at 80% 18%, rgba(74, 159, 216, 0.12), transparent 22%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.06), transparent 40%);
          pointer-events: none;
        }}

        h3.preview-title,
        .preview-title,
        h3.hero-title,
        .hero-title {{
          margin: 0;
          font-family: var(--display) !important;
          font-weight: 700 !important;
          line-height: 1.08 !important;
          letter-spacing: -0.025em !important;
        }}

        .preview-title {{
          color: var(--hero-ink) !important;
          font-size: 1.58rem !important;
          max-width: 100%;
          white-space: normal;
          position: relative;
          z-index: 1;
        }}

        .preview-metrics,
        .hero-metrics {{
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.82rem;
          margin-top: 1rem;
        }}

        .preview-metric,
        .hero-metric {{
          padding: 0.82rem 0.92rem;
          border-radius: 12px;
          border: 1px solid var(--hero-line);
          background: var(--hero-elevated);
          position: relative;
          z-index: 1;
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
          font-family: var(--body);
        }}

        .analysis-input-row {{
          padding: 0.25rem 0 0.2rem;
          border-top: 1px solid rgba(217, 225, 232, 0.72);
          border-bottom: 1px solid rgba(217, 225, 232, 0.72);
        }}

        .analysis-hero {{
          position: relative;
          overflow: hidden;
          padding: 1.4rem 1.45rem 1.45rem;
          border-radius: 24px;
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
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          align-items: flex-start;
          gap: 0.9rem;
          position: relative;
          z-index: 1;
        }}

        .hero-copy-block {{
          min-width: 0;
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
          font-family: var(--display) !important;
          font-size: 1.34rem !important;
          font-weight: 560 !important;
          line-height: var(--title-line) !important;
          letter-spacing: var(--title-track) !important;
          max-width: 100%;
          white-space: normal;
        }}

        .hero-copy {{
          margin: 0.58rem 0 0;
          color: rgba(245, 247, 250, 0.84) !important;
          font-size: 0.94rem;
          line-height: 1.7;
          max-width: 32rem;
          position: relative;
          z-index: 1;
        }}

        .process-shell,
        .judgment-shell,
        .evidence-shell,
        .follow-shell {{
          position: relative;
        }}

        .rail-card,
        .evidence-card,
        .follow-shell {{
          padding: 1.15rem 1.2rem;
          border-radius: 20px;
          background: rgba(252, 253, 254, 0.78);
          border: 1px solid rgba(217, 225, 232, 0.9);
          box-shadow: var(--shadow-sm);
          backdrop-filter: blur(8px);
        }}

        div[data-testid="stVerticalBlock"]:has(.chart-card-marker) {{
          padding: 1.15rem 1.2rem;
          border-radius: 20px;
          background: rgba(252, 253, 254, 0.78);
          border: 1px solid rgba(217, 225, 232, 0.9);
          box-shadow: var(--shadow-sm);
          backdrop-filter: blur(8px);
        }}

        .chart-card-marker {{
          display: none;
        }}

        .process-list {{
          display: grid;
          gap: 0.82rem;
          margin-top: 0.14rem;
        }}

        .process-item {{
          padding: 0.94rem 0 0.1rem 1.08rem;
          border-left: 2px solid rgba(74, 159, 216, 0.32);
        }}

        .process-meta {{
          margin: 0;
          color: var(--ink-muted);
          font-size: 0.62rem;
          font-weight: 600;
          letter-spacing: 0.16em;
        }}

        .process-body {{
          margin: 0.4rem 0 0;
          color: var(--ink);
          font-family: var(--display);
          line-height: 1.2;
          letter-spacing: -0.015em;
        }}

        .process-body.primary {{
          font-size: 1.28rem;
          font-weight: var(--title-weight);
          line-height: var(--title-line);
          letter-spacing: var(--title-track);
        }}

        .process-body.secondary {{
          color: #495767;
          font-size: 0.96rem;
          font-weight: 500;
          line-height: 1.6;
          font-family: var(--body);
        }}

        h2.judgment-title,
        .judgment-title {{
          margin: 0.05rem 0 0.72rem;
          color: var(--ink) !important;
          font-family: var(--display) !important;
          font-size: 1.28rem !important;
          font-weight: var(--title-weight) !important;
          line-height: var(--title-line) !important;
          letter-spacing: var(--title-track) !important;
          max-width: 100%;
          white-space: normal;
        }}

        .judgment-copy,
        .judgment-copy p,
        .judgment-copy li {{
          color: var(--ink-soft);
          font-size: 0.98rem;
          line-height: 1.78;
          font-family: var(--body);
        }}

        .judgment-copy p {{
          margin: 0.4rem 0 0;
        }}

        .judgment-copy ul,
        .judgment-copy ol {{
          padding-left: 1.05rem;
          margin: 0.45rem 0 0;
        }}

        .evidence-title {{
          margin: 0 0 0.6rem;
          color: var(--ink);
          font-family: var(--display);
          font-size: 1.28rem;
          font-weight: var(--title-weight);
          line-height: var(--title-line);
          letter-spacing: var(--title-track);
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
          font-size: 0.64rem;
          font-weight: 600;
          letter-spacing: 0.12em;
          font-family: var(--mono);
        }}

        .evidence-note {{
          margin: 0.5rem 0 0;
          color: var(--ink-soft);
          font-family: var(--mono);
          font-size: 0.62rem;
          font-weight: 600;
          letter-spacing: 0.04em;
        }}

        div[data-testid="stPlotlyChart"] {{
          margin: 0 !important;
          padding: 0.95rem 1rem;
          border-radius: 14px;
          background: var(--surface-subtle);
          border: 1px solid var(--line);
          box-shadow: none;
        }}

        div[data-testid="stPlotlyChart"] > div {{
          border-radius: 8px;
          overflow: hidden;
        }}

        .table-shell {{
          border-radius: 14px;
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
          padding: 0.9rem 0.92rem;
          text-align: left;
          background: #f2f5f8;
          color: var(--ink-soft);
          font-family: var(--mono);
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          border-bottom: 1px solid var(--line);
          white-space: nowrap;
        }}

        .data-table tbody td {{
          padding: 0.94rem 0.92rem;
          color: var(--ink);
          font-size: 0.88rem;
          border-bottom: 1px solid #e6edf3;
          font-family: var(--body);
        }}

        .data-table tbody tr:last-child td {{
          border-bottom: none;
        }}

        .follow-list {{
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.85rem;
          margin-top: 0.18rem;
        }}

        .follow-item {{
          height: 100%;
          padding: 1.08rem 1.05rem;
          border: 1px solid rgba(217, 225, 232, 0.9);
          border-radius: 16px;
          background: linear-gradient(180deg, rgba(252, 253, 254, 0.82) 0%, rgba(247, 249, 251, 0.9) 100%);
        }}

        .follow-question {{
          margin: 0;
          color: var(--ink);
          font-family: var(--display);
          font-size: 0.98rem;
          font-weight: 600;
          line-height: 1.5;
        }}

        @media (max-width: 900px) {{
          .block-container {{
            padding-left: 0.9rem;
            padding-right: 0.9rem;
          }}

          .atelier-title {{
            font-size: 2.45rem;
          }}

          .entry-topline {{
            grid-template-columns: 1fr;
            display: grid;
          }}

          .entry-title,
          .hero-title,
          .preview-title,
          .judgment-title {{
            max-width: none;
          }}

          .empty-prompts,
          .follow-list {{
            grid-template-columns: 1fr;
          }}

          .hero-top,
          .evidence-meta-row,
          .preview-metrics,
          .hero-metrics {{
            grid-template-columns: 1fr;
            display: grid;
          }}

          .analysis-hero,
          .rail-card,
          .evidence-card,
          .follow-shell,
          .preview-hero {{
            padding-left: 1.05rem;
            padding-right: 1.05rem;
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
        "input_columns": [0.56, 0.44],
        "input_button_columns": [0.56, 0.44],
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
        {"title": "哪些表现较弱的城市，在区县或时段维度上也出现了最明显的订单下滑？", "question": ""},
        {"title": "和上一季度相比，哪些城市的变化主要来自销量，哪些主要来自价格？", "question": ""},
        {"title": "如果只聚焦表现最差的几个城市，下一步应该先从哪里开始排查？", "question": ""},
    ]


def build_empty_prompt_lines() -> list[str]:
    """提供空状态输入板下方的三条轻量提示。"""
    return [
        "1. 下滑最明显的前 10 个城市",
        "2. 订单与价格结构拆分",
        "3. 季度异常波动扫描",
    ]


def build_quick_preview_payload() -> dict:
    """构造一份固定样例，调 UI 时直接进入结果页。"""
    raw_rows = [
        {"城市": "中山", "收入下滑": "-16.4%", "订单量": 23822},
        {"城市": "深圳", "收入下滑": "-12.7%", "订单量": 18302},
        {"城市": "珠海", "收入下滑": "-8.5%", "订单量": 15123},
        {"城市": "佛山", "收入下滑": "-6.2%", "订单量": 13518},
    ]
    answer = """## 核心判断

表现较弱的城市，主要是被订单流失拖累，而不是价格变化。

结果页会先找出收入下滑最明显的城市，再比较订单量与价格变化，判断主要驱动因素。这会直接影响下一步动作：与其先做价格复盘，不如先深入看需求、活跃度，以及差城市在区域层面的订单集中度。"""
    chart_config = {
        "type": "bar",
        "x": "城市",
        "y": ["订单量"],
        "title": "城市群季度收入下滑对比",
    }
    assistant_text = build_assistant_message(answer, raw_rows)
    return {
        "messages": [
            {"role": "user", "content": "上个季度哪些城市的收入动能下滑最明显？"},
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
        {"label": "判断", "value": "一个明确结论"},
        {"label": "证据", "value": "图表 + 表格"},
        {"label": "追问", "value": "下一步问题"},
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
        "eyebrow": "+ 分析工作台",
        "status_text": "数据源离线" if db_error else "数据源在线",
        "status_dot_class": "is-error" if db_error else "is-online",
    }


def summarize_answer_for_ui(answer: str) -> tuple[str, str]:
    """把 markdown 结果压成适合 Hero 与正文区的短标题和摘要。"""
    if not answer:
        return (
            "页面会先给出一个居中的结果面板，再向下展开完整分析链路。",
            "首屏先突出一个核心判断，再沿同一条阅读路径逐步展开证据模块。",
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
            "页面会先给出一个居中的结果面板，再向下展开完整分析链路。",
            "首屏先突出一个核心判断，再沿同一条阅读路径逐步展开证据模块。",
        )

    title = lines[1] if len(lines) > 1 and lines[0].lower() in {"core judgment", "核心判断"} else lines[0]
    summary_candidates = [
        line for line in lines if line != title and line.lower() not in {"core judgment", "核心判断"}
    ]
    summary = summary_candidates[0] if summary_candidates else "结果区会先压缩成一句判断，再在下方展开详细证据。"
    if len(title) > 88:
        title = title[:85].rstrip() + "..."
    if len(summary) > 180:
        summary = summary[:177].rstrip() + "..."
    return title, summary


def strip_judgment_heading_and_lead(answer: str, insight_title: str) -> str:
    """移除 markdown 中与页面标题重复的开头内容，避免 Judgment 区重复。"""
    if not answer:
        return answer

    def normalize_text(value: str) -> str:
        value = re.sub(r"^#+\s*", "", value.strip())
        value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
        value = re.sub(r"`([^`]+)`", r"\1", value)
        value = re.sub(r"[。；;:：,.，、!?！？\s]+$", "", value)
        return value.strip()

    lines = answer.splitlines()
    cleaned: list[str] = []
    skipped_heading = False
    skipped_title = False
    normalized_title = normalize_text(insight_title)

    for raw_line in lines:
        line = raw_line.strip()

        if not skipped_heading and re.match(r"^##\s*(核心判断|Core judgment)\s*$", line, flags=re.I):
            skipped_heading = True
            continue

        normalized_line = normalize_text(line)

        if not skipped_title and normalized_line == normalized_title:
            skipped_title = True
            continue

        if not skipped_title and normalized_title and normalized_line.startswith(normalized_title):
            skipped_title = True
            remainder = normalized_line[len(normalized_title) :].lstrip("。；;:：,.，、!?！？ ")
            if remainder:
                cleaned.append(remainder)
            continue

        cleaned.append(raw_line)

    text = "\n".join(cleaned)
    text = re.sub(r"^\s*\n+", "", text)
    return text.strip()


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
            "meta": "问题 01 · 用户",
            "content": latest_question or "上个季度哪些城市的收入动能下滑最明显？",
            "tone": "primary",
        },
        {
            "meta": "步骤 02 · 助手",
            "content": "结果页会先找出收入下滑最明显的城市，再比较订单量与价格变化，判断真正的主导因素。"
            if answer
            else "结果面板会先出现，随后再沿同一条阅读路径铺开展示证据。",
            "tone": "secondary",
        },
        {
            "meta": "步骤 03 · 证据",
            "content": f"当前已准备好 {len(raw_rows)} 行数据供对比，页面会{'同时给出图表和表格' if has_visual else '先从结构化表格开始展示'}。"
            if raw_rows
            else "一旦首轮查询返回数据，结果面板下方就会接出对应证据。",
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
            "kicker": "+ 结果概览",
            "title": hero_title,
            "summary": hero_copy,
            "metric_items": [
                {"label": "模式", "value": "多步分析" if answer and raw_rows else "直接结果"},
                {"label": "行数", "value": str(len(raw_rows))},
                {"label": "图形", "value": f"{chart_count} 张图" if chart_count else "仅表格"},
            ],
        },
        "insight_title": "表现较弱的城市，主要是被订单流失拖累，而不是价格变化。",
        "chart_title": chart_config.get("title") if chart_config else "城市群季度收入下滑对比",
        "table_title": "城市收入下滑快照",
        "follow_up_title": "+ 下一步问题",
        "sections": {
            "show_insight": bool(answer),
            "show_chart": bool(chart_config and raw_rows),
            "show_table": bool(raw_rows),
        },
        "follow_ups": follow_ups,
        "preview_items": build_workspace_preview_items(),
        "chart_note": "重点城市" if raw_rows else "",
        "table_note": f"前 {min(len(raw_rows), 3)} 个城市贡献了大部分下滑。" if raw_rows else "",
    }


def build_input_model(db_error: str | None, latest_result: dict | None) -> dict:
    """构造空状态与分析态共用的输入区文案。"""
    result = latest_result or {}
    has_result = bool(result.get("answer") or result.get("raw_rows"))

    if db_error:
        return {
            "entry_kicker": "+ 从一个问题开始",
            "entry_title": "先从业务判断出发，而不是先看仪表盘。",
            "placeholder": "请先修复数据库连接后再提问",
            "button_label": "开始分析",
            "preview_label": "查看示例",
            "state_badge": "离线",
            "disabled": True,
            "prompt_lines": build_empty_prompt_lines(),
            "entry_lead": "先把现象问清楚，页面会先给一句判断，再把图表、表格和下一步追问依次接出来。",
            "entry_side_note": "问题输入优先",
        }

    return {
        "entry_kicker": "+ 从一个问题开始",
        "entry_title": "先从业务判断出发，而不是先看仪表盘。",
        "placeholder": "为什么有些城市的收入动能在走弱？"
        if not has_result
        else "哪些表现较弱的城市，同时也出现了最明显的订单下滑？",
        "button_label": "开始分析",
        "preview_label": "查看示例",
        "state_badge": "就绪",
        "disabled": False,
        "prompt_lines": build_empty_prompt_lines(),
        "entry_lead": "把业务现象翻成一个可验证的问题，结果页会先给结论，再把证据和下一步动作接出来。",
        "entry_side_note": "问题输入优先",
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
        font=dict(color="#171C22", family="PingFang SC, Hiragino Sans GB, Microsoft YaHei, Noto Sans SC, sans-serif"),
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
        '<div class="rail-card process-shell">'
        '<p class="section-kicker">+ 分析过程</p>'
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
    st.markdown(
        f"""
        <div class="analysis-hero">
          <div class="hero-top">
            <div class="hero-copy-block">
              <p class="hero-kicker">{html.escape(summary["kicker"])}</p>
              <h3 class="hero-title">{html.escape(summary["title"])}</h3>
              <p class="hero-copy">{html.escape(summary["summary"])}</p>
            </div>
          </div>
          {'<div class="hero-metrics">' + metric_cards + '</div>' if summary["metric_items"] else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_chart_shell(chart_config: dict, raw_rows: list[dict], title: str) -> None:
    """使用 Streamlit 容器渲染完整图表卡，避免 HTML 包裹组件时出现空白容器。"""
    with st.container():
        st.markdown('<div class="chart-card-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="evidence-shell">
              <p class="section-kicker">+ 证据图表</p>
              <h3 class="evidence-title">{html.escape(title)}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_chart(chart_config, raw_rows)
        st.markdown(
            f"""
            <div class="evidence-shell">
              <div class="evidence-rule"></div>
              <div class="evidence-meta-row">
                <p class="evidence-meta">图形视图</p>
                <p class="evidence-meta">行数 {len(raw_rows)}</p>
              </div>
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
          <p class="section-kicker">+ 证据表格</p>
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
              <p class="evidence-meta">行数 {len(raw_rows)}</p>
              <p class="evidence-meta">快照表</p>
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
          <p class="section-kicker">+ 提问之后会出现什么</p>
          <div class="preview-hero">
            <p class="section-kicker">+ 结果预览</p>
            <h3 class="preview-title">页面会先给出一个居中的结果面板，再向下展开完整分析链路。</h3>
            <p class="hero-copy">先用一句话锁定判断，再把图表、明细表和下一步追问串成同一条阅读路径。</p>
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
    rail_cols = st.columns([1, 1], gap="small", vertical_alignment="top")

    with rail_cols[0]:
        render_conversation_panel(st.session_state.messages, latest_result)

    with rail_cols[1]:
        if sections["show_insight"] and answer:
            insight_title, _ = summarize_answer_for_ui(answer)
            judgment_body = strip_judgment_heading_and_lead(answer, insight_title)
            st.markdown(
                f"""
                <div class="rail-card judgment-shell">
                  <p class="section-kicker">+ 核心判断</p>
                  <h2 class="judgment-title">{html.escape(insight_title)}</h2>
                  <div class="judgment-copy">{_render_simple_markdown_html(judgment_body)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if sections["show_chart"] or sections["show_table"]:
        st.markdown('<div class="atelier-gap"></div>', unsafe_allow_html=True)
        evidence_cols = st.columns([1, 1], gap="small", vertical_alignment="top")

        with evidence_cols[0]:
            if sections["show_chart"] and chart_config and raw_rows:
                _render_chart_shell(chart_config, raw_rows, workspace["chart_title"])

        with evidence_cols[1]:
            if sections["show_table"] and raw_rows:
                _render_data_table_shell(raw_rows, workspace["table_title"])
                if workspace["table_note"]:
                    st.markdown(
                        f'<p class="evidence-note">{html.escape(workspace["table_note"])}</p>',
                        unsafe_allow_html=True,
                    )

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
        prompt_lines = "".join(
            f'<p class="prompt-line">{html.escape(line)}</p>' for line in model["prompt_lines"]
        )
        st.markdown(
            f"""
            <div class="entry-card">
              <div class="entry-copy">
                <div class="entry-topline">
                  <div>
                    <p class="section-kicker">{html.escape(model["entry_kicker"])}</p>
                    <h2 class="entry-title">{html.escape(model["entry_title"])}</h2>
                  </div>
                  <p class="entry-side-note">{html.escape(model["entry_side_note"])}</p>
                </div>
                <p class="entry-lead">{html.escape(model["entry_lead"])}</p>
                <div class="empty-prompts">{prompt_lines}</div>
              </div>
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
        button_cols = st.columns(layout["input_button_columns"], gap="small", vertical_alignment="center")
        with button_cols[0]:
            generate_clicked = st.button(
                model["button_label"],
                key="input_generate",
                type="primary",
                use_container_width=True,
                disabled=bool(model["disabled"]),
            )
        with button_cols[1]:
            preview_clicked = st.button(
                model["preview_label"],
                key="input_preview",
                type="secondary",
                use_container_width=True,
            )

    if latest_result:
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("</div>", unsafe_allow_html=True)

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
