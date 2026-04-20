import { ResultPayload, SchemaStatus } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type HistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export async function fetchSchemaStatus(): Promise<SchemaStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`health check failed: ${response.status}`);
    }
    const payload = (await response.json()) as {
      db_readable: boolean;
      db_error: string | null;
    };

    if (!payload.db_readable) {
      return {
        status: "offline",
        detail: payload.db_error ?? "数据库暂时不可用",
      };
    }

    return {
      status: "online",
      detail: "",
    };
  } catch (error) {
    return {
      status: "offline",
      detail: error instanceof Error ? error.message : "无法连接分析服务",
    };
  }
}

export async function analyzeQuestion(question: string, history: HistoryMessage[]): Promise<ResultPayload> {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });

  if (!response.ok) {
    let detail = "分析请求失败";
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // 保持默认错误信息即可
    }
    throw new Error(detail);
  }

  return (await response.json()) as ResultPayload;
}
