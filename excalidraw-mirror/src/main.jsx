import React from "react";
import { createRoot } from "react-dom/client";
import { Excalidraw, exportToBlob } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";

// 暴露导出工具，便于离线脚本化/自检（不影响普通使用）
window.__exportToBlob = exportToBlob;

// 纯离线：不传任何协作/后端相关 props，使用内置本地状态。
function App() {
  return (
    <div style={{ height: "100vh", width: "100vw" }}>
      <Excalidraw
        initialData={{
          appState: { viewBackgroundColor: "#ffffff" },
        }}
        // 暴露 API 便于离线脚本化/自检（不影响普通使用）
        excalidrawAPI={(api) => {
          window.__excalidraw = api;
        }}
      />
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
