# MirroredWebPage

用 AI agent 把线上动态网站（SPA）做成**离线镜像**，本地双击 `index.html` 即可使用，零外部请求。

## 内容

- `Geogebra/` — GeoGebra 计算器套件离线镜像（6 模式：Graphing / 3D Calculator / Geometry / CAS / Probability / Scientific）。双击 `Geogebra/index.html` 可用。
- `Desmos/` — Desmos 科学计算器离线镜像。

## 说明

- 资源来自各官网公开客户端；其中内嵌的 Firebase / Bugsnag 等密钥均为对应产品的**公开网页客户端密钥**，非私密凭证，无计费或账户权限风险。
- 离线运行所需的 GWT 运行时（主模块 + 懒加载片段）位于 `Geogebra/apps/`，请勿删除。

## GeoGebra 单文件离线版

`Geogebra/` 是「目录 + 多个 JS 分片」，拷来拷去容易散。`tools/build-geogebra-singlefile.mjs` 可以把它压成一个**自包含的 HTML**（约 22MB），双击即用，不需要旁边的 `apps/` 目录，也不需要任何网络：

```bash
node tools/build-geogebra-singlefile.mjs            # -> dist/geogebra-single.html
node tools/build-geogebra-singlefile.mjs --check    # 额外做静态自检
node tools/test-singlefile-shim.mjs                 # 不开浏览器，验证运行时映射
```

可选参数：`--lang zh-CN`（默认用镜像里唯一的语言包）、`--out FILE`、`--no-xhr-guard`。

产物做了什么：

- 内联 GWT permutation（bootstrap）+ 14 个 deferredjs 分片 + 语言包 + 字体 CSS（字体在镜像里本来就是 base64）；
- 用 `Document.createElement` 拦截器把 GWT / GeoGebra 的 `<script src>`、`<link href>` 重定向到内存里的 `blob:` URL，**保留 GWT 原有的异步加载时序**；blob 被浏览器拒绝时自动回退 `data:`；
- GWT 把分片加载进自己创建的隐藏 iframe，而每个 iframe 是独立 realm，所以拦截器会跟着 iframe 逐个 realm 打补丁；
- 剥离 Service Worker、Google Analytics、指向官网的 canonical/hreflang；
- 未内联的本地资源（`geogebra_macro.xml` 等镜像里本来就没有的文件）由 XHR 守卫快速失败，避免 `file://` 下长时间挂起；
- 语言固定为镜像里内联的那一份（默认 zh-CN），同时写入 `GeoGebraLangUI`，应用内界面也是中文。

已知限制：

- 右上角「布置作业 / 登录」等需要联网的功能不可用（按钮文案在英文下正常，中文下会显示成 `title`——镜像自带的 zh-CN 语言包缺这个键，属于上游翻译包的问题）。
- 3D 模型导出 STL/SVG 仍会尝试从 cdnjs / unpkg 加载 three.js（仅这两个按钮用到，主渲染不依赖）。
- `.gitignore` 已忽略 `dist/`，产物不入库，需要时用 Release 或网盘分发。

渲染冒烟测试（需要本机有 Chromium/Edge）：

```bash
chrome --headless=new --disable-gpu --window-size=1440,900 --virtual-time-budget=60000 \
       --screenshot=shot.png "file:///$(pwd)/dist/geogebra-single.html"
```
