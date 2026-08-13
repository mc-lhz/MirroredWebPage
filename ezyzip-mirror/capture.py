#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 ezyzip asar 页面为离线镜像（本地资源图递归下载）。
产出：ezyzip-mirror/mirror/ 下完整可服务目录。
入口 HTML 使用服务端原始响应（非渲染后 DOM）。
"""
import os, re, sys, ssl, subprocess, urllib.request
from urllib.parse import urljoin

BASE = "https://www.ezyzip.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def fetch(path):
    """用 curl 取字节（urllib 在此网络下偶发读取超时，curl 稳定）。失败抛 RuntimeError。"""
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        url = urljoin(BASE + "/", path.lstrip("/"))
    last = None
    for attempt in range(3):
        try:
            out = subprocess.run(
                ["curl", "-sL", "-A", UA, "--max-time", "30", url],
                capture_output=True,
            )
            if out.returncode == 0 and out.stdout:
                return out.stdout
            last = "rc=%d len=%d" % (out.returncode, len(out.stdout))
        except Exception as e:
            last = str(e)
    raise RuntimeError("fetch failed %s: %s" % (path, last))

def save(path, data):
    rel = path.lstrip("/")
    full = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)

# 通用：任意文件中出现的本地资源路径（/开头，带已知扩展名）
ASSET_RE = re.compile(r"""(?:src|href)=\s*["'](/[^"'?]+)["']""")
CSS_URL_RE = re.compile(r"""url\(\s*["']?(/[^"')?]+)["']?\s*\)""")
# JS 相对导入（./X.js 或 ../X.js）
JS_REL_RE = re.compile(r"""(?:import|from)\s*["'](\.{1,2}/[^"']+)["']""")
JS_DYN_RE = re.compile(r"""import\(\s*["'](\.{1,2}/[^"']+)["']""")

visited = set()
queue = []

def enqueue_local_path(p):
    if p and p not in visited:
        queue.append(p)

def enqueue_js_rel(imp, base_path):
    # base_path 形如 /assets/index-2a01b83e.js
    d = os.path.dirname(base_path)
    np = os.path.normpath(os.path.join(d, imp)).replace("\\", "/")
    if not np.startswith("/"):
        np = "/" + np
    enqueue_local_path(np)

# 1) 入口 HTML（原始响应）
print("[1] fetch entry HTML")
html = fetch("/cn-asar.html")
save("cn-asar.html", html)
text = html.decode("utf-8", "replace")
# 入口同时作为 index.html（方便 serve.py 根路径打开）
save("index.html", html)
for m in ASSET_RE.findall(text):
    enqueue_local_path(m.split("?")[0])
for m in CSS_URL_RE.findall(text):
    enqueue_local_path(m.split("?")[0])

# 2) 已知经典脚本 / CSS（防止 HTML 里没显式写出）
KNOWN = [
    "/assets/zipjs/v2.8.34/zip.min.js",
    "/assets/utf8/utf8.js",
    "/assets/js/app/filesize.min.js",
    "/assets/styles/5.3/js/bootstrap.bundle.min.js",
    "/assets/styles/5.3/ezyzip.min.css",
    "/assets/style-c3617bd9.css",
    "/assets/styles/fonts/Lato-Regular.woff2",
    "/assets/styles/fonts/Lato-Bold.woff2",
    "/assets/styles/fonts/Lato-Light.woff2",
    "/assets/styles/fonts/Lato-Regular.ttf",
    "/assets/styles/fonts/Lato-Bold.ttf",
    "/assets/styles/fonts/Lato-Light.ttf",
]
for k in KNOWN:
    enqueue_local_path(k)

# 3) 主模块入口（BFS 模块图）
enqueue_local_path("/assets/index-2a01b83e.js")

# 4) 主模块里已见到的所有 chunk 文件名，直接入队（双保险）
for m in re.findall(r"[A-Za-z]+-[0-9a-f]{8}\.js", text):
    enqueue_local_path("/assets/" + m)

fail = []
count = 0
print("[2] BFS local asset graph ...")
while queue:
    p = queue.pop(0)
    if p in visited:
        continue
    visited.add(p)
    try:
        data = fetch(p)
    except Exception as e:
        fail.append((p, str(e)))
        print("  FAIL", p, str(e)[:80])
        continue
    save(p, data)
    count += 1
    ext = os.path.splitext(p)[1].lower()
    try:
        t = data.decode("utf-8", "replace")
    except Exception:
        t = ""
    if ext == ".js" or "javascript" in (p.lower()):
        for rel in JS_REL_RE.findall(t) + JS_DYN_RE.findall(t):
            enqueue_js_rel(rel, p)
        # 也抓字符串里出现的 /assets/X.js（部分拼接场景）
        for am in re.findall(r"""(["'])(/assets/[^"']+\.js)\1""", t):
            enqueue_local_path(am[1])
    if ext == ".css":
        for u in CSS_URL_RE.findall(t):
            enqueue_local_path(u.split("?")[0])
        for a in ASSET_RE.findall(t):
            enqueue_local_path(a.split("?")[0])
    if ext in (".html", ".htm"):
        for a in ASSET_RE.findall(t):
            enqueue_local_path(a.split("?")[0])
        for u in CSS_URL_RE.findall(t):
            enqueue_local_path(u.split("?")[0])

print(f"[done] saved {count} local files; failures: {len(fail)}")
for p, e in fail:
    print("  FAIL", p, e)

# 5) bootstrap-icons（来自 jsdelivr）：本地化，保留图标
print("[3] mirror bootstrap-icons locally")
try:
    bcss = fetch("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css")
    save("assets/bootstrap-icons/bootstrap-icons.min.css", bcss)
    # 找字体文件
    for fm in re.findall(r"""url\(\s*["']?([^"')]+\.woff2?)["']?\s*\)""", bcss.decode("utf-8", "replace")):
        furl = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/" + fm.lstrip("./")
        fb = fetch(furl)
        # 保持与 css 内相对引用一致：存到 assets/bootstrap-icons/fonts/
        save("assets/bootstrap-icons/fonts/" + os.path.basename(fm), fb)
    print("  bootstrap-icons OK")
except Exception as e:
    print("  bootstrap-icons FAIL", e)
