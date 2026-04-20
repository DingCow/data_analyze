"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import { PlotChart } from "../components/plot-chart";
import { analyzeQuestion, fetchSchemaStatus } from "../lib/api";
import { previewBoard, previewPayload } from "../lib/fixtures";
import { buildAssistantPreview, buildFollowUps, buildProcessItems, summarizeAnswer } from "../lib/ui";
import { Message, ResultPayload, SchemaStatus } from "../lib/types";

const EMPTY_STATUS: SchemaStatus = {
  status: "loading",
  detail: "",
};

export default function Page() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [latestResult, setLatestResult] = useState<ResultPayload | null>(null);
  const [schemaStatus, setSchemaStatus] = useState<SchemaStatus>(EMPTY_STATUS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSchemaStatus().then(setSchemaStatus);
  }, []);

  const answerParts = useMemo(() => summarizeAnswer(latestResult?.answer ?? ""), [latestResult?.answer]);
  const processItems = useMemo(() => buildProcessItems(messages, latestResult), [messages, latestResult]);
  const followUps = useMemo(() => buildFollowUps(latestResult), [latestResult]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = question.trim();
    if (!trimmed || loading) {
      return;
    }

    setLoading(true);
    setError("");

    const nextHistory = [...messages];
    try {
      const result = await analyzeQuestion(trimmed, nextHistory);
      if (result.db_error) {
        setSchemaStatus({ status: "offline", detail: result.db_error });
        setError(result.db_error);
        setLatestResult(result);
        return;
      }

      const assistantPreview = buildAssistantPreview(result);
      setMessages([
        ...nextHistory,
        { role: "user", content: trimmed },
        { role: "assistant", content: assistantPreview },
      ]);
      setLatestResult(result);
      setQuestion("");
      setSchemaStatus({ status: "online", detail: "" });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "分析请求失败");
    } finally {
      setLoading(false);
    }
  }

  function handlePreview() {
    setMessages(previewPayload.messages);
    setLatestResult(previewPayload.latest_result);
    setError("");
  }

  const statusText =
    schemaStatus.status === "loading"
      ? "正在检查数据源"
      : schemaStatus.status === "online"
        ? "数据源在线"
        : "数据源离线";

  return (
    <main className="page-shell">
      <div className="page-noise" />
      <section className="page">
        <header className="topbar">
          <div className="topbar-copy">
            <p className="eyebrow">+ 分析工作台</p>
            <h1>数据分析助手</h1>
            <p className="lede">
              从一个业务问题开始，快速得到结论、证据和下一步追问。
            </p>
          </div>
          <div className={`status-pill ${schemaStatus.status === "offline" ? "is-offline" : ""}`}>
            <span className="status-dot" />
            <span>{statusText}</span>
          </div>
        </header>

        <section className="input-panel">
          <div className="divider" />
          <form className="composer" onSubmit={handleSubmit}>
            <div className="composer-field">
              <span className="composer-badge">{latestResult ? "继续追问" : "就绪"}</span>
              <input
                aria-label="分析问题"
                className="composer-input"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={
                  latestResult
                    ? "继续追问：例如哪些表现较弱的城市，同时也出现了最明显的订单下滑？"
                    : "从一个业务判断开始：例如上个季度哪些城市的收入动能下滑最明显？"
                }
              />
            </div>
            <button className="primary-button" disabled={loading || schemaStatus.status === "offline"} type="submit">
              {loading ? "分析中..." : "开始分析"}
            </button>
            <button className="secondary-button" onClick={handlePreview} type="button">
              查看示例
            </button>
          </form>
          {(error || schemaStatus.detail) && (
            <p className="error-text">{error || schemaStatus.detail}</p>
          )}
        </section>

        {!latestResult && (
          <section className="empty-board">
            <div className="empty-copy">
              <p className="eyebrow">+ 结果预期</p>
              <h2>先从业务判断出发，再把结论、证据和追问排成一条阅读链路。</h2>
              <p>
                输入一个你真正关心的问题，页面会把分析过程整理成更容易阅读和继续追问的工作台。
              </p>
            </div>
            <div className="preview-grid">
              {previewBoard.map((item) => (
                <article className="preview-metric" key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </article>
              ))}
            </div>
          </section>
        )}

        {latestResult && (
          <>
            <section className="hero-card">
              <p className="eyebrow">+ 结果概览</p>
              <h2>{answerParts.title}</h2>
              <p className="hero-summary">{answerParts.summary}</p>
              <div className="hero-metrics">
                <article>
                  <span>模式</span>
                  <strong>{latestResult.answer ? "多步分析" : "直接查询"}</strong>
                </article>
                <article>
                  <span>行数</span>
                  <strong>{latestResult.raw_rows.length}</strong>
                </article>
                <article>
                  <span>图形</span>
                  <strong>{latestResult.chart_config?.type ? "1 张图" : "未生成"}</strong>
                </article>
              </div>
            </section>

            <section className="two-column">
              <article className="panel-card">
                <p className="eyebrow">+ 分析过程</p>
                <div className="process-list">
                  {processItems.map((item) => (
                    <div className="process-item" key={item.meta}>
                      <p className="process-meta">{item.meta}</p>
                      <p className={`process-body ${item.tone}`}>{item.body}</p>
                    </div>
                  ))}
                </div>
              </article>
              <article className="panel-card">
                <p className="eyebrow">+ 核心判断</p>
                <h3 className="panel-title">{answerParts.title}</h3>
                <div className="markdown-body">
                  <ReactMarkdown>{latestResult.answer || "本轮没有生成文字结论，但下方保留了结构化查询结果。"}</ReactMarkdown>
                </div>
              </article>
            </section>

            <section className="two-column evidence-grid">
              <article className="panel-card evidence-card">
                <p className="eyebrow">+ 证据图表</p>
                <h3 className="panel-title">{latestResult.chart_config?.title ?? "结构化结果视图"}</h3>
                <div className="chart-shell">
                  <PlotChart chartConfig={latestResult.chart_config} rows={latestResult.raw_rows} />
                  {!latestResult.chart_config?.type && (
                    <div className="empty-plot">这轮结果不适合直接画图，保留下方表格做明细确认。</div>
                  )}
                </div>
                <div className="evidence-meta">
                  <span>图形视图</span>
                  <strong>行数 {latestResult.raw_rows.length}</strong>
                </div>
              </article>

              <article className="panel-card evidence-card">
                <p className="eyebrow">+ 证据表格</p>
                <h3 className="panel-title">
                  {latestResult.answer ? "城市收入下滑快照" : "本轮查询结果"}
                </h3>
                <div className="table-shell">
                  {latestResult.raw_rows.length > 0 ? (
                    <table>
                      <thead>
                        <tr>
                          {Object.keys(latestResult.raw_rows[0]).map((column) => (
                            <th key={column}>{column}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {latestResult.raw_rows.map((row, index) => (
                          <tr key={`${index}-${Object.values(row).join("-")}`}>
                            {Object.keys(latestResult.raw_rows[0]).map((column) => (
                              <td key={column}>{row[column] ?? ""}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="empty-plot">本轮没有查到结构化结果。</div>
                  )}
                </div>
                <div className="evidence-meta">
                  <span>快照表</span>
                  <strong>{latestResult.raw_rows.length} 行</strong>
                </div>
              </article>
            </section>

            <section className="follow-up-card">
              <p className="eyebrow">+ 下一步问题</p>
              <div className="follow-up-grid">
                {followUps.map((questionText) => (
                  <article className="follow-up-item" key={questionText}>
                    <p>{questionText}</p>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </section>
    </main>
  );
}
