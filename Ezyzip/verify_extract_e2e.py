#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端证明 ezyzip 的 ASAR 提取在离线镜像下真实可用：
直接实例化 ezyzip 真实的 asar-extract-worker，喂入 test.asar，
等待 fileList 消息，再请求 extractFile('hello.txt')，取回 blob 字节比对。
全程经 127.0.0.1 本地 serve，零外部请求。
"""
import os, sys, subprocess, time, base64
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8138
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

def main():
    asar_b64 = base64.b64encode(open(TEST_ASAR, "rb").read()).decode()
    proc = start_serve()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_context().new_page()
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            # 在页面上下文里直接驱动真实 worker
            result = page.evaluate("""async (b64) => {
                const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
                const file = new File([bytes], "test.asar", {type:"application/octet-stream"});
                const w = new Worker("/assets/workers/asar-extract-worker-aa430551.js");
                const msgs = [];
                const waitMsg = (type) => new Promise((res, rej) => {
                    const h = (e) => { if (e.data.type === type) { w.removeEventListener('message', h); res(e.data); } };
                    w.addEventListener('message', h);
                    setTimeout(() => rej(new Error('timeout waiting '+type)), 8000);
                });
                const fileListP = waitMsg('fileList');
                w.postMessage({method:'setArchiveFile', archiveFile: file});
                const fl = await fileListP;
                const extractP = waitMsg('extractFile');
                w.postMessage({method:'extractFile', filename:'hello.txt'});
                const ex = await extractP;
                const buf = await ex.file.arrayBuffer();
                const arr = Array.from(new Uint8Array(buf));
                w.terminate();
                return { fileList: fl.fileList.map(f=>f.fullpath), bytes: arr };
            }""", asar_b64)

            browser.close()
            names = result["fileList"]
            content = bytes(result["bytes"]).decode("utf-8", "replace")
            print("file list:", names)
            print("extracted 'hello.txt' bytes:", repr(content))
            ok = ("hello.txt" in names) and (content == "hello asar\n")
            print("E2E_OK" if ok else "E2E_FAIL")
            sys.exit(0 if ok else 1)
    finally:
        proc.terminate()

if __name__ == "__main__":
    main()
