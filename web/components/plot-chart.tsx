"use client";

import dynamic from "next/dynamic";

import { ChartConfig } from "../lib/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type PlotChartProps = {
  chartConfig: ChartConfig | null;
  rows: Array<Record<string, string | number | null>>;
};

function toAxisValues(rows: Array<Record<string, string | number | null>>, column: string | null) {
  if (!column) {
    return [];
  }
  return rows.map((row) => row[column]);
}

export function PlotChart({ chartConfig, rows }: PlotChartProps) {
  if (!chartConfig || !chartConfig.type || !chartConfig.x || !chartConfig.y?.length || !rows.length) {
    return null;
  }

  const x = toAxisValues(rows, chartConfig.x);
  const data = chartConfig.y.map((column, index) => ({
    type: chartConfig.type,
    x,
    y: toAxisValues(rows, column),
    name: column,
    marker: {
      color: index === 0 ? "#17202a" : "#4f99d5",
    },
    line: {
      color: index === 0 ? "#17202a" : "#4f99d5",
      width: 3,
    },
  }));

  return (
    <Plot
      data={data}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%", height: "100%" }}
      layout={{
        autosize: true,
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        margin: { l: 52, r: 20, t: 16, b: 48 },
        font: {
          family: '"PingFang SC", "Helvetica Neue", sans-serif',
          color: "#64748b",
        },
        xaxis: {
          tickfont: { size: 14 },
          gridcolor: "rgba(203, 213, 225, 0.28)",
          zeroline: false,
        },
        yaxis: {
          tickfont: { size: 14 },
          gridcolor: "rgba(203, 213, 225, 0.4)",
          zeroline: false,
        },
        showlegend: chartConfig.y.length > 1,
      }}
      useResizeHandler
    />
  );
}
