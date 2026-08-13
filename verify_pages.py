# -*- coding: utf-8 -*-
"""
verify_pages.py — 统一无头浏览器离线可用性验证（7 个镜像页面）。

做法（对齐 Mirror 离线镜像方法论）：
- 每个页面用 `python -m http.server` 以「应用根目录」为 Web 根起本地服务（127.0.0.1）。
  * Drawio/Ezyzip 的 Web 根 = <Dir>/mirror（与它们 serve.py 行为一致）
  * Excalidraw/Mermaid/Reactflow/Tldraw 的 Web 根 = <Dir>/dist
  * ToolhelperJson 的 Web 根 = <Dir>
- Playwright 拦截一切「非 127.0.0.1 / 非 file: / 非 data: / 非 blob:」的请求并 abort，
  统计外部请求数（离线门禁：external == 0）。
- 断言：external==0 且 pageerror==0 且 应用启动标记就绪 且 关键画布/容器可见。
- Excalidraw 额外做真实鼠标绘制，验证可交互。
- 每页跑 ROUNDS 轮（默认 2），避免偶发竞态。

结果写入 verify_pages_report.json，并打印汇总表。
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

VENV_PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
ROOT = Path(__file__).parent
ROUNDS = 2

PAGES = [
    {"name": "Drawio", "dir": "Drawio/mirror",
     "boot": "() => !!document.querySelector('.geDiagramContainer, #graph, .geEditor')",
     "surface": ".geEditor, .geDiagramContainer, #graph"},
    {"name": "Excalidraw", "dir": "Excalidraw/dist",
     "boot": "() => !!(window.__excalidraw && window.__excalidraw.getSceneElements)",
     "surface": "canvas.excalidraw__canvas", "interact": "excalidraw"},
    {"name": "Ezyzip", "dir": "Ezyzip/mirror",
     "boot": "() => !!document.querySelector('input[type=file], #root, .dropzone, .btn, main, button')",
     "surface": "main, #app, .app, button, .dropzone, input[type=file]"},
    {"name": "Mermaid", "dir": "Mermaid/dist",
     "boot": "() => { const r=document.querySelector('#root'); return !!((r && r.childElementCount>0) || document.querySelector('svg, .mermaid')); }",
     "surface": "#root"},
    {"name": "Reactflow", "dir": "Reactflow/dist",
     "boot": "() => !!document.querySelector('.react-flow')",
     "surface": ".react-flow"},
    {"name": "Tldraw", "dir": "Tldraw/dist",
     "boot": "() => !!document.querySelector('.tl-container, canvas')",
     "surface": ".tl-container, canvas"},
    {"name": "ToolhelperJson", "dir": "ToolhelperJson",
     "boot": "() => !!document.querySelector('textarea, form, #root, .container')",
     "surface": "textarea, form, #root"},
]


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_server(web_root):
    port = free_port()
    proc = subprocess.Popen(
        [VENV_PY, "-m", "http.server", str(port), "--bind", "127.0.0.1",
         "--directory", str(web_root)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = "http://127.0.0.1:%d/" % port
    # wait until server answers
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return proc, port, url
        except OSError:
            time.sleep(0.1)
    return proc, port, url


def stop_server(proc):
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_page(page, pw):
    web_root = ROOT / page["dir"]
    if not web_root.exists():
        return {"ok": False, "reason": "web root missing: %s" % web_root}
    proc, port, url = start_server(web_root)
    external, page_errors, console_errors = [], [], []
    try:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page_obj = ctx.new_page()

        def on_route(route):
            u = route.request.url
            if u.startswith(("file://", "data:", "blob:", "about:")):
                return route.continue_()
            if u.startswith(("http://", "https://")):
                host = urlparse(u).hostname or ""
                if host in ("127.0.0.1", "localhost", "[::1]"):
                    return route.continue_()
                external.append(u)
                return route.abort()
            return route.continue_()

        page_obj.route("**/*", on_route)
        page_obj.on("pageerror", lambda e: page_errors.append(str(e)))
        page_obj.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        try:
            page_obj.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            return {"ok": False, "reason": "goto failed: %s" % e,
                    "external": external, "page_errors": page_errors,
                    "console_errors": console_errors}

        boot_ok = False
        try:
            page_obj.wait_for_function(page["boot"], timeout=45000)
            boot_ok = True
        except Exception:
            boot_ok = False

        surface_ok = False
        surface_box = None
        try:
            # 遍历所有候选元素（逗号选择器），任一可见(尺寸>0)即通过；
            # 不能用 .first —— 隐藏的 file input 可能排在可见容器之前导致误判
            for loc in page_obj.query_selector_all(page["surface"]):
                try:
                    box = loc.bounding_box()
                except Exception:
                    continue
                if box and box["width"] > 0 and box["height"] > 0:
                    surface_ok = True
                    surface_box = box
                    break
        except Exception:
            surface_ok = False

        interact_info = None
        if page.get("interact") == "excalidraw" and boot_ok and surface_ok:
            try:
                page_obj.evaluate("window.__excalidraw.setActiveTool({type:'rectangle'})")
                box = surface_box
                page_obj.mouse.click(box["x"] + 640, box["y"] + 400)
                page_obj.wait_for_timeout(300)
                page_obj.mouse.move(box["x"] + 450, box["y"] + 300)
                page_obj.mouse.down()
                page_obj.mouse.move(box["x"] + 780, box["y"] + 520, steps=12)
                page_obj.mouse.up()
                page_obj.wait_for_timeout(600)
                count = page_obj.evaluate("window.__excalidraw.getSceneElements().length")
                interact_info = {"drew_elements": count}
            except Exception as e:
                interact_info = {"error": str(e)}

        # 多等一会，捕捉 draw.io 等应用「加载完成后才动态注入」的云集成 SDK 外部请求
        page_obj.wait_for_timeout(4000)
        browser.close()
        ok = (len(external) == 0 and len(page_errors) == 0 and boot_ok and surface_ok)
        return {
            "ok": ok, "boot_ok": boot_ok, "surface_ok": surface_ok,
            "external": external, "external_count": len(external),
            "page_errors": page_errors, "page_error_count": len(page_errors),
            "console_errors": console_errors, "console_error_count": len(console_errors),
            "interact": interact_info,
        }
    finally:
        stop_server(proc)


def main():
    from playwright.sync_api import sync_playwright
    report = {"pages": {}}
    with sync_playwright() as pw:
        for page in PAGES:
            rounds = []
            all_ok = True
            for r in range(ROUNDS):
                res = run_page(page, pw)
                rounds.append(res)
                if not res.get("ok"):
                    all_ok = False
            report["pages"][page["name"]] = {
                "dir": page["dir"],
                "all_ok": all_ok,
                "rounds": rounds,
            }
    # summary
    print("\n=== 离线可用性验证汇总 (ROUNDS=%d) ===" % ROUNDS)
    print("%-14s %-6s %-8s %-8s %-8s" % ("PAGE", "PASS", "EXT", "PERR", "CONERR"))
    for name, info in report["pages"].items():
        ext = sum(x.get("external_count", 0) for x in info["rounds"])
        perr = sum(x.get("page_error_count", 0) for x in info["rounds"])
        cerr = sum(x.get("console_error_count", 0) for x in info["rounds"])
        print("%-14s %-6s %-8d %-8d %-8d" % (name, "YES" if info["all_ok"] else "NO", ext, perr, cerr))
    (ROOT / "verify_pages_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nreport -> verify_pages_report.json")
    overall = all(v["all_ok"] for v in report["pages"].values())
    print("OVERALL: %s" % ("ALL_PASS" if overall else "HAS_FAIL"))


if __name__ == "__main__":
    main()
