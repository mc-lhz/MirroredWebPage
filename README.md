# MirroredWebPage

用 AI agent 把线上动态网站（SPA）做成**离线镜像**，本地双击 `index.html` 即可使用，零外部请求。

## 内容

- `Geogebra/` — GeoGebra 计算器套件离线镜像（6 模式：Graphing / 3D Calculator / Geometry / CAS / Probability / Scientific）。双击 `Geogebra/index.html` 可用。
- `Desmos/` — Desmos 科学计算器离线镜像。

## 说明

- 资源来自各官网公开客户端；其中内嵌的 Firebase / Bugsnag 等密钥均为对应产品的**公开网页客户端密钥**，非私密凭证，无计费或账户权限风险。
- 离线运行所需的 GWT 运行时（主模块 + 懒加载片段）位于 `Geogebra/apps/`，请勿删除。
