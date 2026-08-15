"""完形填回:在选项行尾标注答案字母,把单词填回正文空位,并删除该选项行。

用法:
  python -m src.fill <md文件> [md文件...]

标记格式(选项行末尾,任选一种):
  21. A. decent B. tolerant C. distant D. selfish → A   箭头
  21. A. decent B. tolerant C. distant D. selfish = A   等号
  21. A. decent B. tolerant C. distant D. selfish > A   大于号
  21. A. decent B. tolerant C. distant D. selfish (A)   括号
  21. A. decent B. tolerant C. distant D. selfish A     裸字母
效果:
  - 正文 $ \\underline{21} $ → **decent**
  - 该选项行删除(非错题彻底清掉)
  - report.md 追加「已填充」清单
"""
import re
import sys
from pathlib import Path

# 行尾填回标记: 箭头/等号/大于号 → 括号 → 裸字母(与选项文本以空白分隔)
MARKER_RE = re.compile(
    r"\s*(?:→|➜|->|=>|>|=)\s*([A-Da-d])\s*$"
    r"|\(\s*([A-Da-d])\s*\)\s*$"
    r"|\s+([A-Da-d])\s*$"
)
OPTION_NUM_RE = re.compile(r"^\s*(\d{1,2})\s*[.、]\s")
BLANK_RE = re.compile(r"\$?\s*\\underline\{(\d{1,2})\}\s*\$?")
OPTION_TOKEN_RE = re.compile(r"[A-Da-d]\.")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
CLOZE_HEAD_RE = re.compile(r"^##\s*(完形)", re.I)


def _marker_letter(line: str) -> str | None:
    m = MARKER_RE.search(line)
    if not m:
        return None
    letter = next((g for g in m.groups() if g), None)
    return letter.upper() if letter else None


def _option_word(line: str, letter: str) -> str:
    """取该选项的英文文本(去掉中文注释、行尾裸答案字母、后续选项)。"""
    pos = [m.start() for m in OPTION_TOKEN_RE.finditer(line)]
    dots = [i for i in pos if line[i : i + 2].upper().startswith(letter.upper())]
    if not dots:
        return ""
    start = dots[0] + 2
    nxt = [i for i in pos if i > dots[0]]
    end = nxt[0] if nxt else len(line)
    seg = line[start:end]
    seg = CJK_RE.split(seg)[0]
    seg = re.sub(r"\s+([A-Da-d])$", "", seg)  # 行尾裸答案字母(如 "pretend D" → "pretend")
    seg = re.sub(r"^[A-Da-d]\.\s*", "", seg)  # 首部误带的选项字母(如 "A. decent" → "decent")
    return seg.strip()


def fill_file(path: Path, report) -> list[str]:
    text = path.read_text(encoding="utf-8")
    out_lines: list[str] = []
    in_cloze = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_cloze = bool(CLOZE_HEAD_RE.match(line))
            out_lines.append(line)
            continue
        if in_cloze and _marker_letter(line):
            letter = _marker_letter(line)
            # 题号: 本行行首,或回溯最近的题号行(选项被 OCR 拆多行)
            num = None
            drop_from = None
            m_num = OPTION_NUM_RE.match(line)
            if m_num:
                num = int(m_num.group(1))
            else:
                for j in range(len(out_lines) - 1, -1, -1):
                    pm = OPTION_NUM_RE.match(out_lines[j])
                    if pm:
                        num, drop_from = int(pm.group(1)), j
                        break
            if num is None:
                report.fill_warnings.append(f"标记行无题号: {line.strip()[:40]}")
                out_lines.append(line)
                continue
            word = _option_word(line, letter)
            if not word:
                report.fill_warnings.append(f"题 {num}: 未解析出 {letter} 选项词")
                out_lines.append(line)
                continue
            text_in = "\n".join(out_lines)
            target = re.compile(r"\$?\s*\\underline\{" + str(num) + r"\}\s*\$?")
            new_in, n = target.subn(lambda m: f"**{word}**", text_in)
            if n == 0:
                report.fill_warnings.append(f"题 {num}: 正文未找到空位 \\underline{{{num}}}")
                out_lines.append(line)
                continue
            out_lines = new_in.split("\n")
            if drop_from is not None:
                out_lines = out_lines[:drop_from]  # 整块删除该题选项(含题号行)
            report.filled.append(f"{num}→{word}")
            continue
        out_lines.append(line)
    path.write_text("\n".join(out_lines), encoding="utf-8")
    return report.filled


def main(argv=None):
    if not argv:
        argv = sys.argv[1:]
    if not argv:
        print("用法: python -m src.fill <md文件> [md文件...]")
        return 1
    from .report import Report

    for f in argv:
        p = Path(f)
        if not p.exists():
            print(f"✗ 文件不存在: {p}")
            continue
        report = Report()
        report.title = p.stem
        filled = fill_file(p, report)
        print(f"✓ {p.name}: 填充 {len(filled)} 题 -> {', '.join(filled)}")
        for w in report.fill_warnings:
            print(f"  ⚠ {w}")
        rp = p.parent / "report.md"
        if rp.exists():
            rp.write_text(rp.read_text(encoding="utf-8") + report.render(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
