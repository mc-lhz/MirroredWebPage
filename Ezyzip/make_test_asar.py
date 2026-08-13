#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a valid Electron-style .asar that ezyzip's extraction worker accepts.

ezyzip asar worker (workers/asar-extract-worker-aa430551.js) expects:
  bytes[0..4)  uint32 LE  pickleHeaderSize   (logged only, not validated)
  bytes[4..8)  uint32 LE  headerPickleSize   (logged only, not validated)
  bytes[8..12) uint32 LE  (unused)
  bytes[12..16) uint32 LE jsonSize  (MUST be >0 and <= byteLength-16)
  bytes[16 .. 16+jsonSize)  UTF-8 JSON header {"files":{...}}
  bytes[16+jsonSize ..]     file data region
Each file entry in JSON: {"size": N, "offset": "M"} where M is the byte offset
of the file's content WITHIN the file-data region (i.e. relative to byte 16+jsonSize).
"""
import json
import struct
import sys

# (relative_path, content_bytes)  -- order determines packing offsets
FILES = [
    ("hello.txt", b"hello asar\n"),
    ("dir/world.txt", b"world\n"),
    ("readme.md", b"# test asar\nmirrored offline by ezyzip-mirror\n"),
]


def build_header(files):
    """Return (header_dict, ordered [(path,content,offset)])."""
    # Build nested files tree
    tree = {}
    flat = []  # (path, content, offset)
    cursor = 0
    for path, content in files:
        parts = path.split("/")
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {}).setdefault("files", {})
        node[parts[-1]] = {"size": len(content), "offset": str(cursor)}
        flat.append((path, content, cursor))
        cursor += len(content)

    def to_json(node):
        out = {}
        for k, v in node.items():
            if "files" in v:
                out[k] = {"files": to_json(v["files"])}
            else:
                out[k] = {"size": v["size"], "offset": v["offset"]}
        return out

    header = {"files": to_json(tree)}
    return header, flat


def pack(files):
    header, flat = build_header(files)
    header_json = json.dumps(header, ensure_ascii=False).encode("utf-8")
    out = bytearray(16)
    struct.pack_into("<I", out, 12, len(header_json))  # jsonSize at offset 12
    out += header_json
    data_start = len(out)
    for path, content, offset in flat:
        assert len(out) == data_start + offset, f"offset mismatch for {path}"
        out += content
    return bytes(out), header


def self_check(asar, header):
    """Re-parse exactly like the worker to confirm validity."""
    import io
    dv = memoryview(asar)
    assert len(asar) >= 16, "too small"
    json_size = struct.unpack_from("<I", asar, 12)[0]
    assert 0 < json_size <= len(asar) - 16, f"bad jsonSize {json_size}"
    h = 16 + json_size
    head = json.loads(asar[16:h].decode("utf-8"))
    assert head.get("files"), "missing files"
    # verify offsets/sizes line up with data region
    def walk(node):
        for k, v in node.items():
            if "files" in v:
                yield from walk(v["files"])
            else:
                off = int(v.get("offset", 0))
                sz = v.get("size", 0)
                assert off + sz <= len(asar) - h, f"{k} out of bounds"
                yield k
    names = list(walk(head["files"]))
    return names


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "test.asar"
    asar, header = pack(FILES)
    with open(out_path, "wb") as f:
        f.write(asar)
    names = self_check(asar, header)
    print(f"wrote {out_path}: {len(asar)} bytes")
    print(f"files in archive: {names}")
    print("self-check: OK")


if __name__ == "__main__":
    main()
