export type Role = "user" | "assistant";

export type Message = {
  role: Role;
  content: string;
};

export type ChartConfig = {
  type: "bar" | "line" | null;
  x: string | null;
  y: string[] | null;
  title: string | null;
};

export type ResultPayload = {
  answer: string;
  chart_config: ChartConfig | null;
  raw_rows: Array<Record<string, string | number | null>>;
  db_error: string | null;
};

export type SchemaStatus = {
  status: "loading" | "online" | "offline";
  detail: string;
};

export type PreviewPayload = {
  messages: Message[];
  latest_result: ResultPayload;
};
