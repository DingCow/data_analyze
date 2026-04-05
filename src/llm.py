"""
llm.py —— 公共基础层
职责：
  1. 初始化 DeepSeek API 客户端（所有 Agent 共用）
  2. 定义 run_sql 工具规格（工具说明书）
  3. 实际执行 run_sql 工具（调用 db.py）
  这里只放"基础设施"，不包含任何 Agent 逻辑。
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from src import db

# 从 .env 文件读取配置
load_dotenv()

# DEBUG 模式：在 .env 里加 DEBUG=true 即可开启调试日志
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# 初始化 DeepSeek 客户端，所有 Agent 都从这里 import 使用
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# run_sql 工具的规格定义，传给模型让它知道有这个工具可以调用
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "执行一条只读 SQLite SQL 查询语句，返回查询结果。如果 SQL 有语法错误会返回错误信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "要执行的 SQL 查询语句"
                    }
                },
                "required": ["sql"]
            }
        }
    }
]


def debug(msg: str):
    """只在 DEBUG=true 时打印日志，不影响正常使用"""
    if DEBUG:
        print(f"  [debug] {msg}")


def execute_tool(tool_name: str, tool_args: dict) -> str:
    """
    实际执行模型请求的工具，返回字符串结果给模型。
    只返回文字，供模型继续对话用。
    """
    # 调用带原始数据的版本，只取文字部分返回
    text_result, _ = execute_tool_with_data(tool_name, tool_args)
    return text_result


def execute_tool_with_data(tool_name: str, tool_args: dict) -> tuple[str, list[dict]]:
    """
    执行工具，同时返回文字结果（给模型）和原始数据行（给画图）。
    """
    if tool_name == "run_sql":
        sql = tool_args["sql"]
        # 打印正在执行的 SQL，让用户知道 Agent 在做什么
        print(f"  → 执行 SQL: {sql[:80]}{'...' if len(sql) > 80 else ''}")
        try:
            columns, rows = db.run_query(sql)

            if not rows:
                return "查询结果为空（0行）", []

            # 把结果格式化成文字表格，方便模型阅读和分析
            header = " | ".join(columns)
            separator = "-" * len(header)
            data_lines = [
                " | ".join(str(v) if v is not None else "" for v in row)
                for row in rows
            ]
            text_result = f"{header}\n{separator}\n" + "\n".join(data_lines)
            text_result += f"\n\n共 {len(rows)} 行{'（已截断至500行）' if len(rows) == 500 else ''}"

            # 把每行数据转成 {列名: 值} 的字典，方便后续画图
            raw_rows = [dict(zip(columns, row)) for row in rows]

            return text_result, raw_rows

        except Exception as e:
            # 把错误信息返回给模型，让它分析原因并修正 SQL
            return f"SQL执行出错：{e}", []

    return f"未知工具：{tool_name}", []
