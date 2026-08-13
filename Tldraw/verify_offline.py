"""
tldraw 离线镜像断网验证：
- 拦截所有 http(s) 请求并 abort（模拟纯离线）
- 打开 dist/index.html (file://)
- 等待编辑器就绪（window.__editor 就绪）
- 切换到画笔工具并真实鼠标拖拽绘制
- 读取页面图形数、统计外部请求 / 错误
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DIST = Path(__file__).parent / "dist" / "index.html"
URL = DIST.as_uri()

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
        # 只等 editor 挂载（不碰 computed getter，避免在非响应式上下文抛错）
        page.wait_for_function("window.__editor !== undefined && window.__editor !== null", timeout=45000)

        # 切换到画笔(draw)工具并真实拖拽
        active_tool = page.evaluate(
            "() => { window.__editor.setCurrentTool('draw'); return window.__editor.getCurrentToolId(); }"
        )

        # 中央空白区拖拽（避开左侧工具栏/右侧面板）
        sx, sy = 450, 300
        ex, ey = 800, 520
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move((sx + ex) / 2, (sy + ey) / 2, steps=12)
        page.mouse.move(ex, ey, steps=12)
        page.mouse.up()
        page.wait_for_timeout(800)

        # 通过渲染结果 DOM 判定（不依赖 editor computed）
        count = page.evaluate("document.querySelectorAll('[data-shape-id]').length")
        types = page.evaluate(
            "Array.from(document.querySelectorAll('[data-shape-id]')).map(e=>e.getAttribute('data-shape-type')||'').filter(Boolean)"
        )

        page.screenshot(path=str(Path(__file__).parent / "verify_screenshot.png"))
        browser.close()

    result = {
        "ok": True,
        "file": str(DIST),
        "active_tool": active_tool,
        "shape_count": count,
        "shape_types": types,
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
