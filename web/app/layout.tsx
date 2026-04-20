import "./globals.css";

import type { Metadata } from "next";
import { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Data Analyze Workbench",
  description: "Next.js + FastAPI 版数据分析工作台",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
