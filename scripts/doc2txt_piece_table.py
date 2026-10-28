#!/usr/bin/env python3
"""Word 97-2003 (.doc) 正文抽取：解析 FIB + CLX 分片表（PlcPcd）。

为什么自带解析器：政策库里附件型条目的正文常在 .doc 里，而 dnf 源里往往没有
catdoc / antiword / libreoffice，装 LibreOffice 又是几百 MB。Word 97-2003 是公开格式，
直接读二进制即可，不需要任何外部命令。

依赖：olefile（pip install olefile）。

用法：
    python3 doc2txt_piece_table.py <file.doc> [out.txt]
    输出正文非空白字数 + 前 120 字，便于确认没抽成乱码再入库。

实现依据 [MS-DOC]：
  - FIB 在 WordDocument 流开头；flags(0x0A) bit9 决定用 1Table 还是 0Table
  - fcClx=0x01A2(4B)、lcbClx=0x01A6(4B) 指向 CLX（在 table 流里）
  - CLX 里 0x02 起是 PlcPcd：CP 数组 (n+1)*4B + n*8B 的 PCD
  - PCD 偏移 2 的 4 字节 fc：bit30=1 表示 8 位压缩，按文档代码页解码（中文文档 cp936/GBK）
"""
import struct
import sys


def extract(path: str, codepage: str = "gbk") -> str:
    import olefile

    ole = olefile.OleFileIO(path)
    wd = ole.openstream("WordDocument").read()
    flags = struct.unpack_from("<H", wd, 0x0A)[0]
    table_name = "1Table" if (flags & 0x0200) else "0Table"
    if not ole.exists(table_name):
        table_name = "1Table" if ole.exists("1Table") else "0Table"
    tbl = ole.openstream(table_name).read()

    fc_clx = struct.unpack_from("<I", wd, 0x01A2)[0]
    lcb_clx = struct.unpack_from("<I", wd, 0x01A6)[0]
    clx = tbl[fc_clx: fc_clx + lcb_clx]

    # 跳过 Prc（0x01 开头），定位 0x02 的 PlcPcd
    i = 0
    while i < len(clx) and clx[i] == 0x01:
        cb = struct.unpack_from("<H", clx, i + 1)[0]
        i += 3 + cb
    if i >= len(clx) or clx[i] != 0x02:
        raise SystemExit("CLX 结构异常：找不到 PlcPcd（可能不是 Word 97-2003 格式）")
    lcb = struct.unpack_from("<I", clx, i + 1)[0]
    plc = clx[i + 5: i + 5 + lcb]

    n = (len(plc) - 4) // 12
    cps = list(struct.unpack_from("<%dI" % (n + 1), plc, 0))

    out = []
    for k in range(n):
        cch = cps[k + 1] - cps[k]
        if cch <= 0:
            continue
        pcd_off = 4 * (n + 1) + k * 8
        fc_raw = struct.unpack_from("<I", plc, pcd_off + 2)[0]
        compressed = bool(fc_raw & 0x40000000)
        fc = fc_raw & 0x3FFFFFFF
        if compressed:
            fc //= 2
            out.append(wd[fc: fc + cch].decode(codepage, errors="replace"))
        else:
            out.append(wd[fc: fc + 2 * cch].decode("utf-16-le", errors="replace"))

    text = "".join(out)
    # 清 Word 控制字符（域代码、分页、单元格分隔等），保留可读换行
    for a, b in (("\r", "\n"), ("\x07", "\n"), ("\x0b", "\n"), ("\x0c", "\n"),
                 ("\x1e", "-"), ("\x13", ""), ("\x14", ""), ("\x15", "")):
        text = text.replace(a, b)
    return text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法: python3 doc2txt_piece_table.py <file.doc> [out.txt]")
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src.rsplit(".", 1)[0] + ".txt"
    t = extract(src)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(t)
    body = "".join(ch for ch in t if not ch.isspace())
    print(f"写出: {dst}")
    print(f"字符数: {len(t)}（非空白 {len(body)}）")
    print("前 120 字:", t.strip()[:120].replace("\n", " "))
