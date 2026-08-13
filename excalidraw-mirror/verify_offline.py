"""
Excalidraw 离线镜像断网验证：
- 拦截所有 http(s) 请求并 abort（模拟纯离线）
- 打开 dist/index.html (file://)
- 等待编辑器就绪（window.__excalidraw 就绪）
- 真实鼠标绘制一个矩形
- 读取场景元素数、统计外部请求 / 错误
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DIST = Path(__file__).parent / "dist" / "index.html"
URL = DIST.as_uri()  # file://...

external_requests = []
page_errors = []
console_errors = []


def main():
    if not DIST.exists():
        print(json.dumps({"ok": False, "reason": f"dist not found: {DIST}"}, ensure_ascii=False))
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # 拦截一切外部请求，模拟离线
        def on_route(route):
            u = route.request.url
            if u.startswith("http://") or u.startswith("https://"):
                external_requests.append(u)
                return route.abort()
            return route.continue_()

        page.route("**/*", on_route)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # 等待 Excalidraw API 就绪
        page.wait_for_function("window.__excalidraw && window.__excalidraw.getSceneElements", timeout=45000)

        # 通过 API 确定性切换矩形工具（不依赖键盘焦点）
        page.evaluate("window.__excalidraw.setActiveTool({type:'rectangle'})")
        active_tool = page.evaluate("window.__excalidraw.getAppState().activeTool.type")
        canvas = page.locator("canvas.excalidraw__canvas.interactive")
        box = canvas.bounding_box()

        # 真实点击（中央空白区，确保落在画布而非 UI 面板上）
        page.mouse.click(box["x"] + 640, box["y"] + 400)
        page.wait_for_timeout(300)
        click_count = page.evaluate("window.__excalidraw.getSceneElements().length")

        # 真实拖拽再画一个矩形（起点/终点均在中央空白区，避开顶栏/左工具栏/底栏）
        sx, sy = box["x"] + 450, box["y"] + 300
        ex, ey = box["x"] + 780, box["y"] + 520
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move((sx + ex) / 2, (sy + ey) / 2, steps=12)
        page.mouse.move(ex, ey, steps=12)
        page.mouse.up()

        # 等一帧渲染
        page.wait_for_timeout(800)

        count = page.evaluate("window.__excalidraw.getSceneElements().length")
        types = page.evaluate("[...window.__excalidraw.getSceneElements()].map(e=>e.type)")

        # 离线导出能力自检（纯客户端 canvas/SVG，不应触外部请求）
        export_blob = page.evaluate(
            """async () => {
                const els = window.__excalidraw.getSceneElements();
                if (!els.length) return null;
                const blob = await window.__exportToBlob({
                    elements: els,
                    appState: window.__excalidraw.getAppState(),
                    files: (window.__excalidraw.getFiles && window.__excalidraw.getFiles()) || {}
                });
                return blob ? { type: blob.type, size: blob.size } : null;
            }"""
        )

        # 导出能力自检（纯客户端，不应触发外部请求）
        try:
            blob = page.evaluate("window.__excalidraw.getSceneElements().length >= 1")
        except Exception:
            blob = None

        page.screenshot(path=str(Path(__file__).parent / "verify_screenshot.png"))

        browser.close()

    result = {
        "ok": True,
        "file": str(DIST),
        "active_tool_before_draw": active_tool,
        "canvas_box": box,
        "click_created_count": click_count,
        "scene_element_count": count,
        "scene_element_types": types,
        "export_to_blob": export_blob,
        "external_requests": external_requests,
        "external_request_count": len(external_requests),
        "page_errors": page_errors,
        "page_error_count": len(page_errors),
        "console_errors": console_errors,
        "console_error_count": len(console_errors),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
