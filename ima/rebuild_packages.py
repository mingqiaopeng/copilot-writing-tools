#!/usr/bin/env python3
"""重建 ima/packages/ 下全部 per-skill ZIP（并逐包校验三约束）。

三约束（见 ima/MIGRATION-GUIDE.md「打包注册」）：
1. ZIP 文件名 = name 字段 = 包内目录名，三者一致
2. 包内换行符必须为 LF
3. frontmatter 前不得有 UTF-8 BOM

用法: python ima/rebuild_packages.py
"""

import os
import sys
import zipfile

IMA = os.path.dirname(os.path.abspath(__file__))
PACKAGES = os.path.join(IMA, "packages")

os.makedirs(PACKAGES, exist_ok=True)

count = 0
for name in sorted(os.listdir(IMA)):
    d = os.path.join(IMA, name)
    if not os.path.isdir(d) or not os.path.isfile(os.path.join(d, "SKILL.md")):
        continue

    zp = os.path.join(PACKAGES, name + ".zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            for fn in files:
                full = os.path.join(root, fn)
                arc = full.replace(os.sep, "/")[len(IMA) + 1:]
                z.write(full, arc)

    # 校验包内结构
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        bad_root = [n for n in names if not n.startswith(name + "/")]
        if bad_root:
            print(f"FAIL {name}: 包内条目不以 {name}/ 开头: {bad_root}")
            sys.exit(1)
        for n in names:
            data = z.read(n)
            if n.endswith((".md", ".py", ".jsonl")):
                if data.startswith(b"\xef\xbb\xbf"):
                    print(f"FAIL {name}/{n}: 含 BOM")
                    sys.exit(1)
                if b"\r\n" in data:
                    print(f"FAIL {name}/{n}: 含 CRLF")
                    sys.exit(1)

    count += 1
    print(f"OK {name} ({len(names)} 个条目)")

print(f"--- 共重建 {count} 个 ZIP ---")
