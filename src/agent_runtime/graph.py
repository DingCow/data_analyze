"""LangGraph 版 router 编排。"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agent_runtime.nodes import (
    analyze_node,
    classify_node,
    complex_sql_node,
    decompose_node,
    finalize_node,
    report_node,
    route_by_intent,
    simple_sql_node,
)
from src.agent_runtime.state import AgentGraphState, WorkflowResult


def build_router_graph():
    """把原 router.run 的 if/else 流程表达成状态图。"""
    builder = StateGraph(AgentGraphState)

    builder.add_node("classify", classify_node)
    builder.add_node("simple_sql", simple_sql_node)
    builder.add_node("decompose", decompose_node)
    builder.add_node("complex_sql", complex_sql_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("report", report_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "simple": "simple_sql",
            "complex": "decompose",
        },
    )
    builder.add_edge("simple_sql", "finalize")
    builder.add_edge("decompose", "complex_sql")
    builder.add_edge("complex_sql", "analyze")
    builder.add_edge("analyze", "report")
    builder.add_edge("report", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


def run_router_graph(schema: str, question: str, history: list[dict]) -> WorkflowResult:
    """运行 LangGraph router，并转换成统一 WorkflowResult。"""
    graph = build_router_graph()
    final_state = graph.invoke(
        {
            "schema": schema,
            "question": question,
            "history": history,
            "trace": [],
        }
    )

    return WorkflowResult(
        answer=final_state.get("answer", ""),
        chart_config=final_state.get("chart_config"),
        raw_rows=final_state.get("raw_rows", []),
        intent=final_state.get("intent"),
        trace=final_state.get("trace", []),
    )
