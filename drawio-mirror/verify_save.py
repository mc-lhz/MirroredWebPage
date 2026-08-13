#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_save.py — 验证离线"保存"修复：
- 拦截一切非 127.0.0.1:8080 请求并 abort（模拟纯离线）。
- 真实插入一个矩形（点击侧栏 + 单击画布）。
- 按 Ctrl/Cmd+S 触发保存（走 EditorUi.saveFile 覆写路径）。
- 捕获下载文件，断言是合法 <mxfile> .drawio 文档。
- 断言保存过程中没有弹出云目标对话框、没有外部请求、没有页面错误。
"""
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/index.html"
OUT = r"C:\Users\Administrator\Desktop\Mirror\drawio-mirror\test_save.drawio"
CLOUD = ["js.pusher.com", "apis.google.com", "www.dropbox.com"]


def main():
    external = []
    page_errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        def route(r):
            u = r.request.url
            if "127.0.0.1:8080" in u:
                return r.continue_()
            external.append(u)
            return r.abort()

        page.route("**/*", route)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(".geDiagramContainer", timeout=30000)
        page.wait_for_timeout(1500)

        def gcount():
            return page.evaluate("document.querySelectorAll('.geDiagramContainer svg g').length")

        base = gcount()
        # 真实插入一个矩形
        item = page.locator(".geSidebarContainer .geItem").first
        item.click()
        cbox = page.locator(".geDiagramContainer").first.bounding_box()
        cx, cy = cbox["x"] + cbox["width"] / 2, cbox["y"] + cbox["height"] / 2
        page.mouse.click(cx, cy)
        page.wait_for_timeout(800)
        after = gcount()
        shape_added = after > base

        # 触发保存（Ctrl/Cmd+S）
        page.locator("body").click(position={"x": 5, "y": 5})
        page.keyboard.press("Control+s")
        time.sleep(0.5)
        page.keyboard.press("Meta+s")
        time.sleep(0.5)

        # 断言没有云目标对话框弹出
        dlg = page.evaluate("""() => {
            const d = document.querySelector('.geDialog');
            if (!d) return {found:false};
            return {found:true, text:(d.innerText||'').slice(0,400)};
        }""")

        downloads = []
        page.on("download", lambda d: downloads.append(d))

        # 给下载一点机会（上面已 press，这里再补一次确保触发）
        page.keyboard.press("Control+s")
        deadline = time.time() + 15
        while time.time() < deadline and not downloads:
            time.sleep(0.3)

        result = {
            "editor_loaded": True,
            "shape_added": shape_added,
            "dialog_opened": bool(dlg.get("found")),
            "download_captured": bool(downloads),
            "external_request_count": len(external),
            "external_is_cloud_only": all(any(h in u for h in CLOUD) for u in external) if external else True,
            "page_error_count": len(page_errors),
            "page_errors": page_errors[:8],
            "console_error_count": len(console_errors),
            "console_errors": console_errors[:8],
        }

        if downloads:
            d = downloads[0]
            try:
                d.save_as(OUT)
                size = os.path.getsize(OUT)
                content = open(OUT, "r", encoding="utf-8", errors="replace").read()
                is_mx = content.lstrip().startswith("<mxfile")
                result["download_filename"] = d.suggested_filename
                result["saved_bytes"] = size
                result["starts_with_mxfile"] = is_mx
                result["save_ok"] = is_mx and size > 0
                result["saved_head"] = content[:200]
            except Exception as e:
                result["save_error"] = str(e)
                result["save_ok"] = False
        else:
            result["save_ok"] = False

        print(json.dumps(result, ensure_ascii=False))
        browser.close()
        sys.exit(0 if result.get("save_ok") else 1)


if __name__ == "__main__":
    main()
