export default function NotFound() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "#f4f7fb",
        color: "#18212c",
        fontFamily: '"PingFang SC", "Helvetica Neue", sans-serif',
      }}
    >
      <section style={{ textAlign: "center", padding: "32px" }}>
        <p style={{ color: "#3c99dd", fontWeight: 700, letterSpacing: "0.08em" }}>+ 页面不存在</p>
        <h1 style={{ fontFamily: '"Source Han Serif SC", serif', fontSize: "3rem", margin: "12px 0" }}>
          这个入口没有内容。
        </h1>
        <p style={{ color: "#69778b", margin: 0 }}>请回到分析工作台继续提问或查看示例。</p>
      </section>
    </main>
  );
}
