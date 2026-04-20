import { Message, ResultPayload } from "./types";

export function stripMarkdown(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/^#+\s*/gm, "")
    .replace(/^[-*]\s*/gm, "")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

export function summarizeAnswer(answer: string): { title: string; summary: string } {
  const cleaned = stripMarkdown(answer);
  if (!cleaned) {
    return {
      title: "这轮分析完成后，会先给出一个核心判断。",
      summary: "随后继续向下展开证据图表、明细表格以及下一步追问。",
    };
  }

  const lines = cleaned
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const headingPattern = /^(核心判断|Core judgment)$/i;
  const contentLines = headingPattern.test(lines[0] ?? "") ? lines.slice(1) : lines;
  const title = contentLines[0] ?? cleaned;
  const summary =
    contentLines.slice(1).join(" ").trim() || "下方会继续展开完整的证据链路。";
  return { title, summary };
}

export function buildAssistantPreview(result: ResultPayload): string {
  if (result.answer) {
    const { summary } = summarizeAnswer(result.answer);
    return summary;
  }
  if (!result.raw_rows.length) {
    return "这一轮没有查到可展示的数据。";
  }
  return `当前已准备好 ${result.raw_rows.length} 行数据供对比，页面会同步展示图表和表格。`;
}

export function buildProcessItems(messages: Message[], latestResult: ResultPayload | null) {
  const lastUser = [...messages].reverse().find((message) => message.role === "user");
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
  const rowCount = latestResult?.raw_rows.length ?? 0;

  return [
    {
      meta: "问题 01 · 用户",
      body: lastUser?.content ?? "请先输入一个业务问题，工作台会围绕这个问题组织结果。",
      tone: "primary",
    },
    {
      meta: "步骤 02 · 助手",
      body:
        lastAssistant?.content ??
        "系统会把问题翻译成查询与分析链路，再把结果组织成可阅读的结论与证据。",
      tone: "secondary",
    },
    {
      meta: "步骤 03 · 证据",
      body:
        rowCount > 0
          ? `当前已准备好 ${rowCount} 行数据供对比，页面会同时给出图表和表格。`
          : "如果本轮没有取到结果，页面会明确标出空结果或数据库异常。",
      tone: "secondary",
    },
  ];
}

export function buildFollowUps(result: ResultPayload | null): string[] {
  if (!result?.raw_rows.length) {
    return [
      "哪些城市在区县或时段维度上也出现了最明显的订单下滑？",
      "和上一季度相比，哪些变化主要来自销量，哪些主要来自价格？",
      "如果只聚焦表现最差的几个城市，下一步应该先从哪里开始排查？",
    ];
  }

  const firstRow = result.raw_rows[0];
  const firstKey = Object.keys(firstRow)[0];
  const firstValue = firstKey ? String(firstRow[firstKey]) : "这些重点城市";

  return [
    `围绕 ${firstValue} 继续下钻时，应该优先看哪些区域、时段或站点？`,
    "如果把订单量、活跃度与价格变化拆开看，真正拖累收入的是哪一项？",
    "下一轮分析最值得补充哪张宽表，才能更快判断是需求问题还是供给问题？",
  ];
}
