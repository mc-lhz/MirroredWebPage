#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""针对 cn-asar.html（用户原始请求页面）的断网验证：零外部请求 + 离线 ASAR worker 解析成功。"""
import os, sys, subprocess, time
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8139
BASE = "http://127.0.0.1:%d/cn-asar.html" % PORT
SERVE = os.path.join(HERE, "serve.py")
TEST_ASAR = os.path.join(HERE, "test.asar")

def start_serve():
    p = subprocess.Popen([sys.executable, SERVE, str(PORT)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:%d/" % PORT, timeout=1)
            return p
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("serve.py 未启动")

def run_once(page):
    ext = {"count": 0}
    asar_logs = []
    def on_route(route):
        u = route.request.url
        if not u.startswith("http://127.0.0.1") and not u.startswith("data:"):
            ext["count"] += 1
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
            # 忽略 ezyzip 自带的 7z 格式探测器良性警告（对任意小文件都会触发，与离线无关）
            if "Buffer might be too small for some signatures" in m.text:
                return
            console_errors.append(m.text)
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("console", _console)
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("input[type=file], #app, main", timeout=20000)
    page.wait_for_timeout(2500)
    inps = page.query_selector_all("input[type=file]")
    inp = page.query_selector("#extractFile") or next((e for e in inps if not e.get_attribute("webkitdirectory")), inps[0] if inps else None)
    parsed = False
    if inp:
        try:
            inp.set_input_files(TEST_ASAR)
            page.wait_for_timeout(4000)
            parsed = any("file list built" in l for l in asar_logs)
        except Exception:
            pass
    return {"external": ext["count"], "page_error": len(page_errors),
            "console_error": len(console_errors), "asar_parsed": parsed}

def main():
    proc = start_serve()
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for i in range(3):
                ctx = browser.new_context()
                r = run_once(ctx.new_page())
                results.append(r)
                print("round", i + 1, r)
                ctx.close()
            browser.close()
    finally:
        proc.terminate()
    ok = all(r["external"] == 0 and r["page_error"] == 0 and r["console_error"] == 0 and r["asar_parsed"] for r in results)
    print("\nCN_FIRM_OK" if ok else "\nCN_NOT_OK", results)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
