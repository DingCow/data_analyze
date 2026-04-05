"""
main.py —— 主入口
用法：python3 main.py

交互流程：
  1. 启动时加载数据库 schema
  2. 用户输入问题
  3. Router Agent 判断意图，分发给 SQL Agent 或 Analysis Agent
  4. 展示最终回答
  输入 'exit' 或 Ctrl+C 退出
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from src import db
from src.workflow import router

console = Console()


def render_result(answer: str, raw_rows: list[dict]) -> None:
    """
    CLI 展示结果。
    complex 路径优先展示分析文字；simple 路径没有文字时，回退展示表格数据。
    """
    if answer:
        console.print(Panel(answer, title="[bold cyan]分析结果[/bold cyan]", border_style="cyan"))
        return

    if not raw_rows:
        console.print(Panel("未查询到结果", title="[bold cyan]分析结果[/bold cyan]", border_style="cyan"))
        return

    table = Table(title="查询结果", box=box.ROUNDED)
    columns = list(raw_rows[0].keys())
    for column in columns:
        table.add_column(str(column))

    for row in raw_rows:
        table.add_row(*[str(row.get(column, "")) if row.get(column) is not None else "" for column in columns])

    console.print(table)


def main():
    console.print(Panel(
        "[bold cyan]Data Analyze Agent[/bold cyan]\n"
        "[dim]用自然语言提问，自动查询数据库并给出分析[/dim]\n"
        "[dim]输入 exit 退出[/dim]",
        box=box.ROUNDED
    ))

    # 启动时加载一次 schema，避免每次提问都查数据库
    console.print("[dim]正在加载数据库结构...[/dim]", end=" ")
    schema = db.get_schema()
    console.print("[green]完成[/green]")

    # 多轮对话历史
    history = []

    while True:
        try:
            question = console.input("\n[bold green]你的问题>[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见！[/dim]")
            break

        if not question:
            continue

        if question.lower() == "exit":
            console.print("[dim]再见！[/dim]")
            break

        # 交给 Router Agent 处理，它会决定调用哪些子 Agent
        # router.run 返回 (文字回答, 图表配置, 原始数据行)，CLI 只展示文字
        try:
            answer, _, raw_rows = router.run(schema, question, history)
        except Exception as e:
            console.print(f"[red]出错：{e}[/red]")
            continue

        # 展示最终回答
        render_result(answer, raw_rows)

        # 更新对话历史，保留最近 10 轮
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 20:
            history = history[-20:]


if __name__ == "__main__":
    main()
