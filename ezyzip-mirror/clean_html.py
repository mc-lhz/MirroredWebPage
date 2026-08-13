#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理入口 HTML：剥离外部资源引用，将 www.ezyzip.com 绝对地址改为本地相对。
处理 mirror/index.html 与 mirror/cn-asar.html（用户原始请求页面）。
"""
import re, os

MIRROR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
TARGETS = ["index.html", "cn-asar.html"]

SCRIPT_RE = re.compile(r'<script\b[^>]*\ssrc=https?://[^>\s]+(?:\s[^>]*)?></script>', re.I)
LINK_RE = re.compile(r'<link\b[^>]*\shref=https?://[^>\s]+(?:\s[^>]*)?>', re.I)
AD_RE = re.compile(
    r'<script>(?:(?!</script>).)*?(buysellads|googlefc|googletagmanager|ezyzip\.pro|cloudflare|ratings\.ezyzip|cdn4\.buysellads|fundingchoices).*?</script>',
    re.S | re.I)
BI = '<link rel="stylesheet" href="/assets/bootstrap-icons/bootstrap-icons.min.css">'


def clean(html):
    html = SCRIPT_RE.sub("", html)
    html = LINK_RE.sub("", html)
    html = AD_RE.sub("", html)
    html = html.replace("https://www.ezyzip.com", "").replace("http://www.ezyzip.com", "")
    if BI not in html:
        html = html.replace("<head>", "<head>\n" + BI + "\n", 1) if "<head>" in html else BI + "\n" + html
    return html


for name in TARGETS:
    path = os.path.join(MIRROR, name)
    if not os.path.exists(path):
        print("skip (missing):", name)
        continue
    html = clean(open(path, encoding="utf-8").read())
    open(path, "w", encoding="utf-8").write(html)
    ext = sorted(set(re.findall(r'(?:src|href)=["\']?https?://([^/"\'\s]+)', html)))
    print(name, "-> remaining external src/href hosts:", ext if ext else "(none)")
