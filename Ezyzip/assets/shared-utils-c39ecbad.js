"use strict";
var sharedUtils = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // src/services/sharedUtils.ts
  var sharedUtils_exports = {};
  __export(sharedUtils_exports, {
    buildDirectoryAncestors: () => buildDirectoryAncestors,
    canPreview: () => canPreview,
    createFileListItem: () => createFileListItem,
    formatDuration: () => formatDuration,
    formatFileSize: () => formatFileSize,
    getTruncName: () => getTruncName,
    hasRootLevelEntry: () => hasRootLevelEntry,
    normalizeWorkerError: () => normalizeWorkerError,
    reconcileOutputSizes: () => reconcileOutputSizes,
    safeFilename: () => safeFilename,
    safePathComponent: () => safePathComponent
  });

  // src/services/filesize.ts
  var b = /^(b|B)$/;
  var symbol = {
    iec: {
      bits: [
        "bit",
        "Kibit",
        "Mibit",
        "Gibit",
        "Tibit",
        "Pibit",
        "Eibit",
        "Zibit",
        "Yibit"
      ],
      bytes: ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    },
    jedec: {
      bits: [
        "bit",
        "Kbit",
        "Mbit",
        "Gbit",
        "Tbit",
        "Pbit",
        "Ebit",
        "Zbit",
        "Ybit"
      ],
      bytes: ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    }
  };
  var fullform = {
    iec: ["", "kibi", "mebi", "gibi", "tebi", "pebi", "exbi", "zebi", "yobi"],
    jedec: [
      "",
      "kilo",
      "mega",
      "giga",
      "tera",
      "peta",
      "exa",
      "zetta",
      "yotta"
    ]
  };
  var roundingFuncs = {
    floor: Math.floor,
    ceil: Math.ceil
  };
  function filesize(arg, descriptor = {}) {
    let result = [], val = 0, e, base, bits, ceil, full, fullforms, locale, localeOptions, neg, num, output, pad, round, u, unix, separator, spacer, standard, symbols, roundingFunc, precision;
    if (isNaN(arg)) {
      throw new TypeError("Invalid number");
    }
    bits = descriptor.bits === true;
    unix = descriptor.unix === true;
    pad = descriptor.pad === true;
    base = descriptor.base || 10;
    round = descriptor.round !== void 0 ? descriptor.round : unix ? 1 : 2;
    locale = descriptor.locale !== void 0 ? descriptor.locale : "";
    localeOptions = descriptor.localeOptions || {};
    separator = descriptor.separator !== void 0 ? descriptor.separator : "";
    spacer = descriptor.spacer !== void 0 ? descriptor.spacer : unix ? "" : " ";
    symbols = descriptor.symbols || {};
    standard = base === 2 ? descriptor.standard || "iec" : "jedec";
    output = descriptor.output || "string";
    full = descriptor.fullform === true;
    fullforms = descriptor.fullforms instanceof Array ? descriptor.fullforms : [];
    e = descriptor.exponent !== void 0 ? descriptor.exponent : -1;
    roundingFunc = roundingFuncs[descriptor.roundingMethod] || Math.round;
    num = Number(arg);
    neg = num < 0;
    ceil = base > 2 ? 1e3 : 1024;
    precision = isNaN(descriptor.precision) === false ? parseInt(descriptor.precision, 10) : 0;
    if (neg) {
      num = -num;
    }
    if (e === -1 || isNaN(e)) {
      e = Math.floor(Math.log(num) / Math.log(ceil));
      if (e < 0) {
        e = 0;
      }
    }
    if (e > 8) {
      if (precision > 0) {
        precision += 8 - e;
      }
      e = 8;
    }
    if (output === "exponent") {
      return e;
    }
    if (num === 0) {
      result[0] = 0;
      u = result[1] = unix ? "" : symbol[standard][bits ? "bits" : "bytes"][e];
    } else {
      val = num / (base === 2 ? Math.pow(2, e * 10) : Math.pow(1e3, e));
      if (bits) {
        val = val * 8;
        if (val >= ceil && e < 8) {
          val = val / ceil;
          e++;
        }
      }
      const p = Math.pow(10, e > 0 ? round : 0);
      result[0] = roundingFunc(val * p) / p;
      if (result[0] === ceil && e < 8 && descriptor.exponent === void 0) {
        result[0] = 1;
        e++;
      }
      u = result[1] = base === 10 && e === 1 ? bits ? "kbit" : "kB" : symbol[standard][bits ? "bits" : "bytes"][e];
      if (unix) {
        result[1] = result[1].charAt(0);
        if (b.test(result[1])) {
          result[0] = Math.floor(result[0]);
          result[1] = "";
        }
      }
    }
    if (neg) {
      result[0] = -result[0];
    }
    if (precision > 0) {
      result[0] = result[0].toPrecision(precision);
    }
    result[1] = symbols[result[1]] || result[1];
    if (locale === true) {
      result[0] = result[0].toLocaleString();
    } else if (locale.length > 0) {
      result[0] = result[0].toLocaleString(locale, localeOptions);
    } else if (separator.length > 0) {
      result[0] = result[0].toString().replace(".", separator);
    }
    if (pad && Number.isInteger(result[0]) === false && round > 0) {
      const x = separator || ".", tmp = result[0].toString().split(x), s = tmp[1] || "", l = s.length, n = round - l;
      result[0] = `${tmp[0]}${x}${s.padEnd(l + n, "0")}`;
    }
    if (full) {
      result[1] = fullforms[e] ? fullforms[e] : fullform[standard][e] + (bits ? "bit" : "byte") + (result[0] === 1 ? "" : "s");
    }
    return output === "array" ? result : output === "object" ? { value: result[0], symbol: result[1], exponent: e, unit: u } : result.join(spacer);
  }
  filesize.partial = (opt) => (arg) => filesize(arg, opt);
  var filesize_default = filesize;

  // src/services/sharedUtils.ts
  function formatFileSize(bytes) {
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }
  function formatDuration(seconds) {
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor(seconds % 3600 / 60);
      return `${hours}h ${minutes}m`;
    }
  }
  function getTruncName(filename, size) {
    const fl = filename.length;
    if (fl < size) {
      return filename;
    }
    return "..." + filename.substring(fl - size);
  }
  var PREVIEW_EXTS = [
    // --- Images ---
    "JPG",
    "JPEG",
    "GIF",
    "BMP",
    "WEBP",
    "PNG",
    "SVG",
    "ICO",
    "AVIF",
    // --- Audio / video ---
    "MP3",
    "WAV",
    "OGG",
    "MID",
    "PDF",
    "MP4",
    "OGV",
    "MKV",
    "MOV",
    "WEBM",
    "WEBA",
    "AAC",
    "FLAC",
    "PCM",
    "MPG",
    "MPEG",
    "AVI",
    "WMV",
    // --- Markup / text / docs ---
    "VUE",
    "INF",
    "HTML",
    "HTM",
    "JS",
    "TXT",
    "MD",
    "SH",
    "CSS",
    "JAVA",
    "XML",
    "PROPERTIES",
    "CONFIG",
    "RB",
    "JSON",
    "LOG",
    "JSP",
    "INI",
    "LUA",
    "CPP",
    "H",
    "PLM",
    "YML",
    "CMD",
    "BAT",
    "CONF",
    "LICENSE",
    "MF",
    "NFO",
    "SRT",
    "URL",
    "ME",
    // --- Modern code (union from asar-extract-worker.ts) ---
    "TS",
    "TSX",
    "JSX",
    "SVELTE",
    "PY",
    "GO",
    "RS",
    "C",
    "HPP",
    "CS",
    "PHP",
    "SQL",
    "YAML",
    // --- Valve game configs (union from vpkedit-extract-worker.ts) ---
    "CFG",
    "VMT",
    // --- Office documents (preview via docx-preview / SheetJS / etc.) ---
    "DOCX",
    "XLSX",
    "XLS",
    "ODS",
    "CSV",
    // --- Exotic images (preview via ImageMagick WASM) ---
    "HEIC",
    "HEIF",
    "TIF",
    "TIFF",
    "PSD",
    "JXL",
    "DNG",
    "CR2",
    "NEF",
    "ARW"
  ];
  function canPreview(filename) {
    if (filename.indexOf(".") < 0) {
      return true;
    }
    if (filename.indexOf(".") === 0) {
      return true;
    }
    const extension = (filename.split(".").pop() ?? "").toUpperCase();
    return PREVIEW_EXTS.indexOf(extension) !== -1;
  }
  function createFileListItem(fullpath, isDirectory, size, options) {
    const directory = fullpath.split("/").slice(0, -1).join("/");
    const filename = fullpath.split("/").pop() ?? "";
    const ext = filename.split(".").pop() ?? "";
    const sizeLabel = filesize_default(size);
    const isSymlink = options && options.isSymlink ? true : false;
    const _maxSize = options && options.maxSize ? options.maxSize : 2147483648;
    return {
      directory,
      filename,
      fullpath,
      ext,
      isDirectory,
      size,
      sizeLabel,
      // Directories are never previewable, regardless of what their name
      // looks like to canPreview(). This matches the explicit guard used by
      // asar/wad/vpkedit workers before migration and fixes a latent quirk
      // in Utils.ts where a directory named e.g. "src" would report true.
      canPreview: !isDirectory && canPreview(filename),
      truncName: getTruncName(fullpath, 100),
      truncNameSM: getTruncName(fullpath, 70),
      isTooBig: size > _maxSize,
      isSymlink
    };
  }
  function hasRootLevelEntry(fileList) {
    let any = false;
    for (const entry of fileList) {
      if (entry.directory === "")
        return true;
      any = true;
    }
    return !any;
  }
  function normalizeWorkerError(error, fallbackMessage) {
    const codeOf = (e) => {
      if (e && typeof e === "object") {
        const c = e.code;
        if (typeof c === "string" && c.length > 0)
          return c;
      }
      return void 0;
    };
    const withCode = (base, e) => {
      const code = codeOf(e);
      return code ? { ...base, code } : base;
    };
    if (typeof error === "string" && error.length > 0) {
      return { name: "Error", message: error };
    }
    if (error instanceof Error && error.message) {
      return withCode({ name: error.name || "Error", message: error.message }, error);
    }
    if (error && typeof error === "object") {
      const e = error;
      if (typeof e.message === "string" && e.message.length > 0) {
        return withCode({
          name: typeof e.name === "string" && e.name.length > 0 ? e.name : "Error",
          message: e.message
        }, error);
      }
    }
    const fallback = fallbackMessage?.trim();
    if (fallback && fallback.length > 0) {
      return { name: "Error", message: fallback };
    }
    if (typeof error === "number") {
      return { name: "Error", message: `WASM error code: ${error}` };
    }
    return { name: "Error", message: "Unknown error" };
  }
  function safePathComponent(name) {
    if (!name)
      return "_";
    let safe = name.replace(/\0/g, "").replace(/[\\/<>|"*?:]/g, "-").replace(/[\x01-\x1f\x7f]/g, "").replace(/\p{Cf}/gu, "").replace(/^\s+/, "");
    safe = safe.replace(/[.\s]+$/, "");
    if (safe === "." || safe === "..")
      safe = "_" + safe;
    const reserved = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)/i;
    if (reserved.test(safe))
      safe = "_" + safe;
    return safe || "_";
  }
  function safeFilename(fullpath) {
    return fullpath.replace(/\\/g, "/").split("/").map((component) => component ? safePathComponent(component) : "").filter(Boolean).join("/");
  }
  function buildDirectoryAncestors(fullpath, existingDirs) {
    const parts = fullpath.split("/");
    if (parts.length <= 1) {
      return [];
    }
    const newDirs = [];
    let currentPath = "";
    for (let i = 0; i < parts.length - 1; i++) {
      currentPath += (i > 0 ? "/" : "") + parts[i];
      if (!existingDirs.has(currentPath) && newDirs.indexOf(currentPath) === -1) {
        newDirs.push(currentPath);
      }
    }
    return newDirs;
  }
  async function reconcileOutputSizes(dirHandle, expectedByDest, options) {
    const { failedDests, concurrency = 64 } = options;
    const short = [];
    const missing = [];
    const targets = [];
    for (const [dest, expected] of expectedByDest) {
      if (failedDests.has(dest))
        continue;
      if (!(expected > 0))
        continue;
      targets.push([dest, expected]);
    }
    if (targets.length === 0)
      return { short, missing };
    const physicalSizeOf = async (dest) => {
      const parts = dest.split("/").filter((p) => p.length > 0);
      const name = parts.pop();
      if (!name)
        return null;
      let dir = dirHandle;
      for (const part of parts) {
        dir = await dir.getDirectoryHandle(part);
      }
      const fh = await dir.getFileHandle(name);
      return (await fh.getFile()).size;
    };
    const limit = Math.max(1, concurrency);
    for (let i = 0; i < targets.length; i += limit) {
      const batch = targets.slice(i, i + limit);
      await Promise.all(
        batch.map(async ([dest, expected]) => {
          let actual;
          try {
            actual = await physicalSizeOf(dest);
          } catch {
            actual = null;
          }
          if (actual === null) {
            missing.push(dest);
          } else if (actual < expected) {
            short.push({ path: dest, expected, actual });
          }
        })
      );
    }
    return { short, missing };
  }
  return __toCommonJS(sharedUtils_exports);
})();

sharedUtils = (function (target, sourceId) {
  return new Proxy(target, {
    get: function (t, k) {
      // Symbol keys and the string key "then" must pass through untouched:
      // "then" is probed as a STRING by every Promise resolution, so throwing
      // here would break any `await sharedUtils`.
      if (typeof k === "string" && k !== "then" && !(k in t)) {
        throw new Error(
          'shared-utils.js is stale: export "' + k + '" is missing (source ' +
          sourceId + '). Redeploy ./shared-utils-*.js'
        );
      }
      return t[k];
    }
  });
})(sharedUtils, "a2220cbe");
