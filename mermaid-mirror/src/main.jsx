import React, { useState, useRef, useEffect, useCallback } from "react";
import { createRoot } from "react-dom/client";
import mermaid from "mermaid";

// 纯离线：mermaid 把文本渲染为内联 SVG，不依赖任何本地 XHR/后端。
mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });

const DEFAULT = `graph TD
  A[开始] --> B{判断条件}
  B -->|是| C[执行处理]
  B -->|否| D[直接结束]
  C --> D
  D --> E([收尾])
`;

function App() {
  const [code, setCode] = useState(DEFAULT);
  const previewRef = useRef(null);
  const idRef = useRef(0);

  const render = useCallback(async (src) => {
    if (!src || !src.trim()) {
      if (previewRef.current) previewRef.current.innerHTML = "";
      return;
    }
    idRef.current += 1;
    const id = "mmd-" + idRef.current;
    try {
      const { svg } = await mermaid.render(id, src);
      if (previewRef.current) previewRef.current.innerHTML = svg;
    } catch (e) {
      if (previewRef.current)
        previewRef.current.innerHTML =
          '<pre style="color:#c00;white-space:pre-wrap">' + String(e) + "</pre>";
    }
  }, []);

  useEffect(() => {
    render(code);
  }, [code, render]);

  const exportSvg = () => {
    const svg = previewRef.current && previewRef.current.querySelector("svg");
    if (!svg) return;
    const s = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([s], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "diagram.svg";
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportPng = () => {
    const svg = previewRef.current && previewRef.current.querySelector("svg");
    if (!svg) return;
    const s = new XMLSerializer().serializeToString(svg);
    const svgBlob = new Blob([s], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext("2d");
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);
      canvas.toBlob((b) => {
        if (!b) return;
        const pngUrl = URL.createObjectURL(b);
        const a = document.createElement("a");
        a.href = pngUrl;
        a.download = "diagram.png";
        a.click();
        URL.revokeObjectURL(pngUrl);
      });
    };
    img.src = url;
  };

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", fontFamily: "sans-serif" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: "1px solid #ccc" }}>
        <div style={{ padding: 8, display: "flex", gap: 8, borderBottom: "1px solid #eee" }}>
          <button onClick={exportSvg}>导出 SVG</button>
          <button onClick={exportPng}>导出 PNG</button>
        </div>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          style={{
            flex: 1,
            fontFamily: "monospace",
            fontSize: 14,
            padding: 8,
            border: "none",
            outline: "none",
            resize: "none",
            lineHeight: 1.5,
          }}
        />
      </div>
      <div
        ref={previewRef}
        id="preview"
        style={{
          flex: 1,
          overflow: "auto",
          padding: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#fafafa",
        }}
      />
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
