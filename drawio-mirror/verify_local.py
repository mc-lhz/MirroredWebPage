#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_local.py — 验证真·draw.io 本地 HTTP 镜像在「离线」下可用。
- Playwright 拦截一切非 127.0.0.1:8080 的外部请求并 abort（模拟纯离线）。
- 检查：编辑器加载、点击侧栏形状→单击画布真实插入图形、外部请求归类、错误统计。
- 用 SVG <g> 数量差值作为「图形被画出」的功能证据（editorUi 不挂 window，DOM 判定最稳）。
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

LOCAL_ORIGIN = "http://127.0.0.1:8080"
URL = LOCAL_ORIGIN + "/index.html"


def main():
    external_blocked = []
    page_errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_context(viewport={"width": 1280, "height": 800}).new_page()
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        def route(route):
            u = route.request.url
            if "127.0.0.1:8080" in u:
                return route.continue_()
            external_blocked.append(u)
            return route.abort()

        page.route("**/*", route)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        try:
            page.wait_for_selector(".geDiagramContainer", timeout=30000)
        except Exception as e:
            out = {"ok": False, "stage": "editor_load", "error": str(e),
                   "external_blocked": external_blocked, "page_errors": page_errors}
            print(json.dumps(out, ensure_ascii=False))
            browser.close()
            sys.exit(0)

        page.wait_for_timeout(1500)

        # 图形计数辅助
        def gcount():
            return page.evaluate("document.querySelectorAll('.geDiagramContainer svg g').length")

        base = gcount()

        # 真实交互：点击侧栏第一个形状（矩形），再单击画布中央落图
        item = page.locator(".geSidebarContainer .geItem").first
        item.click()
        cbox = page.locator(".geDiagramContainer").first.bounding_box()
        cx, cy = cbox["x"] + cbox["width"] / 2, cbox["y"] + cbox["height"] / 2
        page.mouse.click(cx, cy)
        page.wait_for_timeout(1000)
        after = gcount()

        # 再拖拽一个，覆盖「拖放」路径
        ib = item.bounding_box()
        ix, iy = ib["x"] + ib["width"] / 2, ib["y"] + ib["height"] / 2
        page.mouse.move(ix, iy)
        page.mouse.down()
        page.mouse.move((ix + cx) / 2, (iy + cy) / 2, steps=8)
        page.mouse.move(cx + 160, cy + 130, steps=8)
        page.mouse.up()
        page.wait_for_timeout(1000)
        after_drag = gcount()

        shot = Path(__file__).parent / "verify_screenshot_local.png"
        page.screenshot(path=str(shot))
        browser.close()

        # 把 3 个外部云集成脚本的加载失败归类为「预期离线、非致命」
        external_hosts = ["js.pusher.com", "apis.google.com", "www.dropbox.com"]
        unexpected_console = [c for c in console_errors
                              if not (c.startswith("Failed to load resource") or c.startswith("net::ERR"))]

        result = {
            "ok": True,
            "editor_loaded": True,
            "shape_added_by_click": after > base,
            "shape_added_by_drag": after_drag > after,
            "after_click_g": after,
            "after_drag_g": after_drag,
            "base_g": base,
            "external_blocked_count": len(external_blocked),
            "external_blocked": external_blocked,
            "external_is_cloud_integration_only": all(
                any(h in u for h in external_hosts) for u in external_blocked
            ),
            "page_error_count": len(page_errors),
            "page_errors": page_errors[:8],
            "console_error_count": len(console_errors),
            "unexpected_console_error_count": len(unexpected_console),
            "unexpected_console_errors": unexpected_console[:8],
            "screenshot": str(shot),
        }
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
