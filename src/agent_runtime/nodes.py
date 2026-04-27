"""LangGraph 节点函数。

这一层只负责把现有 workflow 的步骤包装成 graph node，暂时不改任何
SQL / Analysis / Report 内部逻辑。
"""

from __future__ import annotations

from typing import Literal

from src.agent_runtime.state import AgentGraphState
from src.workflow import analysis, report, router, sql


def _append_trace(state: AgentGraphState, node_name: str) -> list[str]:
    """记录图执行路径，方便后续对比 legacy 和 langgraph。"""
    return [*state.get("trace", []), node_name]


def classify_node(state: AgentGraphState) -> AgentGraphState:
    """对应 router.run 的第一步：判断 simple / complex。"""
    intent = router.classify(state["question"])
    return {
        "intent": intent,
        "trace": _append_trace(state, "classify"),
    }


def route_by_intent(state: AgentGraphState) -> Literal["simple", "complex"]:
    """根据分类结果决定下一条边。"""
    return "complex" if state.get("intent") == "complex" else "simple"


def simple_sql_node(state: AgentGraphState) -> AgentGraphState:
    """simple 路径：只查数，不生成报告。"""
    raw_rows = sql.run(state["schema"], state["question"], state.get("history", []))
    return {
        "answer": "",
        "chart_config": None,
        "raw_rows": raw_rows,
        "trace": _append_trace(state, "simple_sql"),
    }


def decompose_node(state: AgentGraphState) -> AgentGraphState:
    """complex 路径第一步：把业务问题拆成查询任务。"""
    subtasks = analysis.decompose(state["schema"], state["question"])
    return {
        "subtasks": subtasks,
        "trace": _append_trace(state, "decompose"),
    }


def complex_sql_node(state: AgentGraphState) -> AgentGraphState:
    """complex 路径第二步：按拆解结果查询数据。"""
    guided_question = f"用户原始问题：{state['question']}\n\n需要查询的内容：\n{state['subtasks']}"
    raw_rows = sql.run(state["schema"], guided_question, state.get("history", []))
    return {
        "raw_rows": raw_rows,
        "trace": _append_trace(state, "complex_sql"),
    }


def analyze_node(state: AgentGraphState) -> AgentGraphState:
    """complex 路径第三步：基于查询结果做分析。"""
    conclusion, raw_rows = analysis.analyze(state["question"], state.get("raw_rows", []))
    return {
        "analysis_text": conclusion,
        "raw_rows": raw_rows,
        "trace": _append_trace(state, "analyze"),
    }


def report_node(state: AgentGraphState) -> AgentGraphState:
    """complex 路径第四步：生成 Markdown 报告和图表配置。"""
    markdown, chart_config = report.run(
        state["question"],
        state.get("analysis_text", ""),
        state.get("raw_rows", []),
    )
    return {
        "answer": markdown,
        "chart_config": chart_config,
        "trace": _append_trace(state, "report"),
    }


def finalize_node(state: AgentGraphState) -> AgentGraphState:
    """统一收口节点，后续可以在这里补错误收敛或结果标准化。"""
    return {
        "trace": _append_trace(state, "finalize"),
    }
