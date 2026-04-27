import unittest
from unittest.mock import patch

from src.agent_runtime import LegacyWorkflowRunner, get_runner
from src.agent_runtime.runners import LangGraphWorkflowRunner


class TestAgentRuntime(unittest.TestCase):
    """验证新运行时边界不会改变 legacy 工作流契约。"""

    def test_get_runner_returns_legacy_runner(self):
        runner = get_runner("legacy")

        self.assertIsInstance(runner, LegacyWorkflowRunner)
        self.assertEqual(runner.name, "legacy")

    def test_get_runner_returns_langgraph_runner(self):
        runner = get_runner("langgraph")

        self.assertIsInstance(runner, LangGraphWorkflowRunner)
        self.assertEqual(runner.name, "langgraph")

    @patch("src.agent_runtime.runners.router.run")
    def test_legacy_runner_wraps_router_result(self, mock_router_run):
        mock_router_run.return_value = (
            "## 结论\n收入上升",
            {"type": "line", "x": "月份", "y": ["收入"], "title": "收入趋势"},
            [{"月份": "2024-01", "收入": 100}],
        )

        result = LegacyWorkflowRunner().run("fake schema", "分析收入趋势", [])

        self.assertEqual(result.answer, "## 结论\n收入上升")
        self.assertEqual(result.chart_config["type"], "line")
        self.assertEqual(result.raw_rows, [{"月份": "2024-01", "收入": 100}])
        self.assertEqual(result.trace, ["legacy.router"])
        self.assertIsNone(result.error)

    @patch("src.agent_runtime.runners.router.run")
    def test_legacy_runner_converts_exception_to_result_error(self, mock_router_run):
        mock_router_run.side_effect = RuntimeError("数据库不可读")

        result = LegacyWorkflowRunner().run("fake schema", "查数据", [])

        self.assertEqual(result.answer, "")
        self.assertIsNone(result.chart_config)
        self.assertEqual(result.raw_rows, [])
        self.assertEqual(result.trace, ["legacy.router"])
        self.assertEqual(result.error, "数据库不可读")


class TestLangGraphRunner(unittest.TestCase):
    """验证 LangGraph 版 router 编排和 legacy 路径等价。"""

    @patch("src.agent_runtime.nodes.sql.run")
    @patch("src.agent_runtime.nodes.router.classify")
    def test_langgraph_runner_uses_simple_sql_path(self, mock_classify, mock_sql_run):
        mock_classify.return_value = "simple"
        mock_sql_run.return_value = [{"value": 1}]

        result = LangGraphWorkflowRunner().run("fake schema", "查一条数据", [])

        self.assertEqual(result.intent, "simple")
        self.assertEqual(result.answer, "")
        self.assertIsNone(result.chart_config)
        self.assertEqual(result.raw_rows, [{"value": 1}])
        self.assertEqual(result.trace, ["classify", "simple_sql", "finalize"])
        mock_sql_run.assert_called_once_with("fake schema", "查一条数据", [])

    @patch("src.agent_runtime.nodes.report.run")
    @patch("src.agent_runtime.nodes.analysis.analyze")
    @patch("src.agent_runtime.nodes.sql.run")
    @patch("src.agent_runtime.nodes.analysis.decompose")
    @patch("src.agent_runtime.nodes.router.classify")
    def test_langgraph_runner_uses_complex_pipeline(
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

        result = LangGraphWorkflowRunner().run("fake schema", "分析收入趋势", [])

        self.assertEqual(result.intent, "complex")
        self.assertEqual(result.answer, "## 结论\n收入整体上升")
        self.assertEqual(result.chart_config["type"], "line")
        self.assertEqual(result.raw_rows, [{"月份": "2024-01", "收入": 100}])
        self.assertEqual(
            result.trace,
            ["classify", "decompose", "complex_sql", "analyze", "report", "finalize"],
        )
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
