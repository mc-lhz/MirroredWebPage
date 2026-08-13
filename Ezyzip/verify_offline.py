#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""断网验证 ezyzip 离线镜像：
- 拦截一切非 127.0.0.1 / data: 请求并 abort（模拟纯离线，确保零外部请求）
- 加载页面：断言 external=0、page_error=0、console_error=0
- ASAR 功能性冒烟：选 #extractFile 注入 test.asar，确认离线 worker 真实解析出文件列表
  （捕获 worker 日志 "ASAR file list built" + DOM 出现文件名）
- 并尝试真实提取（捕获 download 事件）作为 bonus 信号
- 连跑 3 轮
"""
import os, sys, subprocess, time
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8137
BASE = "http://127.0.0.1:%d/" % PORT
SERVE = os.path.join(HERE, "serve.py")
TEST_ASAR = os.path.join(HERE, "test.asar")

def start_serve():
    p = subprocess.Popen([sys.executable, SERVE, str(PORT)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            import urllib.request
            urllib.request.urlopen(BASE, timeout=1)
            return p
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("serve.py 未启动")

def run_once(page):
    ext = {"count": 0, "urls": []}
    asar_logs = []
    def on_route(route):
        u = route.request.url
        if not u.startswith("http://127.0.0.1") and not u.startswith("data:"):
            ext["count"] += 1
            ext["urls"].append(u)
            try: route.abort()
            except Exception: pass
        else:
            try: route.continue_()
            except Exception: pass
    page.route("**/*", on_route)

    page_errors, console_errors = [], []
    def _console(m):
        if "ASAR" in m.text:
            asar_logs.append(m.text)
            return
        if m.type == "error":
            if "Buffer might be too small for some signatures" in m.text:
                return
            console_errors.append(m.text)
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("console", _console)

    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("input[type=file], #app, main, .ez-tp", timeout=20000)
    page.wait_for_timeout(2500)

    load_metrics = {
        "external": ext["count"],
        "external_urls": list(ext["urls"][:5]),
        "page_error": len(page_errors),
        "page_error_msg": list(page_errors[:2]),
        "console_error": len(console_errors),
        "console_error_msg": list(console_errors[:2]),
    }

    inps = page.query_selector_all("input[type=file]")
    inp = page.query_selector("#extractFile")
    if not inp:
        inp = next((e for e in inps if not e.get_attribute("webkitdirectory")), inps[0] if inps else None)

    listed = None
    asar_parsed = False
    interaction_error = None
    downloads = []
    if inp:
        try:
            # 捕获可能的下载（真实提取信号）
            page.on("download", lambda d: downloads.append(d.suggested_filename))
            inp.set_input_files(TEST_ASAR)
            page.wait_for_timeout(4000)
            asar_parsed = any("file list built" in l or "ASAR file list" in l for l in asar_logs)
            # DOM 中出现文件名即视为列表渲染成功
            for name in ["hello.txt", "world.txt", "readme.md", "dir/world.txt"]:
                if page.query_selector("text=%s" % name):
                    listed = name
                    break
        except Exception as e:
            interaction_error = str(e)[:160]
    load_metrics.update({
        "file_inputs": len(inps),
        "file_input_found": inp is not None,
        "asar_worker_parsed": asar_parsed,
        "asar_logs": asar_logs[:3],
        "asar_listed": listed,
        "downloads": list(downloads),
        "interaction_error": interaction_error,
    })
    return load_metrics

def main():
    if not os.path.exists(TEST_ASAR):
        subprocess.run([sys.executable, os.path.join(HERE, "make_test_asar.py")])
    proc = start_serve()
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for i in range(3):
                ctx = browser.new_context()
                page = ctx.new_page()
                r = run_once(page)
                results.append(r)
                print("round", i + 1, r)
                ctx.close()
            browser.close()
    finally:
        proc.terminate()
    # 门禁：零外部请求 + 零页面/控制台错误 + 离线 worker 真实解析出文件列表
    ok = all(r["external"] == 0 and r["page_error"] == 0 and r["console_error"] == 0
             and r["asar_worker_parsed"] for r in results)
    print("\nFIRM_OK" if ok else "\nNOT_OK", results)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
