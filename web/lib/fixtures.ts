import { PreviewPayload } from "./types";

export const previewPayload: PreviewPayload = {
  messages: [
    {
      role: "user",
      content: "上个季度哪些城市的收入动能下滑最明显？",
    },
    {
      role: "assistant",
      content:
        "结果页会先找出收入下滑最明显的城市，再比较订单量与价格变化，判断主要驱动因素。",
    },
  ],
  latest_result: {
    answer: `## 核心判断

表现较弱的城市，主要是被订单流失拖累，而不是价格变化。

结果页会先找出收入下滑最明显的城市，再比较订单量与价格变化，判断主要驱动因素。这会直接影响下一步动作：与其先做价格复盘，不如先深入看需求、活跃度，以及差城市在区域层面的订单集中度。`,
    chart_config: {
      type: "bar",
      x: "城市",
      y: ["订单量"],
      title: "城市群季度收入下滑对比",
    },
    raw_rows: [
      { 城市: "中山", 收入下滑: "-16.4%", 订单量: 23822 },
      { 城市: "深圳", 收入下滑: "-12.7%", 订单量: 18302 },
      { 城市: "珠海", 收入下滑: "-8.5%", 订单量: 15123 },
      { 城市: "佛山", 收入下滑: "-6.2%", 订单量: 13518 },
    ],
    db_error: null,
  },
};

export const previewBoard = [
  { label: "判断", value: "一个明确结论" },
  { label: "证据", value: "图表 + 表格" },
  { label: "追问", value: "下一步问题" },
];
