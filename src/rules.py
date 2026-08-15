"""清洗规则:下划线判定、答案剥离、去重、序号补全。

规则表随案例积累(specs/cleaning-rules.md):新增题型标题变体、词义猜测题干模式时改这里。
"""
import re

# ---- 题型标题/指令变体(可扩展;顺序敏感: 越具体越靠前) ----
# 新高考格式: 第三部分 语言运用 → 第一节(共15小题,完形) + 第二节(共10小题,语法填空)
SECTION_PATTERNS = [
    ("语法填空", re.compile(r"语法填空|语篇填空|短文填空|第二节[（(]共10小题|括号内单词的正确形式|在空白处填入适当")),
    ("完形", re.compile(r"完形|cloze|语言运用|第一节[（(]共15小题|阅读下面短文[^。]{0,60}填入空白处|四个选项中选出可以填入空白处", re.I)),
    ("七选五", re.compile(r"七选五|短文后的选项中|选项中选出能填入空白处")),
    ("阅读", re.compile(r"阅读理解|reading comprehension|reading passage", re.I)),
]

# 词义猜测题干模式(可扩展):命中则该行下划线/波浪线全部保留
WORD_GUESS_STEM = re.compile(r"underlined|下划线|划线词|划线部分|加粗|bold", re.I)

# ---- 下划线/波浪线标注(OCR 手写检测),保留 $ 包裹形式 ----
UNDERLINE_RE = re.compile(
    r"\$?\s*\\(?:underline|uwave)\{((?:[^{}]|\{[^{}]*\})*)\}\s*\$?"
)

# 印刷空位编号: ___21___ / 21____ / 1____
FULL_BLANK_RE = re.compile(r"_{2,}\s*(\d{1,2})\s*_{2,}")
TRAIL_BLANK_RE = re.compile(r"(\d{1,2})\s*_{2,}")

# 完形选项行: 定位题号(剥答案前缀用)
NUM_DOT_RE = re.compile(r"(\d{1,2})\s*[.、]\s*(?=[A-Da-d]\.)")       # 41. A. / 353. A.→53
NUM_SPACE_RE = re.compile(r"(\d{1,2})\s*[)）]?\s*(?=[A-Da-d]\.\s)")   # 47 A. / (46) A.
OPTION_TOKEN_RE = re.compile(r"[A-Da-d]\.")
IMG_RE = re.compile(r"<img|<div")

# 阅读分篇标签: 独立字母行 / Passage A / A篇
PASSAGE_LABEL_RE = re.compile(
    r"^\s*(?:Passage\s*[A-D]|[A-D]\s*篇|[A-D]\s*[.、]?\s*)$", re.I
)

# 题号行(阅读题目块起始)
QUESTION_RE = re.compile(r"^\s*(\d{1,2})\s*[.、]\s")


def detect_section(line: str) -> str | None:
    """识别题型标题/指令行;返回题型名(语法填空/完形/七选五/阅读)或 None。"""
    s = line.strip().lstrip("#").strip().strip("*").strip()
    if not s or len(s) > 60:
        return None
    for kind, pat in SECTION_PATTERNS:
        if pat.search(s):
            return kind
    return None


def unwrap_latex(content: str) -> str:
    """去掉 \\text{...} 等包装,取内部文本。"""
    m = re.fullmatch(r"\\(?:text|mathbf|textbf)\{(.*)\}", content.strip())
    return m.group(1) if m else content.strip()


def clean_underlines(line: str, section: str, report) -> str:
    """处理一行中的 \\underline / \\uwave 标注。

    保留: 纯数字序号;词义猜测题干行(规则表)。
    删除: 语法填空中的手写答案(留 ____ 空位);其余去掉划线标记、保留印刷文本。
    """
    guess = bool(WORD_GUESS_STEM.search(line))

    def repl(m):
        inner = unwrap_latex(m.group(1))
        if re.fullmatch(r"\d{1,2}", inner):
            report.underline_kept_number += 1
            return m.group(0)  # 题目序号下划线保留
        if guess:
            report.underline_kept_guess.append(inner)
            return m.group(0)  # 词义猜测词保留
        if section == "语法填空":
            # 粘连题号+答案: "43 a" / "56 an" / "61competitive" → 保留题号,删答案
            mn = re.match(r"^(\d{1,2})\s*(\S.*)$", inner)
            if mn:
                report.grammar_answer_removed.append(mn.group(2))
                return f"$ \\underline{{{int(mn.group(1))}}} $"
            # 中文手写笔记(如"伴随状语")删除,不产生空位
            if re.search(r"[\u4e00-\u9fff]", inner):
                report.grammar_answer_removed.append(inner)
                return ""
            report.grammar_answer_removed.append(inner)
            return "____"  # 手写答案删除,留空位
        report.underline_removed.append(inner)
        return inner  # 印刷文本,去掉划线标记

    return UNDERLINE_RE.sub(repl, line)


def dedupe_lines(lines: list[str], report) -> list[str]:
    """重复行去重(允许空行间隔;空行保留)。"""
    out = []
    last_norm: str | None = None

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    for ln in lines:
        if not ln.strip():
            out.append(ln)
            continue
        n = norm(ln)
        if n == last_norm:
            report.deduped.append(ln.strip()[:60])
            continue
        last_norm = n
        out.append(ln)
    return out


def _option_segments(line: str) -> list[tuple[str, str]]:
    """提取一行中的 (字母, 选项文本) 段,去掉 \\quad 与多余空白。"""
    out = []
    for m in re.finditer(OPTION_TOKEN_RE, line):
        letter = m.group(0)[0].upper()
        start = m.end()
        rest = line[start:]
        nxt = re.search(OPTION_TOKEN_RE, rest)
        end = start + nxt.start() if nxt else len(line)
        seg = re.sub(r"\\quad", " ", line[start:end])
        seg = re.sub(r"\s+", " ", seg).strip()
        out.append((letter, seg))
    return out


def _looks_option(line: str) -> bool:
    return bool(
        NUM_DOT_RE.search(line)
        or NUM_SPACE_RE.search(line)
        or re.match(r"^\s*[A-Da-d][.、]", line)
    )


def _parse_array(body: str) -> tuple[int | None, list[tuple[str, str]]]:
    """解析 $\\begin{array}...\\end{array}$: 返回 (题号|None, [(字母, 选项文本)])。

    示例: '52. \\quad A. \\quad ran out of\\\\C. \\quad cut down on' → (52, [('A','ran out of'),('C','cut down on')])
    """
    num = None
    segs: list[tuple[str, str]] = []
    inner = body.split("\\begin{array}")[-1].split("\\end{array}")[0]
    inner = re.sub(r"\{[lcr]+\}", "", inner, count=1)
    for row in inner.split("\\\\"):
        row = row.replace("\\quad", " ")
        m = NUM_DOT_RE.search(row)
        if m and num is None:
            num = int(m.group(1))
        segs.extend((l, t) for l, t in _option_segments(row) if t)
    return num, segs


def rebuild_option_table(lines: list[str], report) -> list[str]:
    """完形选项表重构: 每行一题。

    - 合并被 OCR 拆散的跨行选项;题号缺失按序补上;未扫到的选项留空。
    - LaTeX array(如 $\\begin{array}...$)解析其中的字母选项。
    - 图片行原位保留;杂行(手写笔记等)丢弃并记录。
    """
    # 定位选项表起始(首个选项样行)
    start = None
    for i, ln in enumerate(lines):
        if _looks_option(ln) and not IMG_RE.search(ln):
            start = i
            break
    if start is None:
        return lines

    # 锚点题号: 表格内首个题号,否则取正文空位首号
    anchor = None
    for ln in lines[start:]:
        m = NUM_DOT_RE.search(ln) or NUM_SPACE_RE.search(ln)
        if m:
            anchor = int(m.group(1))
            break
    if anchor is None:
        mb = re.search(r"\\underline\{(\d{1,2})\}", "\n".join(lines[:start]))
        anchor = int(mb.group(1)) if mb else 1
    last_num = anchor - 1

    out: list[str] = []
    current: dict | None = None  # {"num": int|None, "segs": [(letter, text)]}

    def flush():
        nonlocal current, last_num
        if current is None:
            return
        report.cloze_rebuilt += 1
        num, segs = current["num"], current["segs"]
        if num is None:
            num = last_num + 1
            report.cloze_renumbered.append(num)
        elif last_num is not None and num != last_num + 1:
            report.cloze_numjumps.append((num, last_num + 1))
        d: dict[str, str] = {}
        for letter, text in segs:
            d.setdefault(letter, text)
        parts = []
        for letter in "ABCD":
            if letter in d:
                parts.append(f"{letter}. {d[letter]}")
            else:
                parts.append(f"{letter}. ")
                report.cloze_blank_options.append(num)
        out.append(f"{num}. " + " ".join(parts))
        last_num = num
        current = None

    array_buf: list[str] = []
    for ln in lines[start:]:
        if IMG_RE.search(ln):
            flush()
            out.append(ln)
            continue
        if "\\begin{array}" in ln:
            if "\\end{array}" in ln:
                array_buf = []
                num, segs = _parse_array(ln)
            else:
                array_buf = [ln]  # 跨行数组,继续缓冲
                continue
        elif array_buf:
            array_buf.append(ln)
            if "\\end{array}" in ln:
                num, segs = _parse_array("\n".join(array_buf))
                array_buf = []
            else:
                continue
        else:
            m = NUM_DOT_RE.search(ln) or NUM_SPACE_RE.search(ln)
            num = int(m.group(1)) if m else None
            if m and m.start() > 0:
                report.stripped_prefix.append(ln[: m.start()].strip()[:30])
            # 答案前缀可能是 "A." 形式(如 "A. 26. A. rolled"),选项段须从题号之后提取
            segs = _option_segments(ln[m.start():]) if m else _option_segments(ln)
            if not segs and num is None:
                if ln.strip():
                    report.cloze_dropped.append(ln.strip()[:40])
                continue  # 杂行(手写笔记等)丢弃
        if num is not None:
            if current is not None and current["num"] is None and num == last_num + 1:
                current["num"] = num  # 片段在前、题号在后,合并(如 46 的 C/D 先于题号行)
                current["segs"].extend(segs)
            else:
                flush()
                current = {"num": num, "segs": segs}
        else:
            if current is None:
                current = {"num": None, "segs": segs}
            elif len({l for l, _ in current["segs"]}) >= 4 or (
                current["segs"] and current["segs"][-1][0] == "D"
            ):
                flush()  # 当前题已完整,新起一题
                current = {"num": None, "segs": segs}
            else:
                current["segs"].extend(segs)
    flush()
    return lines[:start] + out  # 保留正文(选项表之前的行)


def normalize_numbered_blanks(text: str) -> str:
    """印刷空位编号统一为 LaTeX 形式: ___21___ / 21____ → $ \\underline{21} $"""
    text = FULL_BLANK_RE.sub(lambda m: f"$ \\underline{{{int(m.group(1))}}} $", text)
    text = TRAIL_BLANK_RE.sub(lambda m: f"$ \\underline{{{int(m.group(1))}}} $", text)
    # 清理 OCR 冗余尾下划线: $ \underline{32} $____ → $ \underline{32} $
    text = re.sub(r"(\$?\s*\\underline\{\d{1,2}\}\s*\$?)\s*_{2,}", r"\1", text)
    return text


# 语法填空空位标记: 题号标注(含外围 $) / 下划线空位
GRAMMAR_BLANK_RE = re.compile(r"\$?\s*\\underline\{(\d{1,2})\}\s*\$?|_{2,}")
# 疑似题号行/选项行(如阅读题干 "4. Why did ... ____?"),其上空位不编号
NON_GRAMMAR_LINE = re.compile(r"^\s*(?:\d{1,2}\s*[.、]|[A-Ga-g]\s*[.、])")
# 漏识别空位: word (英文提示词) 且非紧跟题号标注(如 "held (held)" / "safeguarding (safeguard)")
MISSED_BLANK_RE = re.compile(
    r"(?<![}\$])\s+([A-Za-z][A-Za-z'-]*)\s*\(([a-z][a-z'-]*)\)"
)


def mark_missed_blanks(text: str, report) -> str:
    """把 OCR 漏了手写下划线的空位(word 后跟英文提示词)转成 ____。"""
    def rep(m):
        report.grammar_missed_blanks.append(m.group(1))
        return f" ____ ({m.group(2)})"

    return MISSED_BLANK_RE.sub(rep, text)


def finalize_grammar_numbering(text: str, report, first_q, no_ask) -> str:
    """语法填空编号: 已知题号锚定位置并补全缺口;全文无题号则询问首序号后顺序编号。

    例: 空位 [_, _, 58, 59, 60, _, _, _] → 56-63(已知 58 为第 3 个空位,start=58-2)。
    疑似题号行/选项行上的空位(夹带的阅读题干等)不编号,原样保留。
    """
    lines = text.split("\n")
    blank_locs: list[tuple[str, int | None]] = []  # 按出现顺序
    excluded: set[int] = set()
    for li, ln in enumerate(lines):
        if NON_GRAMMAR_LINE.match(ln):
            excluded.add(li)
            report.grammar_excluded += len(GRAMMAR_BLANK_RE.findall(ln))
            continue
        for m in GRAMMAR_BLANK_RE.finditer(ln):
            blank_locs.append(("known", int(m.group(1))) if m.group(1) else ("unknown", None))
    if not blank_locs:
        return text
    known = [(i, n) for i, (k, n) in enumerate(blank_locs) if k == "known"]
    if known:
        i0, n0 = known[0]
        start = n0 - i0
        report.grammar_first_q = start
        report.grammar_known = [n for _, n in known]
    else:
        start = resolve_first_q(first_q, no_ask)
        report.grammar_first_q = start

    numbers: list[int] = []
    for i, (k, n) in enumerate(blank_locs):
        if k == "known":
            numbers.append(n)
            if n != start + i:
                report.grammar_numjumps.append((n, start + i))
        else:
            report.grammar_autonumbered.append(start + i)
            numbers.append(start + i)

    idx = 0

    def repl(_m):
        nonlocal idx
        num = numbers[idx]
        idx += 1
        return f"$ \\underline{{{num}}} $"

    out_lines = []
    for li, ln in enumerate(lines):
        if li in excluded:
            out_lines.append(ln)
            continue
        out_lines.append(GRAMMAR_BLANK_RE.sub(repl, ln))
    out = "\n".join(out_lines)
    # 清理题号标注后残留的孤立数字(如 "$ \\underline{41} $1 (progress)" → "$ \\underline{41} $ (progress)")
    out = re.sub(
        r"(\$?\s*\\underline\{\d{1,2}\}\s*\$?\s*)\d{1,2}(?=[\s(]|$)", r"\1", out
    )
    return out
