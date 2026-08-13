"""
React Flow 离线镜像断网验证：
- 拦截所有 http(s) 并 abort（模拟纯离线）
- 打开 dist/index.html (file://)
- 等流程图节点渲染；真实点击"添加节点"；真实拖拽一个节点
- 统计外部请求 / 错误
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
        page.wait_for_selector(".react-flow__node", timeout=30000)
        page.wait_for_timeout(1000)

        before = page.evaluate("document.querySelectorAll('.react-flow__node').length")

        # 真实点击"添加节点"
        page.get_by_text("添加节点", exact=True).click(timeout=8000)
        page.wait_for_timeout(600)
        after_add = page.evaluate("document.querySelectorAll('.react-flow__node').length")

        # 真实拖拽第一个节点（证明画布可交互）
        box = page.locator(".react-flow__node").first.bounding_box()
        if box:
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + 120, box["y"] + 120, steps=10)
            page.mouse.up()
            page.wait_for_timeout(400)

        # 导出 PNG（纯客户端）
        try:
            page.get_by_text("导出 PNG", exact=True).click(timeout=8000)
            page.wait_for_timeout(800)
            export_ok = True
        except Exception as e:
            export_ok = False
            console_errors.append("export: " + str(e))

        after_drag = page.evaluate("document.querySelectorAll('.react-flow__node').length")
        page.screenshot(path=str(Path(__file__).parent / "verify_screenshot.png"))
        browser.close()

    result = {
        "ok": True,
        "file": str(DIST),
        "nodes_before": before,
        "nodes_after_add": after_add,
        "nodes_after_drag": after_drag,
        "export_clicked": export_ok,
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
