#!/usr/bin/env node
/**
 * build-geogebra-singlefile.mjs
 *
 * 把 Geogebra/ 镜像（GWT web3d 应用）打成一个自包含的单文件 HTML：
 *   - 内联 index.html 里的全部 CSS（字体在镜像中已是 base64 data URI）
 *   - 内联 GWT permutation（bootstrap）+ 全部 deferredjs 分片
 *   - 内联语言包，启动时直接使用，不再发脚本请求
 *   - 剥离 Service Worker / Google Analytics 等联网代码
 *   - 用 Document.createElement 拦截器把 GWT 原本要发起的 <script src>
 *     重定向到内存中的 blob: URL，从而完整保留 GWT 自己的异步加载时序
 *
 * 用法：
 *   node tools/build-geogebra-singlefile.mjs [--out dist/geogebra-single.html]
 *                                            [--lang zh-CN] [--no-xhr-guard] [--check] [--quiet]
 *
 * 无第三方依赖，只用 Node >= 18。
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const GEO = path.join(ROOT, 'Geogebra');

// ---------------------------------------------------------------- args

function parseArgs(argv) {
  const out = {
    out: path.join(ROOT, 'dist', 'geogebra-single.html'),
    lang: null,
    xhrGuard: true,
    check: false,
    quiet: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--out') out.out = path.resolve(ROOT, argv[++i]);
    else if (a === '--lang') out.lang = argv[++i];
    else if (a === '--no-xhr-guard') out.xhrGuard = false;
    else if (a === '--check') out.check = true;
    else if (a === '--quiet') out.quiet = true;
    else if (a === '--help' || a === '-h') {
      console.log('usage: node tools/build-geogebra-singlefile.mjs [--out FILE] [--lang zh-CN] [--no-xhr-guard] [--check] [--quiet]');
      process.exit(0);
    } else throw new Error(`unknown option: ${a}`);
  }
  return out;
}

const opts = parseArgs(process.argv.slice(2));
const log = (...m) => !opts.quiet && console.log(...m);
const mustExist = (p, hint) => {
  if (!fs.existsSync(p)) throw new Error(`缺少文件: ${path.relative(ROOT, p)}${hint ? ` (${hint})` : ''}`);
  return p;
};

/** 把任意 JS 源码安全地塞进 JS 字符串字面量（不会提前关掉外层 <script>） */
function jsLiteral(src) {
  return JSON.stringify(src)
    .replace(/<\//g, '<\\/')
    .replace(/<!--/g, '\\u003C!--')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}

// ---------------------------------------------------------------- 1. 读取镜像

let html = fs.readFileSync(mustExist(path.join(GEO, 'index.html'), 'GeoGebra 镜像入口'), 'utf8');

const cfg = {
  latestVersion: /var\s+latestVersion\s*=\s*"([^"]+)"/.exec(html)?.[1],
  module: /var\s+module\s*=\s*"([^"]+)"/.exec(html)?.[1],
  codebase: /var\s+codebase\s*=\s*"([^"]+)"/.exec(html)?.[1],
};
for (const [k, v] of Object.entries(cfg)) if (!v) throw new Error(`无法从 index.html 解析 ${k}`);
log(`GeoGebra ${cfg.latestVersion} / module=${cfg.module} / codebase=${cfg.codebase}`);

const web3dDir = path.join(GEO, cfg.codebase, cfg.module);
const nocachePath = mustExist(path.join(web3dDir, `${cfg.module}.nocache.js`), 'GWT nocache');
const nocacheText = fs.readFileSync(nocachePath, 'utf8');
const strongName = /[0-9A-F]{32}/.exec(nocacheText.slice(nocacheText.indexOf('clear.cache.gif')))?.[0];
if (!strongName) throw new Error('无法从 nocache.js 解析 strong name');
const permutationPath = mustExist(path.join(web3dDir, `${strongName}.cache.js`), 'GWT permutation / bootstrap');

const deferredDir = path.join(web3dDir, 'deferredjs', strongName);
const fragments = fs
  .readdirSync(mustExist(deferredDir, 'GWT deferredjs'))
  .filter((f) => f.endsWith('.cache.js'))
  .map((f) => ({ n: parseInt(f, 10), file: f }))
  .sort((a, b) => a.n - b.n);
if (!fragments.length) throw new Error('deferredjs 里没有 .cache.js 分片');
log(`permutation=${strongName} fragments=${fragments.map((f) => f.n).join(',')}`);

const cssFiles = ['fonts.css', 'greek-font.css']
  .map((f) => path.join(GEO, cfg.codebase, 'css', f))
  .filter((p) => fs.existsSync(p));

const langDir = path.join(GEO, 'apps', cfg.latestVersion, cfg.module, 'js');
const langFiles = fs.existsSync(langDir)
  ? fs
      .readdirSync(langDir)
      .map((f) => /^properties_keys_(.+)\.js$/.exec(f))
      .filter(Boolean)
      .map((m) => ({ lang: m[1], file: path.join(langDir, `properties_keys_${m[1]}.js`) }))
  : [];
if (!langFiles.length) throw new Error(`找不到语言包: Geogebra/apps/${cfg.latestVersion}/${cfg.module}/js/properties_keys_*.js`);
const lang = opts.lang ?? langFiles[0].lang;
const langFile = langFiles.find((l) => l.lang === lang);
if (!langFile) throw new Error(`镜像里没有 ${lang} 语言包（可选: ${langFiles.map((l) => l.lang).join(', ')}）`);
log(`lang=${lang}`);

// ---------------------------------------------------------------- 2. 资源表

const sources = new Map();
sources.set('nocache', fs.readFileSync(nocachePath));
sources.set('permutation', fs.readFileSync(permutationPath));
for (const f of fragments) sources.set(`fragment:${f.n}`, fs.readFileSync(path.join(deferredDir, f.file)));
sources.set(`l10n:${lang}`, fs.readFileSync(langFile.file));
// GeoGebra 启动时会自己注入 <link class="ggw_resource"> 去加载字体 CSS，并且会等它们加载完
for (const p of cssFiles) sources.set(`css:${path.basename(p)}`, fs.readFileSync(p));

let totalBytes = 0;
for (const [k, buf] of sources) {
  totalBytes += buf.length;
  log(`  ${k.padEnd(18)} ${(buf.length / 1048576).toFixed(2)} MB  sha256:${crypto.createHash('sha256').update(buf).digest('hex').slice(0, 16)}`);
}
log(`JS 合计 ${(totalBytes / 1048576).toFixed(2)} MB`);

// ---------------------------------------------------------------- 3. 运行时 shim

const shim = `(function () {
  'use strict';
  var LOG = '[geogebra-singlefile] ';
  var MODULE = ${JSON.stringify(cfg.module)};
  var LANG = ${JSON.stringify(lang)};
  var XHR_GUARD = ${JSON.stringify(opts.xhrGuard)};

  var SRC = Object.create(null);
${[...sources].map(([k, buf]) => `  SRC[${JSON.stringify(k)}] = ${jsLiteral(buf.toString('utf8'))};`).join('\n')}

  var blobCache = Object.create(null);

  function mimeOf(key) {
    return key.slice(0, 4) === 'css:' ? 'text/css' : 'text/javascript';
  }

  function toUrl(key) {
    if (blobCache[key]) return blobCache[key];
    var mime = mimeOf(key);
    var url = null;
    try {
      url = URL.createObjectURL(new Blob([SRC[key]], { type: mime }));
    } catch (e) {
      try { url = 'data:' + mime + ';charset=utf-8,' + encodeURIComponent(SRC[key]); } catch (e2) { url = null; }
    }
    if (url) blobCache[key] = url;
    return url;
  }

  // GWT / GeoGebra 真实会请求的 URL -> SRC 里的键
  function resolve(url) {
    if (typeof url !== 'string') return null;
    var u = url.split('#')[0].split('?')[0];
    var frag = /deferredjs\\/[^/]+\\/(\\d+)\\.cache\\.js$/.exec(u);
    if (frag) {
      var key = 'fragment:' + frag[1];
      return key in SRC ? key : null;
    }
    var base = u.slice(u.lastIndexOf('/') + 1);
    if (/^[0-9A-F]{32}\\.cache\\.js$/.test(base)) return 'permutation';
    if (base === MODULE + '.nocache.js') return 'nocache';
    var l10n = /^properties_keys_(.+)\\.js$/.exec(base);
    if (l10n) {
      var lkey = 'l10n:' + l10n[1];
      return lkey in SRC ? lkey : null;
    }
    var css = /\\/css\\/([^/]+\\.css)$/.exec(u) || /\\/(.+\\.css)$/.exec(u);
    if (css) {
      var ckey = 'css:' + css[1];
      return ckey in SRC ? ckey : null;
    }
    return null;
  }

  // 拦截 <script src>：GWT 仍按原时序异步加载，只是数据来自内存
  function install(realm) {
    var proto = realm && realm.Document && realm.Document.prototype;
    if (!proto || proto.__ggbScriptHooked) return;
    proto.__ggbScriptHooked = true;
    var nativeCreate = proto.createElement;
    proto.createElement = function (tag) {
      var el = nativeCreate.call(this, tag);
      var lower = String(tag).toLowerCase();
      // GWT 的脚本、GeoGebra 注入的字体样式表，都要从内存供给
      if (lower !== 'script' && lower !== 'link') return el;
      var attr = lower === 'script' ? 'src' : 'href';
      var nativeSet = el.setAttribute.bind(el);
      function rewrite(value) {
        var key = resolve(value);
        if (!key) return value;
        var url = toUrl(key);
        if (!url) return value;
        // blob: 在个别环境（隐私模式 / 严格 file:// 策略）可能被拒，失败后退回 data:
        if (url.slice(0, 5) === 'blob:' && el.addEventListener) {
          el.addEventListener(
            'error',
            function () {
              console.warn(LOG + 'blob: 加载失败，改用 data: 回退 ' + key);
              nativeSet(attr, 'data:' + mimeOf(key) + ';charset=utf-8,' + encodeURIComponent(SRC[key]));
            },
            { once: true }
          );
        }
        return url;
      }
      el.setAttribute = function (name, value) {
        if (String(name).toLowerCase() === attr) value = rewrite(value);
        return nativeSet(name, value);
      };
      try {
        Object.defineProperty(el, attr, {
          configurable: true,
          get: function () { return el.getAttribute(attr); },
          set: function (value) { nativeSet(attr, rewrite(value)); }
        });
      } catch (e) {}
      return el;
    };
  }

  install(window);

  // GWT 把 permutation 和 deferredjs 加载到它自己创建的隐藏 iframe 里。
  // 每个 iframe 是独立 realm，Document.prototype 不是同一个对象，必须逐个 realm 打补丁。
  function hookIframe(node) {
    try {
      if (node && node.tagName === 'IFRAME') install(node.contentWindow);
    } catch (e) {}
  }
  ['appendChild', 'insertBefore', 'replaceChild'].forEach(function (m) {
    var native = Node.prototype[m];
    Node.prototype[m] = function (node) {
      var res = native.apply(this, arguments);
      hookIframe(node);
      return res;
    };
  });
  ['append', 'prepend', 'before', 'after', 'replaceWith'].forEach(function (m) {
    if (!Element.prototype[m]) return;
    var native = Element.prototype[m];
    Element.prototype[m] = function (node) {
      var res = native.apply(this, arguments);
      hookIframe(node);
      return res;
    };
  });

  // 镜像里没有的静态资源（geogebra_macro.xml / structure.json / 其它语言包 / CDN 字体）
  // 直接快速失败，避免 file:// 下长时间挂起
  if (XHR_GUARD) {
    var nativeOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url) {
      var pathname = '';
      try { pathname = new URL(url, location.href).pathname; } catch (e) {}
      if (pathname && !resolve(pathname) && /\\.(xml|json|gwt|woff2?|ttf|css)$/i.test(pathname)) {
        console.warn(LOG + 'offline: 未内联的请求被拦截 ' + pathname);
        var self = this;
        if (!self.__ggbOffline) {
          self.__ggbOffline = true;
          setTimeout(function () {
            ['readyState', 'status', 'responseText', 'response'].forEach(function (p) {
              try { Object.defineProperty(self, p, { value: p === 'readyState' ? 4 : p === 'status' ? 404 : '', configurable: true }); } catch (e) {}
            });
            try { self.onreadystatechange && self.onreadystatechange(); } catch (e) {}
            for (var i = 0; i < 3; i++) {
              try { self.dispatchEvent(new Event(['readystatechange', 'error', 'load'][i])); } catch (e) {}
            }
          }, 0);
        }
        return;
      }
      return nativeOpen.apply(this, arguments);
    };
  }

  // 语言包：立即执行内联的那一份，启动流程直接用它
  try { (0, eval)(SRC['l10n:' + LANG]); } catch (e) { console.warn(LOG + '语言包执行失败: ' + e); }
  try {
    var kv = window.__GGB__keysVar || {};
    if (kv[LANG]) localStorage.setItem('translation', JSON.stringify({ version: ${JSON.stringify(cfg.latestVersion)}, [LANG]: kv[LANG] }));
    // GeoGebra 应用内部界面语言（不在线取翻译文件，只能用已内联的这一份）
    localStorage.setItem('GeoGebraLangUI', LANG);
  } catch (e) {}
  window.validLang = function () { return LANG; };
  window.switchLang = function () {
    var kv = window.__GGB__keysVar || (window.__GGB__keysVar = {});
    if (!kv[LANG]) kv[LANG] = {};
    try { showInLang(LANG); } catch (e) { try { showInEnglish(); } catch (e2) {} }
  };

  window.__GGB_SINGLEFILE__ = {
    version: ${JSON.stringify(cfg.latestVersion)},
    strongName: ${JSON.stringify(strongName)},
    module: MODULE,
    lang: LANG,
    fragments: ${JSON.stringify(fragments.map((f) => f.n))},
    sourceBytes: ${totalBytes}
  };
  console.log(LOG + 'ready: GeoGebra ' + ${JSON.stringify(cfg.latestVersion)} + ' / ' + LANG + ' / ' + window.__GGB_SINGLEFILE__.fragments.length + ' fragments');
})();`;

// ---------------------------------------------------------------- 4. 改写 index.html

const removed = [];
function cut(pattern, label) {
  const re = new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g');
  const n = html.split(re).length - 1;
  if (!n) return;
  html = html.replace(re, () => {
    removed.push(label);
    return '';
  });
  log(`已移除 ${label} ×${n}`);
}

cut(/if\s*\(location\.protocol\s*===\s*"https:"\)\s*\{[\s\S]*?serviceWorker\.register[\s\S]*?\r?\n\}\r?\n/, 'service worker 注册');
cut(/<script[^>]*>[\s\S]{0,400}?googletagmanager[\s\S]*?<\/script>/gi, 'google analytics 脚本');
cut(/<span[^>]*id="fbase"[^>]*>[\s\S]*?<\/span>/gi, 'google analytics 占位');
cut(/<script[^>]*>[\s\S]*?window\.dataLayer[\s\S]*?<\/script>/gi, 'google dataLayer');

const banner = `<div id="ggbSingleFileBanner" style="position:fixed;right:8px;bottom:8px;z-index:1000000;font:12px/1.5 system-ui,sans-serif;color:#6557d2;background:rgba(255,255,255,.92);border:1px solid #e2dff5;border-radius:8px;padding:3px 10px;pointer-events:none">离线单文件版 GeoGebra ${cfg.latestVersion}</div>`;

const cssBlock = cssFiles.length
  ? `<style data-geogebra-singlefile="fonts">\n${cssFiles.map((f) => `/* ${path.basename(path.dirname(f))}/${path.basename(f)} */\n${fs.readFileSync(f, 'utf8')}`).join('\n')}\n</style>`
  : '';
if (cssBlock) html = html.replace('</head>', () => `${cssBlock}\n</head>`);
else log('警告: 镜像里没有 css/*.css，字体将回退到系统字体');

// 页面上标记一下，避免 SEO 标签指向线上站点
html = html.replace(/<link rel="canonical"[^>]*>/gi, '<!-- canonical 已移除: 单文件离线版 -->');
html = html.replace(/<link rel="alternate"[^>]*href="https:\/\/www\.geogebra\.org[^>]*>/gi, '');

// 注意：替换值必须用函数形式，否则 GWT 源码里的 "$'" / "$&" 会被当成 replace 的特殊模式
if (!html.includes('</body>')) throw new Error('index.html 里没有 </body>');
const shell = html;
html = html.replace('</body>', () => `${banner}\n<script>\n${shim}\n</script>\n</body>`);

// ---------------------------------------------------------------- 5. 输出

fs.mkdirSync(path.dirname(opts.out), { recursive: true });
const outBuf = Buffer.from(html, 'utf8');
fs.writeFileSync(opts.out, outBuf);

log(`\n输出 ${path.relative(ROOT, opts.out)}  ${(outBuf.length / 1048576).toFixed(2)} MB  sha256:${crypto.createHash('sha256').update(outBuf).digest('hex').slice(0, 16)}`);

// ---------------------------------------------------------------- 6. 自检

if (opts.check) {
  const problems = [];
  // 只检查页面骨架（注入 GWT 源码之前），否则会把源码里的字符串当成资源引用
  for (const m of shell.matchAll(/<script[^>]*\ssrc=["']([^"']+)["']/gi)) problems.push(`外部脚本: ${m[1]}`);
  for (const m of shell.matchAll(/<link[^>]*\shref=["'](https?:)?\/\/([^"']+)["']/gi)) problems.push(`外部样式: ${m[2]}`);
  if (/serviceWorker\.register/.test(shell)) problems.push('仍有 serviceWorker.register');
  if (!/<html[\s>]/i.test(html) || !/<\/html>/i.test(html)) problems.push('HTML 结构不完整');
  for (const [k, buf] of sources) {
    if (k.startsWith('css:')) continue;
    try {
      new Function(buf.toString('utf8'));
    } catch (e) {
      problems.push(`${k} 语法错误: ${e.message}`);
    }
  }
  if (problems.length) {
    console.error('\n自检未通过:');
    for (const p of problems) console.error('  - ' + p);
    process.exit(1);
  }
  log('\n自检通过: 无外部资源引用，内联 JS 均可解析。');
}