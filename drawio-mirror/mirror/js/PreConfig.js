// 占位文件：原站 js/PreConfig.js 通常 404（站点自定义预配置，默认部署无此文件）。
// diagrams.net 的 bootstrap.js 在 PreConfig.js 成功加载后才回调 loadAppJS 去加载 app.min.js。
// 这里放一个空文件使其返回 200，确保离线镜像下 app.min.js 能被加载、编辑器正常初始化。
