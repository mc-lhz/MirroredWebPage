#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 mirror 内所有 html/css，补抓缺失的本地 /... 资源（图片/字体等），确保离线无 404 噪音。"""
import os, re, subprocess

BASE = "https://www.ezyzip.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 兼容无引号属性值（ezyzip 原站 src/href 多为无引号）
REF_RE = re.compile(r'(?:src|href|srcset|poster|content|data-src)=\s*["\']?([^"\'>\s]+\.[a-z0-9]+)', re.I)
CSS_URL_RE = re.compile(r'url\(\s*["\']?(/[^"\'()?]+\.[a-z0-9]+)')

def fetch(path):
    url = BASE + path
    last = None
    for _ in range(3):
        try:
            out = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "30", url], capture_output=True)
            if out.returncode == 0 and out.stdout:
                return out.stdout
            last = "rc=%d" % out.returncode
        except Exception as e:
            last = str(e)
    raise RuntimeError("%s: %s" % (path, last))

missing = 0
for root, _, files in os.walk(OUT):
    for fn in files:
        if not fn.endswith((".html", ".htm", ".css")):
            continue
        fp = os.path.join(root, fn)
        try:
            t = open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        refs = set(REF_RE.findall(t)) | set(CSS_URL_RE.findall(t))
        for r in refs:
            r_clean = re.sub(r"[?#].*$", "", r)  # 去掉 ?缓存串/#片段
            local = OUT + r_clean
            if os.path.exists(local):
                continue
            try:
                data = fetch(r_clean)
                os.makedirs(os.path.dirname(local), exist_ok=True)
                open(local, "wb").write(data)
                missing += 1
                print("  fetched", r_clean, len(data), "B")
            except Exception as e:
                print("  SKIP (404?)", r_clean, str(e)[:60])

print("fetched missing local assets:", missing)
