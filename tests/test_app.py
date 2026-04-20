import unittest
from unittest.mock import patch
import sys
import types


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:  # pragma: no cover
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _ContextBlock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


fake_streamlit = types.ModuleType("streamlit")
fake_streamlit.session_state = _SessionState()
fake_streamlit.cache_resource = lambda func: func
fake_streamlit.markdown = lambda *args, **kwargs: None
fake_streamlit.columns = lambda spec, **kwargs: [_ContextBlock() for _ in spec]
fake_streamlit.text_input = lambda *args, **kwargs: ""
fake_streamlit.button = lambda *args, **kwargs: False
fake_streamlit.plotly_chart = lambda *args, **kwargs: None
fake_streamlit.set_page_config = lambda *args, **kwargs: None
fake_streamlit.rerun = lambda *args, **kwargs: None
fake_streamlit.error = lambda *args, **kwargs: None
fake_streamlit.container = lambda *args, **kwargs: _ContextBlock()
fake_streamlit.spinner = lambda *args, **kwargs: _ContextBlock()
sys.modules.setdefault("streamlit", fake_streamlit)

fake_pandas = types.ModuleType("pandas")
fake_pandas.DataFrame = lambda rows: rows
sys.modules.setdefault("pandas", fake_pandas)

fake_plotly = types.ModuleType("plotly")
fake_px = types.ModuleType("plotly.express")
fake_px.bar = lambda *args, **kwargs: None
fake_px.line = lambda *args, **kwargs: None
fake_plotly.express = fake_px
sys.modules.setdefault("plotly", fake_plotly)
sys.modules.setdefault("plotly.express", fake_px)

fake_router = types.ModuleType("src.workflow.router")
fake_router.run = lambda schema, question, history: ("", None, [])
sys.modules.setdefault("src.workflow.router", fake_router)

import app


class TestEditorialUI(unittest.TestCase):
    """验证新版两状态 UI 的核心模型和渲染入口。"""

    def test_build_layout_config_matches_pen_desktop_width(self):
        layout = app.build_layout_config()

        self.assertEqual(layout["content_mode"], "waterfall")
        self.assertEqual(layout["content_max_width_px"], 820)
        self.assertEqual(layout["input_columns"], [0.56, 0.44])
        self.assertEqual(layout["input_button_columns"], [0.56, 0.44])
        self.assertGreater(layout["content_section_gap_rem"], 1.0)

    def test_build_header_model_uses_editorial_copy(self):
        online = app.build_header_model(db_error=None, latest_result=None)
        offline = app.build_header_model(db_error="down", latest_result=None)

        self.assertEqual(online["eyebrow"], "+ 分析工作台")
        self.assertEqual(online["status_text"], "数据源在线")
        self.assertEqual(online["status_dot_class"], "is-online")
        self.assertEqual(offline["status_text"], "数据源离线")
        self.assertEqual(offline["status_dot_class"], "is-error")

    def test_build_input_model_empty_state_uses_pen_copy(self):
        model = app.build_input_model(db_error=None, latest_result=None)

        self.assertEqual(model["entry_kicker"], "+ 从一个问题开始")
        self.assertIn("先从业务判断出发", model["entry_title"])
        self.assertEqual(model["button_label"], "开始分析")
        self.assertEqual(model["preview_label"], "查看示例")
        self.assertEqual(model["state_badge"], "就绪")
        self.assertEqual(
            model["prompt_lines"],
            ["1. 下滑最明显的前 10 个城市", "2. 订单与价格结构拆分", "3. 季度异常波动扫描"],
        )

    def test_build_input_model_analysis_state_updates_placeholder(self):
        model = app.build_input_model(
            db_error=None,
            latest_result={"answer": "ok", "chart_config": None, "raw_rows": [{"a": 1}]},
        )

        self.assertIn("订单下滑", model["placeholder"])

    def test_workspace_preview_items_match_empty_state_board(self):
        preview_items = app.build_workspace_preview_items()

        self.assertEqual(
            preview_items,
            [
                {"label": "判断", "value": "一个明确结论"},
                {"label": "证据", "value": "图表 + 表格"},
                {"label": "追问", "value": "下一步问题"},
            ],
        )

    def test_summarize_answer_for_ui_extracts_title_and_summary(self):
        title, summary = app.summarize_answer_for_ui(
            "## 核心判断\n表现较弱的城市主要是被订单流失拖累。\n下一步应该继续检查活跃度与区域集中度。"
        )

        self.assertIn("表现较弱的城市", title)
        self.assertIn("下一步", summary)

    def test_build_conversation_panel_returns_three_process_items(self):
        panel = app.build_conversation_panel(
            messages=[
                {"role": "user", "content": "哪些城市的动能下滑了？"},
                {"role": "assistant", "content": "结果已准备好。"},
            ],
            latest_result={"answer": "ok", "chart_config": {"type": "bar"}, "raw_rows": [{"城市": "A"}]},
        )

        self.assertEqual(len(panel["items"]), 3)
        self.assertEqual(panel["items"][0]["meta"], "问题 01 · 用户")
        self.assertEqual(panel["items"][1]["meta"], "步骤 02 · 助手")
        self.assertEqual(panel["items"][2]["meta"], "步骤 03 · 证据")

    def test_build_workspace_sections_empty_state_has_preview_only(self):
        workspace = app.build_workspace_sections(None)

        self.assertEqual(workspace["mode"], "empty")
        self.assertEqual(len(workspace["preview_items"]), 3)
        self.assertEqual(workspace["follow_ups"], [])

    def test_build_workspace_sections_analysis_state_has_editorial_sections(self):
        workspace = app.build_workspace_sections(
            {
                "answer": "## 核心判断\n表现较弱的城市主要是被订单流失拖累。",
                "chart_config": {"type": "bar", "x": "城市", "y": ["订单量"], "title": "城市群季度收入下滑对比"},
                "raw_rows": [{"城市": "A", "订单量": 10}, {"城市": "B", "订单量": 8}],
            }
        )

        self.assertEqual(workspace["mode"], "analysis")
        self.assertEqual(workspace["summary"]["kicker"], "+ 结果概览")
        self.assertEqual(workspace["follow_up_title"], "+ 下一步问题")
        self.assertTrue(workspace["sections"]["show_chart"])
        self.assertTrue(workspace["sections"]["show_table"])
        self.assertEqual(len(workspace["follow_ups"]), 3)

    def test_quick_preview_payload_matches_new_ui_language(self):
        payload = app.build_quick_preview_payload()

        self.assertIn("收入动能下滑最明显", payload["messages"][0]["content"])
        self.assertEqual(payload["latest_result"]["chart_config"]["title"], "城市群季度收入下滑对比")
        self.assertIn("核心判断", payload["latest_result"]["answer"])

    def test_inject_styles_uses_new_editorial_tokens(self):
        captured: list[str] = []
        original_markdown = app.st.markdown

        try:
            app.st.markdown = lambda value, unsafe_allow_html=False: captured.append(value)
            app.inject_styles(app.build_layout_config())
        finally:
            app.st.markdown = original_markdown

        css = captured[0]
        self.assertIn("--page-bg: #f5f7fa;", css)
        self.assertIn('--display: "Source Han Serif SC"', css)
        self.assertIn('--body: "PingFang SC"', css)
        self.assertIn('--mono: "SF Pro Text"', css)
        self.assertIn(".analysis-hero", css)
        self.assertIn(".entry-card", css)
        self.assertIn(".process-item", css)
        self.assertIn(".preview-hero", css)
        self.assertIn(".follow-question", css)
        self.assertNotIn("--bg: #f6f0e3;", css)
        self.assertNotIn("secondary-action.reset-action", css)

    def test_render_header_outputs_editorial_eyebrow_and_status(self):
        with patch.object(app.st, "markdown") as mock_markdown:
            app.render_header(db_error=None, latest_result=None)

        joined = "\n".join(str(call.args[0]) for call in mock_markdown.call_args_list if call.args)
        self.assertIn("+ 分析工作台", joined)
        self.assertIn("数据源在线", joined)
        self.assertIn('class="status-pill"', joined)

    def test_render_workspace_outputs_new_section_labels(self):
        app.st.session_state.messages = [
            {"role": "user", "content": "上个季度哪些城市的收入动能下滑最明显？"},
            {"role": "assistant", "content": "结果已准备好。"},
        ]

        with patch.object(app.st, "markdown") as mock_markdown, patch.object(app, "render_chart") as mock_chart:
            app.render_workspace(
                {
                    "answer": "## 核心判断\n表现较弱的城市主要是被订单流失拖累。",
                    "chart_config": {"type": "bar", "x": "城市", "y": ["订单量"], "title": "城市群季度收入下滑对比"},
                    "raw_rows": [{"城市": "A", "订单量": 10}],
                }
            )

        joined = "\n".join(str(call.args[0]) for call in mock_markdown.call_args_list if call.args)
        self.assertIn("+ 分析过程", joined)
        self.assertIn("+ 核心判断", joined)
        self.assertIn("+ 证据图表", joined)
        self.assertIn("+ 证据表格", joined)
        self.assertIn("+ 下一步问题", joined)
        mock_chart.assert_called_once()

    def test_handle_question_marks_pending_clear_instead_of_directly_resetting_widget_value(self):
        app.st.session_state.messages = []
        app.st.session_state.latest_result = None
        app.st.session_state.analysis_question = "哪些城市的收入动能下滑最明显？"
        app.st.session_state.pending_clear_analysis_question = False

        with patch.object(app.router, "run", return_value=("## 核心判断\n订单量正在下滑。", None, [])), patch.object(
            app.st, "rerun"
        ) as mock_rerun:
            app.handle_question("schema", None, "哪些城市的收入动能下滑最明显？")

        self.assertEqual(app.st.session_state.analysis_question, "哪些城市的收入动能下滑最明显？")
        self.assertTrue(app.st.session_state.pending_clear_analysis_question)
        self.assertIsNotNone(app.st.session_state.latest_result)
        mock_rerun.assert_called_once()

    def test_render_app_routes_to_empty_or_analysis_page(self):
        with patch.object(app, "inject_styles"), patch.object(app, "load_schema", return_value=("schema", None)), patch.object(
            app, "render_header"
        ), patch.object(app, "render_empty_state_page") as mock_empty, patch.object(
            app, "render_analysis_state_page"
        ) as mock_analysis, patch.object(app.st, "set_page_config"), patch.object(app.st, "markdown"):
            app.st.session_state.messages = []
            app.st.session_state.latest_result = None
            app.render_app()
            mock_empty.assert_called_once()
            mock_analysis.assert_not_called()

        with patch.object(app, "inject_styles"), patch.object(app, "load_schema", return_value=("schema", None)), patch.object(
            app, "render_header"
        ), patch.object(app, "render_empty_state_page") as mock_empty, patch.object(
            app, "render_analysis_state_page"
        ) as mock_analysis, patch.object(app.st, "set_page_config"), patch.object(app.st, "markdown"):
            app.st.session_state.messages = []
            app.st.session_state.latest_result = {"answer": "ok", "chart_config": None, "raw_rows": []}
            app.render_app()
            mock_analysis.assert_called_once()
            mock_empty.assert_not_called()


if __name__ == "__main__":
    unittest.main()
