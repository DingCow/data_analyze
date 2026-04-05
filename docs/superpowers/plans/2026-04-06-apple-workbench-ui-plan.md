# Apple Workbench UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留当前 Streamlit 页面结构和业务逻辑的前提下，先备份原始 UI，再使用 `pencil` MCP 产出苹果式轻量工作台目标稿，最后把目标稿映射到 `app.py` 的样式系统并完成验证。

**Architecture:** 这次改造只触达展示层。实现会先做文件级备份，避免当前非 Git 目录下没有版本回退点；再通过 `pencil` 形成单页面工作台设计稿，锁定苹果风视觉目标；最后通过 `app.py` 内的 CSS 变量、面板样式和输入区样式做低风险替换，并用现有单测加手工页面检查验证不破坏原功能。

**Tech Stack:** Python、Streamlit、unittest、Pencil MCP

---

## File Structure

- Modify: `app.py`
- Modify: `tests/test_app.py`
- Create: `app_backup_2026_04_06.py`
- Create: `docs/superpowers/plans/2026-04-06-apple-workbench-ui-plan.md`
- Create: `docs/superpowers/specs/2026-04-06-apple-workbench-ui-design.md`

---

### Task 1: 备份当前 UI 基线

**Files:**
- Create: `app_backup_2026_04_06.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: 为备份文件增加存在性回归测试**

```python
import os
import unittest


class TestUiBackup(unittest.TestCase):
    """确保 UI 改造前保留了可回退的原始文件副本。"""

    def test_backup_file_exists_before_visual_refresh(self):
        backup_path = os.path.join(os.path.dirname(__file__), "..", "app_backup_2026_04_06.py")
        self.assertTrue(os.path.exists(os.path.abspath(backup_path)))
```

- [ ] **Step 2: 运行测试，确认在创建备份前先失败**

Run: `python3 -m unittest tests.test_app.TestUiBackup.test_backup_file_exists_before_visual_refresh -v`  
Expected: FAIL，提示找不到 `app_backup_2026_04_06.py`

- [ ] **Step 3: 创建 `app.py` 的完整备份副本**

```python
# app_backup_2026_04_06.py
# 内容直接复制自当前改造前的 app.py
```

- [ ] **Step 4: 再次运行测试，确认备份文件已建立**

Run: `python3 -m unittest tests.test_app.TestUiBackup.test_backup_file_exists_before_visual_refresh -v`  
Expected: PASS

- [ ] **Step 5: 记录本任务完成**

```bash
ls app_backup_2026_04_06.py
```

Expected: 输出 `app_backup_2026_04_06.py`

---

### Task 2: 用 Pencil 产出苹果式轻量工作台目标稿

**Files:**
- Modify: `docs/superpowers/specs/2026-04-06-apple-workbench-ui-design.md`

- [ ] **Step 1: 在 spec 中补充设计稿已完成后的落地检查点**

```markdown
## 12. 设计稿落地检查点

- 顶部仍保留标题与状态
- 左侧仍保留历史/过程线程
- 右侧仍保留结果、图表、表格
- 底部仍保留统一输入区
- 风格转为苹果式轻玻璃工作台
```

- [ ] **Step 2: 使用 `pencil` 建立单页面目标稿**

```text
工作区应包含：
1. 顶部标题 + 在线状态胶囊
2. 左侧轻玻璃历史面板
3. 右侧主结果面板
4. 底部输入托盘
5. 整体采用浅色、通透、克制的 macOS 工作台视觉
```

- [ ] **Step 3: 目测核对设计稿是否符合 spec**

Run: 使用 `pencil` 的截图或画布状态检查以下点  
Expected:
- 顶部是轻层级
- 左侧存在感弱于右侧
- 右侧是主视觉焦点
- 输入区像底部操作托盘

- [ ] **Step 4: 将设计稿结果回写到 spec 的“已确认状态”说明**

```markdown
## 13. 设计稿确认状态

- 已在 pencil 中完成目标稿
- 目标稿遵守“只改视觉、不改结构”
- 后续 CSS 以该稿的背景、圆角、面板、输入区语言为准
```

- [ ] **Step 5: 记录本任务完成**

```bash
echo "pencil design completed"
```

Expected: 输出 `pencil design completed`

---

### Task 3: 回写苹果式视觉样式到 `app.py`

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: 先写失败测试，锁定新的苹果式样式 token**

```python
def test_inject_styles_uses_apple_workbench_tokens(self):
    captured: list[str] = []
    original_markdown = app.st.markdown

    try:
        app.st.markdown = lambda value, unsafe_allow_html=False: captured.append(value)
        app.inject_styles(app.build_layout_config())
    finally:
        app.st.markdown = original_markdown

    css = captured[0]
    self.assertIn("--bg: #f2f4f7;", css)
    self.assertIn("--surface: rgba(255, 255, 255, 0.58);", css)
    self.assertIn("--surface-strong: rgba(255, 255, 255, 0.78);", css)
    self.assertIn("--accent: #0f62fe;", css)
    self.assertIn("backdrop-filter: blur(24px);", css)
    self.assertIn("border-radius: 30px !important;", css)
```

- [ ] **Step 2: 运行测试，确认现有样式与新目标稿不一致**

Run: `python3 -m unittest tests.test_app.TestHomepageViewModels.test_inject_styles_uses_apple_workbench_tokens -v`  
Expected: FAIL，旧 CSS token 与新断言不匹配

- [ ] **Step 3: 按 pencil 目标稿改写 `inject_styles()` 中的核心视觉层**

```python
:root {
  --bg: #f2f4f7;
  --bg-accent:
    radial-gradient(circle at top left, rgba(167, 196, 255, 0.42), transparent 34%),
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.72), transparent 28%),
    linear-gradient(180deg, #f7f8fb 0%, #eef2f6 100%);
  --surface: rgba(255, 255, 255, 0.58);
  --surface-strong: rgba(255, 255, 255, 0.78);
  --surface-muted: rgba(248, 250, 252, 0.72);
  --text: #111827;
  --text-soft: #667085;
  --line: rgba(15, 23, 42, 0.08);
  --accent: #0f62fe;
  --shadow-lg: 0 20px 60px rgba(15, 23, 42, 0.08);
}

div[data-testid="stForm"] {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(24px);
  border-radius: 30px !important;
}
```

- [ ] **Step 4: 收口各分区样式，使其匹配轻玻璃工作台**

```python
.conversation-panel.process-shell {
  background: rgba(255, 255, 255, 0.42);
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(20px);
  border-radius: 24px;
}

.summary-hero.results-shell,
.insight-card.insight-shell,
.plain-section.suggested-questions,
.plain-section.follow-up-shell {
  background: rgba(255, 255, 255, 0.54);
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(22px);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}
```

- [ ] **Step 5: 跑页面模型相关测试，确认展示层未断**

Run: `python3 -m unittest tests.test_app -v`  
Expected: PASS

---

### Task 4: 做页面验证与回归确认

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app.py`
- Reference: `docs/manual_checklist.md`

- [ ] **Step 1: 启动 Streamlit 页面，核对苹果式工作台效果**

Run: `streamlit run app.py`  
Expected:
- 页面能正常打开
- 顶部更轻
- 左侧更安静
- 右侧更聚焦
- 输入区更像底部操作托盘

- [ ] **Step 2: 跑项目自动测试，确认改造没伤到主流程**

Run: `python3 -m unittest discover -s tests -v`  
Expected: PASS

- [ ] **Step 3: 按手工清单执行至少前 3 条问题验证**

```text
1. users_info 表前 5 行数据是什么？
2. users_info 一共有多少条记录？
3. 2024 年各月充电收入趋势如何？
```

Expected:
- 页面无报错
- simple 问题仍直接出结果
- complex 问题仍能出文字结论和图表

- [ ] **Step 4: 如发现视觉或交互回归，最小化回调样式**

```python
# 只调整 CSS token、间距、圆角、阴影
# 不修改 router.run、handle_question、db 相关逻辑
```

- [ ] **Step 5: 记录本任务完成**

```bash
python3 -m unittest discover -s tests -v
```

Expected: 全部测试通过
