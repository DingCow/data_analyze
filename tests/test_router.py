import unittest
from unittest.mock import patch

import main
from rich.table import Table
from src import llm
from src.workflow import analysis
from src.workflow import report
from src.workflow import router
from src.workflow import sql


class TestRouter(unittest.TestCase):
    """验证路由编排是否按预期调用各 Agent。"""

    @patch("src.workflow.router.sql.run")
    @patch("src.workflow.router.classify")
    def test_simple_question_uses_sql_path_only(self, mock_classify, mock_sql_run):
        mock_classify.return_value = "simple"
        mock_sql_run.return_value = [{"value": 1}]

        answer, chart_config, raw_rows = router.run("fake schema", "查一条数据", [])

        self.assertEqual(answer, "")
        self.assertIsNone(chart_config)
        self.assertEqual(raw_rows, [{"value": 1}])
        mock_sql_run.assert_called_once_with("fake schema", "查一条数据", [])

    @patch("src.workflow.router.report.run")
    @patch("src.workflow.router.analysis.analyze")
    @patch("src.workflow.router.sql.run")
    @patch("src.workflow.router.analysis.decompose")
    @patch("src.workflow.router.classify")
    def test_complex_question_uses_full_pipeline(
        self,
        mock_classify,
        mock_decompose,
        mock_sql_run,
        mock_analyze,
        mock_report_run,
    ):
        mock_classify.return_value = "complex"
        mock_decompose.return_value = "最终查询目标：按月汇总收入"
        mock_sql_run.return_value = [{"月份": "2024-01", "收入": 100}]
        mock_analyze.return_value = ("收入整体上升", [{"月份": "2024-01", "收入": 100}])
        mock_report_run.return_value = (
            "## 结论\n收入整体上升",
            {"type": "line", "x": "月份", "y": ["收入"], "title": "收入趋势"},
        )

        answer, chart_config, raw_rows = router.run("fake schema", "分析收入趋势", [])

        self.assertEqual(answer, "## 结论\n收入整体上升")
        self.assertEqual(chart_config["type"], "line")
        self.assertEqual(raw_rows, [{"月份": "2024-01", "收入": 100}])
        mock_decompose.assert_called_once_with("fake schema", "分析收入趋势")
        mock_sql_run.assert_called_once()
        mock_analyze.assert_called_once_with("分析收入趋势", [{"月份": "2024-01", "收入": 100}])
        mock_report_run.assert_called_once_with(
            "分析收入趋势",
            "收入整体上升",
            [{"月份": "2024-01", "收入": 100}],
        )


if __name__ == "__main__":
    unittest.main()


class TestCliRendering(unittest.TestCase):
    """验证 CLI 在 simple 路径下也会展示查询结果。"""

    def test_render_result_falls_back_to_raw_rows_when_answer_is_empty(self):
        with patch.object(main.console, "print") as mock_print:
            main.render_result("", [{"value": 1}, {"value": 2}])

        self.assertEqual(mock_print.call_count, 1)
        self.assertIsInstance(mock_print.call_args.args[0], Table)


class TestSqlAgent(unittest.TestCase):
    """验证 SQL Agent 不会把旧中间结果误当成最终结果。"""

    @patch("src.workflow.sql.execute_tool_with_data")
    @patch("src.workflow.sql.client.chat.completions.create")
    def test_run_returns_empty_when_final_query_result_is_empty(
        self,
        mock_create,
        mock_execute_tool,
    ):
        class FakeToolFunction:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments

        class FakeToolCall:
            def __init__(self, call_id, name, arguments):
                self.id = call_id
                self.function = FakeToolFunction(name, arguments)

        class FakeMessage:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls or []

        class FakeChoice:
            def __init__(self, finish_reason, message):
                self.finish_reason = finish_reason
                self.message = message

        class FakeResponse:
            def __init__(self, choice):
                self.choices = [choice]

        mock_create.side_effect = [
            FakeResponse(
                FakeChoice(
                    "tool_calls",
                    FakeMessage(
                        tool_calls=[FakeToolCall("call_1", "run_sql", '{"sql":"SELECT 1"}')]
                    ),
                )
            ),
            FakeResponse(
                FakeChoice(
                    "tool_calls",
                    FakeMessage(
                        tool_calls=[FakeToolCall("call_2", "run_sql", '{"sql":"SELECT 2"}')]
                    ),
                )
            ),
            FakeResponse(FakeChoice("stop", FakeMessage(content="查询完成"))),
        ]

        mock_execute_tool.side_effect = [
            ("中间查询结果", [{"value": 1}]),
            ("查询结果为空（0行）", []),
        ]

        result = sql.run("fake schema", "测试问题", [])

        self.assertEqual(result, [])
        self.assertEqual(mock_create.call_args_list[0].kwargs["model"], llm.FAST_MODEL)
        self.assertEqual(mock_create.call_args_list[0].kwargs["extra_body"], llm.NON_THINKING_EXTRA_BODY)


class TestModelConfiguration(unittest.TestCase):
    """验证各 Agent 已切换到 DeepSeek 新模型配置。"""

    @patch("src.workflow.router.client.chat.completions.create")
    def test_router_uses_fast_model_without_thinking(self, mock_create):
        class FakeMessage:
            content = "simple"

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        mock_create.return_value = FakeResponse()

        self.assertEqual(router.classify("查一下订单数"), "simple")
        self.assertEqual(mock_create.call_args.kwargs["model"], llm.FAST_MODEL)
        self.assertEqual(mock_create.call_args.kwargs["extra_body"], llm.NON_THINKING_EXTRA_BODY)

    @patch("src.workflow.analysis.client.chat.completions.create")
    def test_analysis_uses_reasoning_model_with_thinking(self, mock_create):
        class FakeMessage:
            content = "最终查询目标：按城市汇总收入"

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        mock_create.return_value = FakeResponse()

        result = analysis.decompose("fake schema", "分析收入变化")

        self.assertIn("最终查询目标", result)
        self.assertEqual(mock_create.call_args.kwargs["model"], llm.REASONING_MODEL)
        self.assertEqual(mock_create.call_args.kwargs["extra_body"], llm.THINKING_EXTRA_BODY)
        self.assertEqual(mock_create.call_args.kwargs["reasoning_effort"], llm.THINKING_REASONING_EFFORT)
        self.assertNotIn("temperature", mock_create.call_args.kwargs)

    @patch("src.workflow.report.client.chat.completions.create")
    def test_report_uses_fast_model_without_thinking(self, mock_create):
        class FakeMessage:
            content = '{"markdown":"## 结论\\n收入下降","chart":null}'

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        mock_create.return_value = FakeResponse()

        markdown, chart_config = report.run("分析收入", "收入下降", [{"城市": "中山", "收入": 100}])

        self.assertIn("收入下降", markdown)
        self.assertIsNone(chart_config)
        self.assertEqual(mock_create.call_args.kwargs["model"], llm.FAST_MODEL)
        self.assertEqual(mock_create.call_args.kwargs["extra_body"], llm.NON_THINKING_EXTRA_BODY)


class TestWebUiHelpers(unittest.TestCase):
    """验证新版页面模型的 Web UI 辅助结构。"""

    def test_build_layout_config_keeps_header_compact_and_workspace_primary(self):
        import app

        layout = app.build_layout_config()

        self.assertGreaterEqual(layout["header_columns"][1], 0.16)
        self.assertEqual(layout["content_mode"], "waterfall")
        self.assertLessEqual(layout["content_max_width_px"], 1080)
        self.assertGreater(layout["content_section_gap_rem"], 0.6)
        self.assertEqual(layout["workspace_density"], "compact")
        self.assertLess(layout["workspace_title_size_rem"], 1.3)
        self.assertLess(layout["summary_title_size_rem"], 1.0)
        self.assertLess(layout["summary_hero_padding_rem"], 0.7)
        self.assertLess(layout["metric_value_size_rem"], 0.85)
        self.assertEqual(layout["header_gap"], "small")
        self.assertGreater(layout["header_action_offset_rem"], 0)
        self.assertLessEqual(layout["input_columns"][0], 0.8)
        self.assertGreaterEqual(layout["input_columns"][1], 0.2)

    def test_build_header_model_uses_workspace_identity_and_online_status(self):
        import app

        header = app.build_header_model(
            db_error=None,
            latest_result={
                "answer": "",
                "chart_config": None,
                "raw_rows": [{"value": 1}],
            },
        )

        self.assertEqual(header["title"], "Data Analyze Agent")
        self.assertEqual(header["status_label"], "数据源状态")
        self.assertEqual(header["status_value"], "在线")
        self.assertIn("直接获得核心判断", header["subtitle"])
        self.assertEqual(header["status_detail"], "")

    def test_build_header_model_switches_to_error_state_when_db_unavailable(self):
        import app

        header = app.build_header_model(
            db_error="sqlite unavailable",
            latest_result=None,
        )

        self.assertEqual(header["status_label"], "数据源状态")
        self.assertEqual(header["status_value"], "未在线")
        self.assertEqual(header["status_detail"], "")

    def test_build_input_model_encourages_follow_up_when_result_exists(self):
        import app

        model = app.build_input_model(
            db_error=None,
            latest_result={
                "answer": "## 结论\n收入上升",
                "chart_config": None,
                "raw_rows": [{"收入": 100}],
            },
        )

        self.assertEqual(model["button_label"], "继续生成结论")
        self.assertEqual(model["copy"], "")
        self.assertEqual(model["hint"], "")
        self.assertEqual(
            set(model.keys()),
            {"title", "copy", "placeholder", "button_label", "hint", "disabled", "status_label"},
        )

    def test_build_input_model_uses_clear_start_language_for_empty_state(self):
        import app

        model = app.build_input_model(
            db_error=None,
            latest_result=None,
        )

        self.assertEqual(model["title"], "从一个业务判断开始")
        self.assertEqual(model["copy"], "")
        self.assertEqual(model["hint"], "")
        self.assertEqual(model["button_label"], "生成分析结论")

    def test_build_input_model_returns_disabled_error_state_when_db_unavailable(self):
        import app

        model = app.build_input_model(
            db_error="sqlite unavailable",
            latest_result=None,
        )

        self.assertTrue(model["disabled"])
        self.assertEqual(model["status_label"], "数据库异常")
        self.assertEqual(model["button_label"], "数据库不可用")
        self.assertEqual(
            set(model.keys()),
            {"title", "copy", "placeholder", "button_label", "hint", "disabled", "status_label"},
        )

    def test_build_result_panel_returns_analysis_mode_when_answer_exists(self):
        import app

        panel = app.build_result_panel(
            answer="## 结论\n收入上升",
            chart_config={"type": "line", "x": "月份", "y": ["收入"], "title": "趋势"},
            raw_rows=[{"月份": "2024-01", "收入": 100}],
        )

        self.assertEqual(panel["mode"], "analysis")
        self.assertEqual(panel["title"], "本轮分析结果")
        self.assertTrue(panel["has_chart"])
        self.assertEqual(panel["row_count"], 1)

    def test_build_result_panel_returns_table_mode_for_simple_query(self):
        import app

        panel = app.build_result_panel(
            answer="",
            chart_config=None,
            raw_rows=[{"value": 1}],
        )

        self.assertEqual(panel["mode"], "table")
        self.assertEqual(panel["title"], "已拿到关键数据")
        self.assertEqual(panel["row_count"], 1)

    def test_build_result_panel_treats_chart_config_without_rows_as_non_chart(self):
        import app

        panel = app.build_result_panel(
            answer="## 结论\n收入上升",
            chart_config={"type": "line"},
            raw_rows=[],
        )

        self.assertEqual(panel["mode"], "analysis")
        self.assertFalse(panel["has_chart"])

    def test_build_conversation_panel_keeps_message_thread_order(self):
        import app

        messages = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "结果1"},
            {"role": "user", "content": "问题2"},
            {"role": "assistant", "content": "结果2"},
        ]

        panel = app.build_conversation_panel(
            messages,
            {"answer": "最终结果", "chart_config": {"type": "line"}, "raw_rows": [{"value": 1}]},
        )

        self.assertEqual(panel["title"], "分析过程")
        self.assertIn("保留本轮分析过程", panel["helper_text"])
        self.assertEqual(panel["examples_title"], "建议先问")
        self.assertEqual(len(panel["items"]), 4)
        self.assertEqual(panel["items"][0]["role"], "user")
        self.assertEqual(panel["items"][1]["role"], "assistant")
        self.assertEqual(panel["items"][2]["content"], "问题2")
        self.assertEqual(panel["items"][3]["content"], "结果2")
        self.assertEqual(set(panel["items"][0].keys()), {"role", "label", "content"})

    def test_build_conversation_panel_returns_empty_shell_before_any_question(self):
        import app

        panel = app.build_conversation_panel([], None)

        self.assertEqual(panel["title"], "")
        self.assertEqual(panel["helper_text"], "")
        self.assertEqual(panel["examples_title"], "")
        self.assertEqual(panel["examples"], [])
        self.assertEqual(panel["items"], [])

    def test_build_workspace_sections_returns_analysis_sections_for_complex_result(self):
        import app

        workspace = app.build_workspace_sections(
            {
                "answer": "## 结论\n收入上升",
                "chart_config": {"type": "line"},
                "raw_rows": [{"收入": 100}],
            }
        )

        self.assertEqual(workspace["mode"], "analysis")
        self.assertEqual(workspace["summary"]["mode_label"], "分析中")
        self.assertIn("description", workspace["summary"])
        self.assertGreaterEqual(len(workspace["follow_ups"]), 2)
        self.assertTrue(workspace["sections"]["show_insight"])
        self.assertTrue(workspace["sections"]["show_chart"])
        self.assertTrue(workspace["sections"]["show_table"])
        self.assertEqual(workspace["summary"]["metric_items"][0]["label"], "结果结构")
        self.assertEqual(workspace["summary"]["metric_items"][0]["value"], "核心判断")

    def test_build_workspace_sections_describes_row_count_for_table_result(self):
        import app

        workspace = app.build_workspace_sections(
            {
                "answer": "",
                "chart_config": None,
                "raw_rows": [{"value": 1}, {"value": 2}],
            }
        )

        self.assertEqual(workspace["mode"], "table")
        self.assertIn("2 行", workspace["summary"]["description"])
        self.assertEqual(workspace["summary"]["mode_label"], "已返回数据")
        self.assertTrue(workspace["sections"]["show_table"])
        self.assertFalse(workspace["sections"]["show_insight"])

    def test_build_workspace_sections_returns_idle_empty_state_without_result(self):
        import app

        workspace = app.build_workspace_sections(None)

        self.assertEqual(workspace["mode"], "empty")
        self.assertEqual(workspace["summary"]["mode_label"], "示例预览")
        self.assertEqual(workspace["summary"]["title"], "你将得到什么")
        self.assertEqual(workspace["summary"]["metric_items"], [])
        self.assertEqual(workspace["summary"]["description"], "")
        self.assertEqual(workspace["empty_hint"], "")
        self.assertEqual(workspace["follow_ups"], [])
        self.assertEqual(len(workspace["preview_items"]), 3)
