# -*- coding: utf-8 -*-
"""Pal-Windows.pak (UnrealPak v11, 非暗号化) のFullDirectoryIndexを読んで
全アセットパスを列挙する。読み取り専用。

使い方: python pak_list.py <出力txt> [フィルタ文字列]
"""

import io
import struct
import sys

PAK_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Palworld\Pal\Content\Paks\Pal-Windows.pak"
MAGIC = 0x5A6F12E1


def read_fstring(f):
    (n,) = struct.unpack("<i", f.read(4))
    if n == 0:
        return ""
    if n > 0:
        b = f.read(n)
        return b[:-1].decode("ascii", errors="replace")
    # 負数はUTF-16
    b = f.read(-n * 2)
    return b[:-2].decode("utf-16-le", errors="replace")


def find_footer(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        tail_len = min(4096, size)
        f.seek(size - tail_len)
        tail = f.read(tail_len)
    magic_le = struct.pack("<I", MAGIC)
    i = tail.rfind(magic_le)
    if i < 0:
        raise RuntimeError("pak magicが見つからない")
    off = size - tail_len + i
    with open(path, "rb") as f:
        f.seek(off)
        magic, version = struct.unpack("<II", f.read(8))
        index_offset, index_size = struct.unpack("<qq", f.read(16))
    return version, index_offset, index_size


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "pak_filelist.txt"
    needle = sys.argv[2].lower() if len(sys.argv) > 2 else None

    # 第1引数は「出力先txt」であって検査対象pakではない。pakパスを渡すと
    # そのpakを一覧テキストで上書き破壊する(2026-07-17に実害発生)ため拒否する
    if out_path.lower().endswith((".pak", ".ucas", ".utoc")):
        raise SystemExit(
            f"[NG] 出力先に {out_path} は指定できない。"
            "第1引数は出力txtのパス。pakの中身を見たいなら UnrealPak.exe <pak> -List を使え"
        )

    version, index_offset, index_size = find_footer(PAK_PATH)
    print(f"pak version={version} index_offset={index_offset} index_size={index_size}")

    with open(PAK_PATH, "rb") as f:
        f.seek(index_offset)
        idx = io.BytesIO(f.read(index_size))

    mount_point = read_fstring(idx)
    (num_entries,) = struct.unpack("<i", idx.read(4))
    (path_hash_seed,) = struct.unpack("<Q", idx.read(8))
    print(f"mount={mount_point} entries={num_entries}")

    (has_path_hash_index,) = struct.unpack("<i", idx.read(4))
    if has_path_hash_index:
        idx.read(8 + 8 + 20)  # offset, size, hash
    (has_full_dir_index,) = struct.unpack("<i", idx.read(4))
    if not has_full_dir_index:
        raise RuntimeError("FullDirectoryIndexが無い")
    fdi_offset, fdi_size = struct.unpack("<qq", idx.read(16))
    idx.read(20)  # hash

    with open(PAK_PATH, "rb") as f:
        f.seek(fdi_offset)
        fdi = io.BytesIO(f.read(fdi_size))

    (num_dirs,) = struct.unpack("<i", fdi.read(4))
    paths = []
    for _ in range(num_dirs):
        dir_name = read_fstring(fdi)
        (num_files,) = struct.unpack("<i", fdi.read(4))
        for _ in range(num_files):
            file_name = read_fstring(fdi)
            fdi.read(4)  # encoded entry offset
            paths.append(dir_name + file_name)

    print(f"total files={len(paths)}")
    if needle:
        paths = [p for p in paths if needle in p.lower()]
        print(f"filtered({needle})={len(paths)}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(paths)))
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
