import test from "node:test";
import assert from "node:assert/strict";

import { summarizeAnswer } from "./ui";

test("空字符串时返回默认标题和摘要", () => {
  const result = summarizeAnswer("");

  assert.equal(result.title, "这轮分析完成后，会先给出一个核心判断。");
  assert.equal(result.summary, "随后继续向下展开证据图表、明细表格以及下一步追问。");
});

test("会跳过中文章节标题并提取真正结论", () => {
  const result = summarizeAnswer("## 核心判断\n表现较弱的城市主要是被订单流失拖累。\n下一步需要检查活跃度。");

  assert.equal(result.title, "表现较弱的城市主要是被订单流失拖累。");
  assert.equal(result.summary, "下一步需要检查活跃度。");
});

test("会跳过英文章节标题并提取真正结论", () => {
  const result = summarizeAnswer("## Core judgment\nOrder loss is the main driver.\nCheck activity next.");

  assert.equal(result.title, "Order loss is the main driver.");
  assert.equal(result.summary, "Check activity next.");
});

test("只有正文时直接把首句作为标题", () => {
  const result = summarizeAnswer("订单量下滑最明显的是中山。\n珠海次之。");

  assert.equal(result.title, "订单量下滑最明显的是中山。");
  assert.equal(result.summary, "珠海次之。");
});

test("只有章节标题时回退到章节标题本身", () => {
  const result = summarizeAnswer("## 核心判断");

  assert.equal(result.title, "核心判断");
  assert.equal(result.summary, "下方会继续展开完整的证据链路。");
});
