"""
src/workflow/sql.py —— SQL Agent
职责：
  专职负责数据查询。接收用户问题，自主决定执行哪些 SQL，
  把查到的原始数据整理后返回。不做分析，只取数。
  始终使用 deepseek-chat（速度快，查数不需要推理能力）。
"""

import json
from src.llm import client, TOOLS, execute_tool_with_data, debug

# SQL Agent 的系统提示词
SYSTEM_PROMPT_TEMPLATE = """你是一个专业的数据查询助手，负责从新能源充电桩与停车场运营数据库中取数。

数据库结构如下：
{schema}

你的工作方式：
- 根据用户问题，调用 run_sql 工具执行 SQL 查询
- 复杂问题可以多次调用 run_sql，分步骤取数
- SQL 执行出错时，修改后重试
- 所有数据查询完毕后，直接回复"查询完成"即可，不需要做任何整理、分析或解读

注意：
- 数据库类型是 SQLite，日期格式为 'YYYY-MM-DD HH:MM:SS'
- 金额单位为"元"，电量单位为"kW·h"
- 数据量大的表（如 orders_all 约318万行），查询时加 WHERE 条件或 LIMIT
- 如果任务涉及多张表，必须用 JOIN 合并成一条 SQL 返回，不要分开查再各自返回
- 探索性查询（如查字段取值、确认表结构）只是中间步骤，最终结果必须是一张包含所有字段的宽表
"""


def run(schema: str, question: str, history: list[dict]) -> list[dict]:
    """
    SQL Agent 主函数：执行查询，只返回结构化原始数据。

    参数：
      schema   - 数据库结构
      question - 用户问题（或 Analysis.decompose 拆解后的子任务描述）
      history  - 多轮对话历史

    返回：
      原始数据行列表，每项是 {列名: 值} 的字典。
      不包含任何文字摘要，分析工作交给 Analysis Agent。
    """
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)

    # 构造消息列表
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    # 只保留最后一次查询的原始数据行。
    # 注意：如果最终一次查询结果为空，也要保留这个“空结果”，
    # 不能把更早的中间查询结果误当成最终结果返回。
    last_raw_rows = []

    # 工具调用循环，最多30次
    for i in range(30):
        debug(f"[SQL Agent] 第 {i+1} 轮")

        response = client.chat.completions.create(
            model="deepseek-chat",   # 查数固定用 chat，快且够用
            messages=messages,
            tools=TOOLS,
            temperature=0,
            max_tokens=2048,
        )

        choice = response.choices[0]

        # 模型要调用工具
        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                # 参数是 JSON 字符串，解析成字典
                tool_args = json.loads(tool_call.function.arguments)
                # execute_tool_with_data 同时返回文字结果（给模型）和原始数据行（给画图）
                text_result, raw_rows = execute_tool_with_data(tool_name, tool_args)

                # 每次工具查询都覆盖最后结果。
                # 这样最终查询即使返回空，也不会沿用更早的中间表。
                last_raw_rows = raw_rows

                # 把文字结果返回给模型继续对话
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": text_result,
                })

        # 模型完成，丢弃模型的文字输出，只返回最后一次查询的原始数据行
        elif choice.finish_reason == "stop":
            return last_raw_rows

        else:
            return []

    return []
