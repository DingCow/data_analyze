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
        self.assertEqual(layout["input_columns"], [0.64, 0.22, 0.14])
        self.assertGreater(layout["content_section_gap_rem"], 1.0)

    def test_build_header_model_uses_editorial_copy(self):
        online = app.build_header_model(db_error=None, latest_result=None)
        offline = app.build_header_model(db_error="down", latest_result=None)

        self.assertEqual(online["eyebrow"], "+ ANALYSIS ATELIER")
        self.assertEqual(online["status_text"], "DATA SOURCE ONLINE")
        self.assertEqual(online["status_dot_class"], "is-online")
        self.assertEqual(offline["status_text"], "DATA SOURCE OFFLINE")
        self.assertEqual(offline["status_dot_class"], "is-error")

    def test_build_input_model_empty_state_uses_pen_copy(self):
        model = app.build_input_model(db_error=None, latest_result=None)

        self.assertEqual(model["entry_kicker"], "+ BEGIN WITH ONE QUESTION")
        self.assertIn("Start from a business judgment", model["entry_title"])
        self.assertEqual(model["button_label"], "Generate")
        self.assertEqual(model["preview_label"], "Preview")
        self.assertEqual(model["state_badge"], "READY")
        self.assertEqual(
            model["prompt_lines"],
            ["1. Top 10 declining cities", "2. Order vs price mix", "3. Quarterly anomaly scan"],
        )

    def test_build_input_model_analysis_state_updates_placeholder(self):
        model = app.build_input_model(
            db_error=None,
            latest_result={"answer": "ok", "chart_config": None, "raw_rows": [{"a": 1}]},
        )

        self.assertIn("sharpest order decline", model["placeholder"])

    def test_workspace_preview_items_match_empty_state_board(self):
        preview_items = app.build_workspace_preview_items()

        self.assertEqual(
            preview_items,
            [
                {"label": "Judgment", "value": "One clear answer"},
                {"label": "Visuals", "value": "Chart + table"},
                {"label": "Follow-up", "value": "Next questions"},
            ],
        )

    def test_summarize_answer_for_ui_extracts_title_and_summary(self):
        title, summary = app.summarize_answer_for_ui(
            "## Core judgment\nMost underperforming cities are being dragged by order loss.\nThe next move is to inspect activity and location concentration."
        )

        self.assertIn("Most underperforming cities", title)
        self.assertIn("The next move", summary)

    def test_build_conversation_panel_returns_three_process_items(self):
        panel = app.build_conversation_panel(
            messages=[
                {"role": "user", "content": "Which cities lost momentum?"},
                {"role": "assistant", "content": "Result ready."},
            ],
            latest_result={"answer": "ok", "chart_config": {"type": "bar"}, "raw_rows": [{"City": "A"}]},
        )

        self.assertEqual(len(panel["items"]), 3)
        self.assertEqual(panel["items"][0]["meta"], "QUESTION 01 · USER")
        self.assertEqual(panel["items"][1]["meta"], "STEP 02 · ASSISTANT")
        self.assertEqual(panel["items"][2]["meta"], "STEP 03 · EVIDENCE")

    def test_build_workspace_sections_empty_state_has_preview_only(self):
        workspace = app.build_workspace_sections(None)

        self.assertEqual(workspace["mode"], "empty")
        self.assertEqual(len(workspace["preview_items"]), 3)
        self.assertEqual(workspace["follow_ups"], [])

    def test_build_workspace_sections_analysis_state_has_editorial_sections(self):
        workspace = app.build_workspace_sections(
            {
                "answer": "## Core judgment\nMost underperforming cities are being dragged by order loss.",
                "chart_config": {"type": "bar", "x": "City", "y": ["Orders"], "title": "Quarterly revenue decline by city cluster"},
                "raw_rows": [{"City": "A", "Orders": 10}, {"City": "B", "Orders": 8}],
            }
        )

        self.assertEqual(workspace["mode"], "analysis")
        self.assertEqual(workspace["summary"]["kicker"], "+ RESULT PATTERN")
        self.assertEqual(workspace["follow_up_title"], "+ NEXT QUESTIONS")
        self.assertTrue(workspace["sections"]["show_chart"])
        self.assertTrue(workspace["sections"]["show_table"])
        self.assertEqual(len(workspace["follow_ups"]), 3)

    def test_quick_preview_payload_matches_new_ui_language(self):
        payload = app.build_quick_preview_payload()

        self.assertIn("Which cities lost the most revenue momentum", payload["messages"][0]["content"])
        self.assertEqual(payload["latest_result"]["chart_config"]["title"], "Quarterly revenue decline by city cluster")
        self.assertIn("Core judgment", payload["latest_result"]["answer"])

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
        self.assertIn('--display: "Newsreader"', css)
        self.assertIn('--body: "Funnel Sans"', css)
        self.assertIn('--mono: "IBM Plex Mono"', css)
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
        self.assertIn("+ ANALYSIS ATELIER", joined)
        self.assertIn("DATA SOURCE ONLINE", joined)
        self.assertIn('class="status-pill"', joined)

    def test_render_workspace_outputs_new_section_labels(self):
        app.st.session_state.messages = [
            {"role": "user", "content": "Which cities lost the most revenue momentum over the last quarter?"},
            {"role": "assistant", "content": "Result ready."},
        ]

        with patch.object(app.st, "markdown") as mock_markdown, patch.object(app, "render_chart") as mock_chart:
            app.render_workspace(
                {
                    "answer": "## Core judgment\nMost underperforming cities are being dragged by order loss.",
                    "chart_config": {"type": "bar", "x": "City", "y": ["Orders"], "title": "Quarterly revenue decline by city cluster"},
                    "raw_rows": [{"City": "A", "Orders": 10}],
                }
            )

        joined = "\n".join(str(call.args[0]) for call in mock_markdown.call_args_list if call.args)
        self.assertIn("+ PROCESS THREAD", joined)
        self.assertIn("+ CORE JUDGMENT", joined)
        self.assertIn("+ EVIDENCE VISUAL", joined)
        self.assertIn("+ EVIDENCE TABLE", joined)
        self.assertIn("+ NEXT QUESTIONS", joined)
        mock_chart.assert_called_once()

    def test_handle_question_marks_pending_clear_instead_of_directly_resetting_widget_value(self):
        app.st.session_state.messages = []
        app.st.session_state.latest_result = None
        app.st.session_state.analysis_question = "Which cities lost the most revenue momentum?"
        app.st.session_state.pending_clear_analysis_question = False

        with patch.object(app.router, "run", return_value=("## Core judgment\nOrders are down.", None, [])), patch.object(
            app.st, "rerun"
        ) as mock_rerun:
            app.handle_question("schema", None, "Which cities lost the most revenue momentum?")

        self.assertEqual(app.st.session_state.analysis_question, "Which cities lost the most revenue momentum?")
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
