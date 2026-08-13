import React from "react";
import { createRoot } from "react-dom/client";
import { Tldraw } from "@tldraw/tldraw";
import { getAssetUrlsByMetaUrl } from "@tldraw/assets/urls";
import "@tldraw/tldraw/tldraw.css";

// 本地化资源：urls 用 new URL('./...', import.meta.url) 引用包内字体/图标，
// Vite 会打包、vite-plugin-singlefile 再内联为 data URI → 离线零外部请求。
const assetUrls = getAssetUrlsByMetaUrl();

function App() {
  return (
    <div style={{ position: "fixed", inset: 0 }}>
      <Tldraw
        assetUrls={assetUrls}
        // 暴露 editor 便于离线脚本化/自检（不影响普通使用）
        onMount={(editor) => {
          window.__editor = editor;
        }}
      />
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
