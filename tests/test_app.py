import unittest
import re
from unittest.mock import patch

import app


class TestHomepageViewModels(unittest.TestCase):
    """验证首页改版后的文案与状态模型。"""

    def test_build_layout_config_compacts_header_and_prioritizes_workspace(self):
        layout = app.build_layout_config()

        self.assertEqual(layout["header_columns"], [0.78, 0.22])
        self.assertEqual(layout["content_mode"], "waterfall")
        self.assertLessEqual(layout["content_max_width_px"], 1080)
        self.assertLessEqual(layout["content_section_gap_rem"], 0.14)
        self.assertEqual(layout["workspace_density"], "compact")
        self.assertLess(layout["workspace_title_size_rem"], 1.3)
        self.assertLess(layout["summary_title_size_rem"], 1.0)
        self.assertLess(layout["summary_hero_padding_rem"], 0.7)
        self.assertLess(layout["metric_value_size_rem"], 0.85)
        self.assertEqual(layout["header_gap"], "small")
        self.assertLessEqual(layout["header_action_offset_rem"], 0.05)
        self.assertLessEqual(layout["input_columns"][0], 0.8)
        self.assertGreaterEqual(layout["input_columns"][1], 0.2)

    def test_build_header_model_only_describes_data_source_status(self):
        header = app.build_header_model(
            db_error=None,
            latest_result={"answer": "", "chart_config": None, "raw_rows": [{"value": 1}, {"value": 2}]},
        )

        self.assertEqual(header["title"], "Data Analyze Agent")
        self.assertEqual(
            header["subtitle"],
            "输入业务问题，直接获得核心判断、关键数据和推荐追问。",
        )
        self.assertEqual(header["status_label"], "数据源状态")
        self.assertEqual(header["status_value"], "在线")
        self.assertEqual(header["status_dot_class"], "is-online")
        self.assertEqual(header["status_detail"], "")

    def test_build_input_model_uses_analysis_assistant_copy(self):
        model = app.build_input_model(db_error=None, latest_result=None)

        self.assertEqual(model["title"], "从一个业务判断开始")
        self.assertEqual(model["button_label"], "生成分析结论")
        self.assertEqual(model["copy"], "")
        self.assertIn("为什么某些城市收入下滑", model["placeholder"])
        self.assertEqual(model["hint"], "")

    def test_build_input_model_hides_follow_up_copy_when_result_exists(self):
        model = app.build_input_model(
            db_error=None,
            latest_result={"answer": "## 结论\n收入上升", "chart_config": None, "raw_rows": [{"收入": 1}]},
        )

        self.assertEqual(model["title"], "继续补充这轮判断")
        self.assertEqual(model["copy"], "")

    def test_build_quick_preview_payload_provides_ready_to_render_fixture(self):
        payload = app.build_quick_preview_payload()

        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertIn("广东", payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][1]["role"], "assistant")
        self.assertIn("核心判断", payload["messages"][1]["content"])
        self.assertIn("chart_config", payload["latest_result"])
        self.assertGreaterEqual(len(payload["latest_result"]["raw_rows"]), 3)
        self.assertEqual(payload["latest_result"]["chart_config"]["type"], "bar")

    def test_activate_quick_preview_writes_fixture_to_session(self):
        with patch.object(app.st, "rerun") as mock_rerun:
            app.st.session_state.messages = []
            app.st.session_state.latest_result = None

            app.activate_quick_preview()

        self.assertEqual(len(app.st.session_state.messages), 2)
        self.assertIsNotNone(app.st.session_state.latest_result)
        self.assertEqual(app.st.session_state.latest_result["chart_config"]["type"], "bar")
        mock_rerun.assert_called_once()

    def test_build_workspace_sections_for_empty_state_provides_examples(self):
        workspace = app.build_workspace_sections(None)

        self.assertEqual(workspace["mode"], "empty")
        self.assertEqual(workspace["summary"]["title"], "结果判断")
        self.assertEqual(workspace["summary"]["mode_label"], "示例预览")
        self.assertEqual(workspace["summary"]["description"], "")
        self.assertEqual(workspace["summary"]["metric_items"], [])
        self.assertEqual(len(workspace["preview_items"]), 3)
        self.assertEqual(workspace["follow_ups"], [])
        self.assertEqual(workspace["preview_items"][0]["title"], "核心判断")
        self.assertEqual(workspace["empty_hint"], "")

    def test_visual_refresh_removes_analysis_flow_helper(self):
        self.assertFalse(hasattr(app, "build_analysis_flow"))

    def test_build_workspace_sections_for_result_state_focuses_current_round(self):
        workspace = app.build_workspace_sections(
            {
                "answer": "## 结论\n上海收入最高",
                "chart_config": None,
                "raw_rows": [{"城市": "上海", "收入": 100}],
            }
        )

        self.assertEqual(workspace["mode"], "analysis")
        self.assertEqual(workspace["summary"]["title"], "结果判断")
        self.assertEqual(workspace["summary"]["mode_label"], "")
        self.assertTrue(workspace["sections"]["show_insight"])
        self.assertTrue(workspace["sections"]["show_table"])
        self.assertEqual(workspace["insight_title"], "核心判断")
        self.assertEqual(workspace["table_title"], "关键数据")
        self.assertEqual(workspace["follow_up_title"], "推荐追问")

    def test_build_workspace_sections_uses_router_metrics_in_summary(self):
        workspace = app.build_workspace_sections(
            {
                "answer": "## 结论\n上海收入最高",
                "chart_config": {"type": "bar", "x": "城市", "y": ["收入"], "title": "收入对比"},
                "raw_rows": [{"城市": "上海", "收入": 100}, {"城市": "北京", "收入": 80}],
            }
        )

        self.assertEqual(workspace["summary"]["title"], "结果判断")
        self.assertEqual(
            workspace["summary"]["metric_items"],
            [
                {"label": "分析类型", "value": "复杂链路"},
                {"label": "数据行数", "value": "2 行"},
                {"label": "图表数", "value": "1 张"},
            ],
        )

    def test_build_conversation_panel_uses_welcome_state_before_any_question(self):
        panel = app.build_conversation_panel(messages=[], latest_result=None)

        self.assertEqual(panel["title"], "")
        self.assertEqual(panel["helper_text"], "")
        self.assertEqual(panel["examples_title"], "")
        self.assertEqual(len(panel["examples"]), 0)
        self.assertFalse(panel["items"])

    def test_inject_styles_uses_apple_workbench_tokens(self):
        captured: list[str] = []
        original_markdown = app.st.markdown

        try:
            app.st.markdown = lambda value, unsafe_allow_html=False: captured.append(value)
            app.inject_styles(app.build_layout_config())
        finally:
            app.st.markdown = original_markdown

        css = captured[0]
        self.assertIn("--bg: #f6f0e3;", css)
        self.assertIn("--surface: rgba(255, 251, 245, 0.74);", css)
        self.assertIn("--surface-strong: rgba(255, 252, 247, 0.92);", css)
        self.assertIn("--accent: #a24a2a;", css)
        self.assertIn("backdrop-filter: blur(24px);", css)
        self.assertIn("border-radius: 30px !important;", css)
        self.assertNotIn(".flow-shell", css)
        self.assertIn(".plain-section.suggested-questions", css)
        self.assertIn(".plain-section.follow-up-shell", css)
        self.assertIn(".conversation-panel.process-shell", css)
        self.assertIn(".insight-card.insight-shell", css)
        self.assertIn('div[data-testid="stFormSubmitButton"]', css)
        self.assertIn('--font-display: "Baskerville"', css)
        self.assertIn('--font-body: "Avenir Next"', css)
        self.assertIn(".status-dot", css)
        self.assertIn(".status-dot.is-online", css)
        self.assertIn(".status-dot.is-error", css)
        self.assertIn("--workspace-stack-gap: 0.72rem;", css)
        self.assertIn(".header-utility-actions", css)
        self.assertIn(".secondary-action.preview-action .stButton > button", css)
        self.assertIn(".secondary-action.reset-action .stButton > button", css)
        self.assertIn(".summary-topline", css)
        self.assertIn(".summary-kicker", css)
        self.assertRegex(css, r"\.shell-title\s*\{[^}]*font-weight:\s*700;")
        self.assertRegex(css, r"\.panel-title\s*\{[^}]*font-weight:\s*600;")
        self.assertRegex(css, r"\.shell-copy\s*\{[^}]*font-size:\s*0\.94rem;")
        self.assertRegex(css, r"\.shell-copy\s*\{[^}]*margin:\s*0\.58rem 0 0;")
        self.assertRegex(css, r"\.top-shell\s*\{[^}]*padding:\s*0\.48rem 0 0\.2rem;")
        self.assertRegex(css, r"\.header-action-stack\s*\{[^}]*gap:\s*1\.42rem;")
        self.assertRegex(css, r"\.header-meta-card\s*\{[^}]*display:\s*inline-flex;")
        self.assertRegex(css, r"\.header-meta-card\s*\{[^}]*padding:\s*0\.32rem 0\.54rem;")
        self.assertRegex(css, r"\.header-meta-card\s*\{[^}]*width:\s*fit-content;")
        self.assertRegex(css, r"\.header-meta-card\s*\{[^}]*min-width:\s*0;")
        self.assertRegex(css, r"\.header-meta-card\s*\{[^}]*max-width:\s*none;")
        self.assertRegex(css, r"\.conversation-thread\s*\{[^}]*gap:\s*0\.78rem;")
        self.assertRegex(css, r"\.summary-hero\.results-shell\s*\{[^}]*margin:\s*0;")
        self.assertRegex(css, r"\.insight-card\.insight-shell\s*\{[^}]*margin:\s*0;")
        self.assertRegex(css, r"\.plain-section\.follow-up-shell\s*\{[^}]*margin:\s*0;")
        self.assertIn(".workspace-gap", css)
        self.assertRegex(css, r"\.workspace-gap\s*\{[^}]*height:\s*var\(--workspace-stack-gap\);")
        self.assertIn(".analytics-gap", css)
        self.assertRegex(css, r"\.analytics-gap\s*\{[^}]*height:\s*0;")
        self.assertRegex(css, r"\.table-section\s*\{[^}]*margin:\s*-0\.92rem 0 0;")
        self.assertRegex(css, r"\.section-heading\s*\{[^}]*letter-spacing:\s*0\.14em;")
        self.assertRegex(css, r"\.panel-helper,\s*\.input-copy,\s*\.input-hint\s*\{[^}]*font-size:\s*0\.64rem;")
        self.assertRegex(css, r"\.microcopy\s*\{[^}]*font-size:\s*0\.68rem !important;")
        self.assertRegex(css, r"\.example-card-copy,\s*\.follow-card-copy\s*\{[^}]*font-size:\s*0\.78rem !important;")
        self.assertRegex(css, r"\.summary-copy\s*\{[^}]*font-size:\s*0\.82rem !important;")
        self.assertRegex(css, r"\.metric-label\s*\{[^}]*font-size:\s*0\.66rem;")
        self.assertRegex(css, r"\.empty-copy\s*\{[^}]*font-size:\s*0\.78rem;")
        self.assertRegex(css, r"\.preview-item\s*\{[^}]*font-size:\s*0\.72rem;")
        self.assertRegex(css, r"\.input-shell div\[data-testid=\"stTextInput\"\] input::placeholder\s*\{[^}]*font-size:\s*0\.78rem;")

    def test_render_workspace_empty_state_skips_static_preview_modules(self):
        with patch.object(app, "_render_summary_hero") as mock_summary, patch.object(
            app, "_render_workspace_preview"
        ) as mock_preview, patch.object(app, "_render_sample_result_card") as mock_sample:
            app.render_workspace(None)

        mock_summary.assert_not_called()
        mock_preview.assert_not_called()
        mock_sample.assert_not_called()

    def test_render_workspace_analysis_state_renders_summary_hero_and_insight_body(self):
        with patch.object(app, "_render_summary_hero") as mock_summary, patch.object(
            app.st, "markdown"
        ) as mock_markdown:
            app.render_workspace({"answer": "## 结论\n测试正文", "chart_config": None, "raw_rows": [{"收入": 1}]})

        mock_summary.assert_called_once()
        joined = "\n".join(str(call.args[0]) for call in mock_markdown.call_args_list if call.args)
        self.assertIn('class="insight-card insight-shell"', joined)
        self.assertNotIn(">核心判断<", joined)

    def test_render_workspace_renders_summary_hero_before_insight_body(self):
        call_order: list[str] = []

        with patch.object(
            app,
            "_render_summary_hero",
            side_effect=lambda summary: call_order.append(f"summary:{summary['title']}"),
        ), patch.object(app.st, "markdown", side_effect=lambda *args, **kwargs: call_order.append("markdown")):
            app.render_workspace({"answer": "## 结论\n测试正文", "chart_config": None, "raw_rows": [{"收入": 1}]})

        self.assertGreaterEqual(len(call_order), 2)
        self.assertEqual(call_order[0], "summary:结果判断")
        self.assertEqual(call_order[1], "markdown")

    def test_render_workspace_hides_summary_status_when_mode_label_is_empty(self):
        with patch.object(app.st, "markdown") as mock_markdown:
            app.render_workspace({"answer": "## 结论\n测试正文", "chart_config": None, "raw_rows": [{"收入": 1}]})

        joined = "\n".join(str(call.args[0]) for call in mock_markdown.call_args_list if call.args)
        self.assertNotIn('class="summary-status"', joined)
        self.assertNotIn(">分析中<", joined)

    def test_render_header_uses_status_dot_instead_of_status_text(self):
        with patch.object(app.st, "markdown") as mock_markdown, patch.object(app.st, "button", return_value=False):
            app.render_header(db_error=None, latest_result=None)

        joined = "\n".join(str(call.args[0]) for call in mock_markdown.call_args_list if call.args)
        self.assertIn('class="status-dot is-online"', joined)
        self.assertNotIn(">在线<", joined)
        self.assertNotIn(">未在线<", joined)

    def test_render_header_offers_quick_preview_button(self):
        with patch.object(app.st, "markdown"), patch.object(
            app.st, "button", side_effect=[False]
        ) as mock_button, patch.object(app, "activate_quick_preview") as mock_preview:
            app.render_header(db_error=None, latest_result=None)

        mock_button.assert_any_call("清空会话", key="header_reset", type="secondary", use_container_width=False, width="content")
        mock_preview.assert_not_called()

    def test_render_input_bar_offers_quick_preview_in_input_area(self):
        with patch.object(app, "_render_example_cards"), patch.object(
            app.st, "button", return_value=False
        ) as mock_button, patch.object(app.st, "form_submit_button", return_value=False), patch.object(
            app.st, "text_input", return_value=""
        ), patch.object(app, "activate_quick_preview") as mock_preview:
            app.render_input_bar(schema="fake schema", db_error=None, latest_result=None)

        mock_button.assert_any_call("快速预览", key="input_preview", type="tertiary", use_container_width=False)
        mock_preview.assert_not_called()

    def test_render_workspace_renders_main_answer_inside_single_shell_with_markdown_preview(self):
        answer = "## 整体趋势\n- **工作日**更高\n- 周末回落"

        with patch.object(app.st, "markdown") as mock_markdown:
            app.render_workspace({"answer": answer, "chart_config": None, "raw_rows": [{"收入": 1}]})

        insight_calls = [
            call
            for call in mock_markdown.call_args_list
            if call.args and 'class="insight-card insight-shell"' in str(call.args[0])
        ]
        self.assertEqual(len(insight_calls), 1)
        rendered = str(insight_calls[0].args[0])
        self.assertIn("<h2>整体趋势</h2>", rendered)
        self.assertIn("<strong>工作日</strong>", rendered)
        self.assertIn("<ul>", rendered)

    def test_render_input_bar_places_suggested_questions_above_form_when_empty(self):
        with patch.object(app, "_render_example_cards") as mock_examples:
            app.render_input_bar(schema="fake schema", db_error=None, latest_result=None)

        mock_examples.assert_called_once()
        args = mock_examples.call_args.args
        self.assertEqual(args[1], "建议先问")
        self.assertEqual(mock_examples.call_args.kwargs["tone"], "suggested-questions")

    def test_render_input_bar_submits_question_to_handler(self):
        with patch.object(app, "_render_example_cards"), patch.object(app.st, "form_submit_button", return_value=True), patch.object(
            app.st, "text_input", return_value="为什么深圳收入下滑？"
        ), patch.object(app, "handle_question") as mock_handle:
            app.render_input_bar(schema="fake schema", db_error=None, latest_result=None)

        mock_handle.assert_called_once_with("fake schema", None, "为什么深圳收入下滑？")

    def test_render_app_places_conversation_before_workspace_after_result_exists(self):
        call_order: list[str] = []

        with patch.object(app, "st") as mock_st, patch.object(app, "inject_styles"), patch.object(
            app, "init_state"
        ), patch.object(app, "load_schema", return_value=("fake schema", None)), patch.object(
            app, "render_header", side_effect=lambda *args, **kwargs: call_order.append("header")
        ), patch.object(
            app, "render_input_bar", side_effect=lambda *args, **kwargs: call_order.append("input")
        ), patch.object(
            app, "render_conversation_panel", side_effect=lambda *args, **kwargs: call_order.append("conversation")
        ), patch.object(
            app, "render_workspace", side_effect=lambda *args, **kwargs: call_order.append("workspace")
        ):
            left_col = unittest.mock.MagicMock()
            right_col = unittest.mock.MagicMock()
            left_col.__enter__.return_value = left_col
            left_col.__exit__.return_value = None
            right_col.__enter__.return_value = right_col
            right_col.__exit__.return_value = None
            mock_st.columns.return_value = [left_col, right_col]
            mock_st.session_state.latest_result = {"answer": "## 结论\n收入上升", "chart_config": None, "raw_rows": [{"收入": 1}]}
            mock_st.session_state.messages = [{"role": "user", "content": "问题"}, {"role": "assistant", "content": "回答"}]
            app.render_app()

        self.assertEqual(call_order, ["header", "input", "conversation", "workspace"])

    def test_build_conversation_panel_turns_messages_into_thread(self):
        panel = app.build_conversation_panel(
            messages=[
                {"role": "user", "content": "2024 年哪个城市收入最高？"},
                {"role": "assistant", "content": "我先按城市汇总收入，再看最高值。"},
            ],
            latest_result={"answer": "## 结论\n上海最高", "chart_config": None, "raw_rows": [{"城市": "上海"}]},
        )

        self.assertEqual(panel["title"], "分析过程")
        self.assertEqual(panel["helper_text"], "")
        self.assertEqual(len(panel["items"]), 2)
        self.assertEqual(panel["items"][0]["role"], "user")
        self.assertEqual(panel["items"][1]["role"], "assistant")

    def test_calculate_table_height_keeps_table_compact(self):
        self.assertEqual(app.calculate_table_height(0), 180)
        self.assertEqual(app.calculate_table_height(3), 188)
        self.assertEqual(app.calculate_table_height(20), 496)

    def test_build_chart_layout_keeps_plot_compact(self):
        layout = app.build_chart_layout()

        self.assertEqual(layout["height"], 360)
        self.assertEqual(layout["margin"]["t"], 46)
        self.assertEqual(layout["margin"]["b"], 8)

    def test_build_conversation_thread_html_keeps_panel_and_thread_in_one_markup_block(self):
        html_block = app._build_conversation_thread_html(
            [
                {"role": "user", "label": "你", "content": "先看趋势"},
                {"role": "assistant", "label": "分析助手", "content": "我先按城市拆开。"},
            ]
        )

        self.assertIn('<p class="stream-headline">分析过程</p>', html_block)
        self.assertIn('<div class="conversation-panel process-shell"><div class="conversation-thread">', html_block)
        self.assertEqual(html_block.count('<div class="conversation-panel process-shell">'), 1)
        self.assertIn('thread-item user', html_block)
        self.assertIn('thread-item assistant', html_block)

    def test_build_conversation_panel_strips_code_blocks_from_assistant_thread_preview(self):
        panel = app.build_conversation_panel(
            messages=[
                {
                    "role": "assistant",
                    "content": "## 结论\n上海收入最高\n```sql\nSELECT city, revenue FROM orders;\n```",
                }
            ],
            latest_result={"answer": "## 结论\n上海收入最高", "chart_config": None, "raw_rows": [{"城市": "上海"}]},
        )

        self.assertEqual(len(panel["items"]), 1)
        self.assertNotIn("```", panel["items"][0]["content"])
        self.assertNotIn("SELECT city", panel["items"][0]["content"])
        self.assertIn("上海收入最高", panel["items"][0]["content"])

    def test_build_conversation_panel_strips_html_markup_from_assistant_thread_preview(self):
        panel = app.build_conversation_panel(
            messages=[
                {
                    "role": "assistant",
                    "content": (
                        '<div class="thread-item assistant">'
                        '<div class="thread-label">分析助手</div>'
                        '<div class="thread-content"><p>查询已完成，结果工作区展示了 14 行数据。</p></div>'
                        "</div>"
                    ),
                }
            ],
            latest_result={"answer": "", "chart_config": None, "raw_rows": [{"区域": "A"}]},
        )

        self.assertEqual(len(panel["items"]), 1)
        self.assertNotIn("<div", panel["items"][0]["content"])
        self.assertNotIn("thread-label", panel["items"][0]["content"])
        self.assertNotIn("分析助手", panel["items"][0]["content"])
        self.assertIn("查询已完成", panel["items"][0]["content"])

    def test_build_conversation_panel_strips_thread_template_markup_even_when_payload_is_tagged_as_user(self):
        panel = app.build_conversation_panel(
            messages=[
                {
                    "role": "user",
                    "content": (
                        '<div class="thread-item assistant">'
                        '<div class="thread-label">分析助手</div>'
                        '<div class="thread-content"><p>2023年第四季度，广东地区不同城市的收入占比差异如何？</p></div>'
                        "</div>"
                    ),
                }
            ],
            latest_result={"answer": "", "chart_config": None, "raw_rows": [{"区域": "A"}]},
        )

        self.assertEqual(len(panel["items"]), 1)
        self.assertNotIn("<div", panel["items"][0]["content"])
        self.assertNotIn("thread-item", panel["items"][0]["content"])
        self.assertIn("2023年第四季度", panel["items"][0]["content"])

    def test_build_thread_preview_strips_escaped_html_template_from_any_role(self):
        preview = app.build_thread_preview(
            "user",
            '&lt;div class="result-shell"&gt;&lt;p&gt;本轮分析结果&lt;/p&gt;&lt;p&gt;收入最高的是上海&lt;/p&gt;&lt;/div&gt;',
        )

        self.assertNotIn("&lt;div", preview)
        self.assertNotIn("<div", preview)
        self.assertNotIn('class="result-shell"', preview)
        self.assertIn("收入最高的是上海", preview)


if __name__ == "__main__":
    unittest.main()
