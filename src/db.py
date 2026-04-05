"""
db.py —— SQLite 数据库工具
职责：
  1. 连接数据库
  2. 提取所有表的结构（schema），用于给 LLM 做上下文
  3. 执行 SQL 查询，返回结果
"""

import csv
import io
import re
import sqlite3
import subprocess

# 数据库路径固定，不得更改
DB_PATH = "/Users/owenlau/SqliteDB.db"


def _is_db_open_error(exc: Exception) -> bool:
    """判断是否为当前环境下常见的数据库文件打开失败。"""
    return isinstance(exc, sqlite3.OperationalError) and "unable to open database file" in str(exc)


def _coerce_cli_value(value: str) -> object:
    """把 sqlite3 CLI 的文本结果尽量还原成基础 Python 类型。"""
    if value == "":
        return ""
    lowered = value.lower()
    if lowered == "null":
        return None
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _run_sqlite_cli(sql: str) -> tuple[list[str], list[tuple]]:
    """使用 sqlite3 CLI 执行只读查询，作为 Python sqlite 失败时的回退。"""
    result = subprocess.run(
        ["sqlite3", "-readonly", "-header", "-csv", DB_PATH, sql],
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if not output:
        return [], []

    reader = csv.reader(io.StringIO(output))
    rows = list(reader)
    if not rows:
        return [], []

    columns = rows[0]
    data = [tuple(_coerce_cli_value(cell) for cell in row) for row in rows[1:]]
    return columns, data


def get_connection():
    """创建并返回 SQLite 只读连接，从底层阻止写入操作。"""
    # mode=ro 相当于只给 Agent 一个"只读账号"，即使误生成写 SQL 也无法落库
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row  # 让查询结果可以按列名访问
    return conn


# 各表的业务说明，帮助 LLM 选择正确的表
# 如果新增了表，在这里补充说明即可
TABLE_DESCRIPTIONS = {
    "orders_all":           "充电订单主表（2021.10-2024.07，约318万行），包含充电时间、电站、订单金额、电量等事实字段；不直接包含省份/城市字段，涉及省份、城市、区域时需通过电站名称或车场编号关联 taizhang",
    "taizhang":             "充电站台账（静态数据），包含电站名称、地址、省份、城市、桩数、分润比例等维度字段，不含时间序列；地区类问题优先与 orders_all 做关联",
    "fees_24":              "2024年费用结算明细，包含电站收费、分润金额等财务数据",
    "users_info":           "用户信息表，包含用户注册时间、城市、充电次数等",
    "parking_stations_all": "停车场信息表（静态数据），包含停车场名称、地址、车位数等",
    "parking_taizhang":     "停车场运营台账（静态数据），包含停车场运营商、分润比例等",
}


def get_schema() -> str:
    """
    提取所有表的结构，返回带业务说明的字符串，直接发给 LLM 作为数据库上下文。
    格式示例：
      orders_all [充电订单主表，分析趋势首选]: 充电订单号(TEXT), 电站名称(TEXT), ...
      taizhang [静态台账，不含时间序列]: 电站名称(TEXT), ...
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        schema_lines = []
        for table in tables:
            # 获取每张表的列信息
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = cursor.fetchall()
            col_str = ", ".join(f"{col[1]}({col[2]})" for col in columns)
            desc = TABLE_DESCRIPTIONS.get(table, "")
            prefix = f"{table} [{desc}]" if desc else table
            schema_lines.append(f"{prefix}: {col_str}")

        conn.close()
        schema_lines.append(
            "查询提示: orders_all 是事实表，taizhang 是充电站维表。凡是涉及省份、城市、区域、TopN城市等地理维度问题，优先考虑 orders_all JOIN taizhang。"
        )

        return "\n".join(schema_lines)
    except Exception as exc:
        if not _is_db_open_error(exc):
            raise

    _, table_rows = _run_sqlite_cli("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    schema_lines = []
    for row in table_rows:
        table = str(row[0])
        _, pragma_rows = _run_sqlite_cli(f"PRAGMA table_info('{table}')")
        col_str = ", ".join(f"{col[1]}({col[2]})" for col in pragma_rows)
        desc = TABLE_DESCRIPTIONS.get(table, "")
        prefix = f"{table} [{desc}]" if desc else table
        schema_lines.append(f"{prefix}: {col_str}")
    schema_lines.append(
        "查询提示: orders_all 是事实表，taizhang 是充电站维表。凡是涉及省份、城市、区域、TopN城市等地理维度问题，优先考虑 orders_all JOIN taizhang。"
    )
    return "\n".join(schema_lines)


def validate_readonly_sql(sql: str) -> None:
    """
    校验 SQL 是否为只读查询。
    这里先在代码层做门禁，尽量把危险语句拦在真正执行之前。
    """
    normalized = sql.strip()
    if not normalized:
        raise ValueError("SQL 不能为空")

    # 只允许单条语句，避免把查询和写操作拼在一起执行
    stripped = normalized.rstrip()
    if ";" in stripped.rstrip(";"):
        raise ValueError("只允许执行单条 SQL 查询")

    lowered = normalized.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("只允许执行只读查询（SELECT / WITH）")

    # 拒绝明显的写操作和高风险语句，避免模型误生成破坏性 SQL
    banned_keywords = (
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "replace",
        "create",
        "attach",
        "detach",
        "pragma",
        "vacuum",
        "reindex",
    )
    for keyword in banned_keywords:
        if re.search(rf"\b{keyword}\b", lowered):
            raise ValueError(f"SQL 包含不允许的语句：{keyword}")


def run_query(sql: str) -> tuple[list[str], list[tuple]]:
    """
    执行 SQL 查询，返回 (列名列表, 数据行列表)。
    如果查询出错，抛出异常由调用方处理。
    结果最多返回 500 行，避免终端刷屏。
    """
    validate_readonly_sql(sql)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchmany(500)  # 最多取 500 行
        columns = [description[0] for description in cursor.description]
        data = [tuple(row) for row in rows]
        conn.close()
        return columns, data
    except Exception as exc:
        if not _is_db_open_error(exc):
            raise
        return _run_sqlite_cli(sql)
