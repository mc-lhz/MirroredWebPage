#!/usr/bin/env node
/**
 * test-singlefile-shim.mjs —— 不开浏览器，验证单文件里注入的运行时是否正确。
 *
 *   node tools/build-geogebra-singlefile.mjs
 *   node tools/test-singlefile-shim.mjs [dist/geogebra-single.html]
 *
 * 用最小 DOM 桩把 shim 跑起来，断言：
 *   - GWT 的 nocache / permutation / deferredjs 请求都被映射到内存资源
 *   - GeoGebra 注入的 <link>（字体 CSS）也被映射
 *   - iframe 独立 realm 同样被打补丁（GWT 把分片加载进自建 iframe）
 *   - 未内联的资源不会被误拦截，XHR 守卫只拦真正的缺失文件
 *   - 语言包与 GeoGebraLangUI 已就位
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = process.argv[2] ? path.resolve(ROOT, process.argv[2]) : path.join(ROOT, 'dist', 'geogebra-single.html');
if (!fs.existsSync(target)) throw new Error(`先构建：node tools/build-geogebra-singlefile.mjs（找不到 ${target}）`);

const html = fs.readFileSync(target, 'utf8');
const marker = "var LOG = '[geogebra-singlefile] '";
const start = html.indexOf(marker);
if (start < 0) throw new Error('产物里找不到注入的运行时');
const from = html.lastIndexOf('<script>', start);
const to = html.indexOf('</script>', html.length - 4096);
const shim = html.slice(from + '<script>'.length, to);
if (!shim.trimEnd().endsWith('})();')) throw new Error('运行时提取不完整');

// ---------------------------------------------------------- 最小 DOM 桩

class FakeElement {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.attrs = {};
  }
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  getAttribute(k) {
    return this.attrs[k] ?? null;
  }
  addEventListener() {}
}
class FakeDocument {}
FakeDocument.prototype.createElement = function (tag) {
  return new FakeElement(tag);
};
class FakeNode {
  appendChild(n) {
    return n;
  }
  insertBefore(n) {
    return n;
  }
  replaceChild(n) {
    return n;
  }
}
class FakeXHR {
  open(...args) {
    this.opened = args;
  }
}

globalThis.Node = FakeNode;
globalThis.Element = FakeNode;
for (const m of ['append', 'prepend', 'before', 'after', 'replaceWith']) {
  globalThis.Element.prototype[m] = FakeNode.prototype.appendChild;
}
globalThis.Document = FakeDocument;
globalThis.XMLHttpRequest = FakeXHR;
globalThis.window = globalThis;
globalThis.document = new FakeDocument();
globalThis.document.body = new FakeNode();
globalThis.location = { href: 'file:///C:/repo/dist/geogebra-single.html', host: '', protocol: 'file:', search: '' };
globalThis.localStorage = {
  _d: {},
  getItem(k) {
    return this._d[k] ?? null;
  },
  setItem(k, v) {
    this._d[k] = String(v);
  },
};
let shown = null;
globalThis.showInLang = (l) => {
  shown = l;
};
globalThis.showInEnglish = () => {
  shown = 'en';
};

const quiet = console.log;
console.log = () => {};
console.warn = () => {};
(0, eval)(shim);
console.log = quiet;

// ---------------------------------------------------------- 断言

let failed = 0;
function check(name, ok, detail = '') {
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`);
}

const S = window.__GGB_SINGLEFILE__.strongName;
const mainDoc = new FakeDocument();

const mapped = [
  ['apps/latest/web3d/web3d.nocache.js', 'nocache'],
  [`file:///C:/repo/Geogebra/apps/latest/web3d/web3d.nocache.js`, 'nocache'],
  [`file:///C:/repo/apps/latest/web3d/${S}.cache.js`, 'permutation'],
  [`file:///C:/repo/apps/latest/web3d/deferredjs/${S}/2.cache.js`, `fragment:2`],
  [`https://x/apps/latest/web3d/deferredjs/${S}/14.cache.js`, 'fragment:14'],
  ['apps/5.0.580.0/web3d/js/properties_keys_zh-CN.js', `l10n:${window.__GGB_SINGLEFILE__.lang}`],
  ['file:///C:/repo/dist/apps/latest/web3d/../css/fonts.css', 'css:fonts.css'],
];
for (const [url, label] of mapped) {
  const el = mainDoc.createElement('script');
  el.setAttribute('src', url);
  const got = String(el.getAttribute('src'));
  check(`映射到内存: ${label}`, /^(blob:|data:)/.test(got), got.slice(0, 32));
}

const untouched = [
  'https://www.geogebra.org/apps/5.0.580.0/web3d/js/properties_keys_en.js',
  'https://cdnjs.cloudflare.com/ajax/libs/three.js/92/three.min.js',
  'https://www.geogebra.org/api/material_preview.php?u=abc',
];
for (const url of untouched) {
  const el = mainDoc.createElement('script');
  el.setAttribute('src', url);
  check(`原样透传: ${url.slice(0, 46)}`, el.getAttribute('src') === url);
}

const el2 = mainDoc.createElement('script');
el2.src = `deferredjs/${S}/3.cache.js`;
check('el.src 赋值路径同样被改写', /^(blob:|data:)/.test(String(el2.getAttribute('src'))));

const linkEl = mainDoc.createElement('link');
linkEl.href = 'file:///C:/repo/dist/apps/latest/web3d/../css/greek-font.css';
check('<link href> 被改写（字体 CSS 缺失会卡住启动）', /^(blob:|data:)/.test(String(linkEl.getAttribute('href'))));

// GWT 把 permutation / deferredjs 加载进自建的隐藏 iframe，而 iframe 是独立 realm
const childRealm = { Document: FakeDocument };
const fakeIframe = new FakeElement('iframe');
fakeIframe.contentWindow = childRealm;
globalThis.document.body.appendChild(fakeIframe);
const childEl = new childRealm.Document().createElement('script');
childEl.src = `deferredjs/${S}/4.cache.js`;
check('iframe realm 同样被打补丁', /^(blob:|data:)/.test(String(childEl.getAttribute('src'))));

const xhr = new FakeXHR();
xhr.open('GET', 'file:///C:/repo/apps/latest/web3d/geogebra_macro.xml');
check('XHR 守卫拦下未内联的 xml', !xhr.opened);

const xhr2 = new FakeXHR();
xhr2.open('GET', `file:///C:/repo/apps/latest/web3d/deferredjs/${S}/1.cache.js`);
check('XHR 守卫放行已内联资源', !!xhr2.opened);

shown = null;
window.switchLang('en');
check('switchLang 强制使用内联语言包', shown === window.__GGB_SINGLEFILE__.lang, `-> ${shown}`);

const tr = JSON.parse(globalThis.localStorage.getItem('translation') || '{}');
check('localStorage.translation 已写入', !!tr[window.__GGB_SINGLEFILE__.lang], `version=${tr.version}`);
check('GeoGebraLangUI 已写入', globalThis.localStorage.getItem('GeoGebraLangUI') === window.__GGB_SINGLEFILE__.lang);
check('__GGB__keysVar 已求值', !!globalThis.__GGB__keysVar?.[window.__GGB_SINGLEFILE__.lang]);

console.log(`\n${failed ? failed + ' 个用例失败' : '全部通过'}  (${window.__GGB_SINGLEFILE__.fragments.length} fragments, ${(window.__GGB_SINGLEFILE__.sourceBytes / 1048576).toFixed(2)} MB JS)`);
process.exit(failed ? 1 : 0);