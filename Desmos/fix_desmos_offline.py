#!/usr/bin/env python
# 让 Desmos 离线镜像支持 file:// 双击打开（不内联业务逻辑，保留 assets/ 外部）。
# 修复：
#  1) 绝对路径 /assets/ -> assets/；locale ftl 的 /api/v1/ -> api/v1/
#  2) 删除外链(desmos.com) 与本地缺失的 favicon/webmanifest
#  3) 内联 zh-CN.ftl 并拦截 fetch/XHR，避免 file:// 下 fetch 本地文件被浏览器拒绝
import os, re

D = os.path.dirname(os.path.abspath(__file__))
MARK = "<!-- DESMOS_OFFLINE_PATCH -->"


def patch(p, fn):
    s = open(p, encoding="utf-8", errors="replace").read()
    s2 = fn(s)
    if s2 != s:
        open(p, "w", encoding="utf-8").write(s2)
        print("patched:", os.path.relpath(p, D))
    else:
        print("unchanged:", os.path.relpath(p, D))


def html_fn(s):
    s = s.replace("/assets/", "assets/")
    s = re.sub(r'<link\b[^>]*\bhref=["\']https?://www\.desmos\.com/[^>]*>', "", s)
    s = re.sub(r'<link\b[^>]*\bhref=["\']//www\.desmos\.com/[^>]*>', "", s)
    s = re.sub(r'<link\b[^>]*\bhref=["\']assets/img/[^>]*>', "", s)
    s = re.sub(r'<link\b[^>]*\bhref=["\']assets/pwa/[^>]*>', "", s)
    return s


def css_fn(s):
    # 绝对路径 /assets/ -> assets/（HTML 引用保持相对）
    s = s.replace("/assets/", "assets/")
    # 本 CSS 文件自身位于 assets/build/ 下；其中 url("assets/build/...") 指向同目录兄弟资源。
    # 在 file:// 下若保留前缀会解析成 assets/build/assets/build/...（多一层），故去掉前缀，
    # 使其相对 CSS 文件位置解析为同目录资源。
    s = s.replace('url("assets/build/', 'url("')
    s = s.replace("url('assets/build/", "url('")
    s = s.replace("url(assets/build/", "url(")
    return s


def js_fn(s):
    s = s.replace("/assets/", "assets/")
    s = s.replace("/api/v1/", "api/v1/")
    return s


def inject_locale(s):
    if MARK in s:
        return s
    ftl = open(
        os.path.join(D, "api/v1/calculator/language/zh-CN.ftl"),
        encoding="utf-8",
        errors="replace",
    ).read()
    # 安全地嵌进 <script type=application/json>：仅转义 </script
    ftl_safe = ftl.replace("</script", "<\\/script")
    block = (
        MARK
        + """
<script type="application/json" id="desmos-loc-zh-CN">
"""
        + ftl_safe
        + """
</script>
<script>
(function(){
  function locContent(code){ if(code==='zh-CN'){var el=document.getElementById('desmos-loc-zh-CN');return el?el.textContent:null;} return null; }
  function isTracker(u){ return /bugsnag\\.com|googletagmanager\\.com|doubleclick\\.net|google-analytics\\.com|googleadservices\\.com|adservice\\.google\\.com|analytics|connect\\.facebook\\.net|scorecardresearch\\.com/.test(u); }
  function serve(url){ if(typeof url!=='string') return undefined; var m=/api\\/v1\\/calculator\\/language\\/([\\w-]+)\\.ftl/.exec(url); if(m){ var c=locContent(m[1]); return c!=null?c:'{}'; } if(isTracker(url)) return ''; return undefined; }
  if(window.fetch){ var _f=window.fetch.bind(window); window.fetch=function(u,o){ var b=serve(typeof u==='string'?u:(u&&u.url)); if(b!==undefined) return Promise.resolve(new Response(b,{status:200,headers:{'Content-Type':'application/json'}})); return _f(u,o); }; }
  if(navigator.sendBeacon){ navigator.sendBeacon=function(){ return true; }; }
  var _open=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(m,u){ this.__loc=serve(typeof u==='string'?u:String(u)); return _open.apply(this,arguments); };
  var _send=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send=function(){ if(this.__loc!==undefined){ var self=this,d=this.__loc; setTimeout(function(){ try{Object.defineProperty(self,'status',{value:200,configurable:true});Object.defineProperty(self,'statusText',{value:'OK',configurable:true});Object.defineProperty(self,'responseText',{value:d,configurable:true});Object.defineProperty(self,'response',{value:d,configurable:true});}catch(e){} self.dispatchEvent(new Event('load')); },0); return; } return _send.apply(this,arguments); };
})();
</script>
"""
    )
    # 插到 </head> 之前（head 内脚本先于 body 的 bundle 执行）
    if "</head>" in s:
        return s.replace("</head>", block + "</head>", 1)
    return s + block


patch(os.path.join(D, "index.html"), html_fn)
css = os.path.join(
    D,
    "assets",
    "build",
    "shared_calculator_desktop-fbf7dbc3b53aa9223fa4dc43f6b9ffc8d2365a02.css",
)
js = os.path.join(
    D,
    "assets",
    "build",
    "shared_calculator_desktop-de76a17681fb6861c6967714faf61f785768c508.js",
)
if os.path.exists(css):
    patch(css, css_fn)
if os.path.exists(js):
    patch(js, js_fn)
# locale 注入（整体注入一次）
hp = os.path.join(D, "index.html")
hs = open(hp, encoding="utf-8", errors="replace").read()
hs2 = inject_locale(hs)
if hs2 != hs:
    open(hp, "w", encoding="utf-8").write(hs2)
    print("patched: index.html (locale inline)")
print("done")
