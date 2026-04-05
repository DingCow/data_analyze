# 项目进度追踪

## 项目概述

新能源充电桩与停车场数据分析 Agent，支持自然语言提问，自动路由到 SQL 查询或深度分析链路，同时提供 CLI 和 Web 两种交互方式。

---

## 文件结构

```
data_analyze/
├── .env                  # DEEPSEEK_API_KEY（不得硬编码）
├── AGENTS.md             # 项目协作规则与输出约束
├── main.py               # CLI 主入口，多轮对话循环，调用 router.run()
├── app.py                # Streamlit Web UI，支持图表渲染（Plotly）
├── run.sh                # 常用启动脚本
├── docs/                 # 项目文档、状态记录、操作说明
├── skills/               # 项目级协作 skill
├── src/
│   ├── db.py             # SQLite 工具层：连接、schema 提取、SQL 执行（只读，最多500行）
│   ├── llm.py            # 公共基础层：DeepSeek 客户端、TOOLS 定义、工具执行（含原始数据返回）
│   └── workflow/
│       ├── __init__.py
│       ├── router.py     # Router Agent：意图分类（simple/complex），分发到对应链路
│       ├── sql.py        # SQL Agent：专职取数，多次工具调用，只返回原始数据行
│       ├── analysis.py   # Analysis Agent：前置拆解（decompose）+ 后置推理（analyze）
│       └── report.py     # Report Agent：格式化 Markdown 报告 + 图表配置 JSON 输出
└── tests/                # 回归测试
```

---

## 已完成功能

### Phase 1：Text-to-SQL MVP ✅
- SQLite 只读连接（防误操作）
- 自动提取 schema + 业务说明，注入给 LLM 作上下文
- DeepSeek API 客户端封装（OpenAI 兼容接口）
- CLI 多轮对话（保留最近 10 轮历史）

### Phase 2：完整 Agent 框架 ✅
- **Router Agent**：用 deepseek-chat 做意图分类（simple/complex），低成本快速路由
- **SQL Agent**：工具调用循环（最多30次），只透传最后一次有数据的查询结果
- **Analysis Agent**：
  - `decompose()`：前置拆解，用 deepseek-reasoner 把模糊问题翻译成具体查询子任务
  - `analyze()`：后置推理，基于数据做深度分析，使用 deepseek-reasoner
- **Report Agent**：用 deepseek-chat 格式化 Markdown 报告，输出图表配置 JSON（line/bar/null）
- **Streamlit Web UI**（app.py）：
  - 气泡式对话展示
  - 侧边栏：数据库状态 + 清空对话
  - Plotly 图表渲染（折线图/柱状图）
  - 会话状态管理（session_state）
- DEBUG 模式：`.env` 中设 `DEBUG=true` 开启调试日志

---

## 待完成

### 财务/分润专项 Agent
- 数据源：`fees_24`、`taizhang`（分润比例）、`jiesuan`
- 核查结算金额 vs 实收金额差异
- 各电站/停车场分润收益排行

### 其他优化项
- SQL 自动修正重试（目前已有基础，SQL 出错会返回错误给模型）
- 对话历史在 Web UI 中支持导出
- 图表支持更多类型（饼图、散点图）

### Phase 3：LangChain 架构改造（待规划）
- 用 LangChain 框架替换手写的 Agent 调用逻辑
- 利用内置 Agent、Tool、Memory 抽象简化代码结构

---

## 架构图（当前数据流）

```
用户自然语言问题
       ↓
  Router Agent（deepseek-chat，意图分类）
  ├── simple → SQL Agent → 直接转 Markdown 表格返回
  └── complex
        ↓
  Analysis.decompose()（deepseek-reasoner，前置拆解）
        ↓
  SQL Agent（deepseek-chat，工具调用取数）
        ↓
  Analysis.analyze()（deepseek-reasoner，后置推理）
        ↓
  Report Agent（deepseek-chat，格式化 Markdown + 图表配置）
        ↓
  返回：(markdown文字, chart_config, raw_rows)
        ↓
  CLI: 展示 markdown    Web: 展示 markdown + Plotly 图表
```

---

## 运行方式

```bash
# CLI 模式
python3 main.py

# Web UI 模式
streamlit run app.py
```

---

## 数据库概览

| 表名 | 说明 | 行数 |
|------|------|------|
| orders_all | 充电订单主表（2021.10-2024.07） | ~318万 |
| taizhang | 充电站台账（静态数据） | 979 |
| parking_stations_all | 停车场信息 | 50,561 |
| fees_24 | 2024年费用结算 | 95,656 |
| users_info | 用户信息 | 188,247 |
| parking_taizhang | 停车场运营台账 | - |
| orders_230x/240x | 按月分区的历史订单 | - |
