import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// 产出单个自包含 index.html：所有 JS / CSS / 字体均内联，可直接 file:// 双击打开。
export default defineConfig({
  base: "./",
  plugins: [viteSingleFile()],
  build: {
    outDir: "dist",
    assetsInlineLimit: 100000000,
    chunkSizeWarningLimit: 100000,
    cssCodeSplit: false,
    reportCompressedSize: false,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
