"""文章分割与 md 生成。

- 标题驱动合并: 同一题型标题只开一次块,后续页内容追加(用户保证页序)。
- 阅读按 A/B/C/D 标签分篇;题号行包 <!-- qN --> 注释边界。
- 七选五选项包 <!-- optX --> 注释边界。
- 文章块之间用 --- 分隔。
"""
import re
from dataclasses import dataclass, field

from . import rules
from .report import Report

KIND_TITLE = {
    "阅读": "阅读理解",
    "七选五": "七选五",
    "完形": "完形填空",
    "语法填空": "语法填空",
    "其他": "其他(未识别区块)",
}


@dataclass
class Section:
    kind: str
    title: str
    lines: list = field(default_factory=list)


def split_sections(pages, report: Report) -> list[Section]:
    """跨页拼接后按题型标题分割;重复页眉并入当前块。"""
    text = "\n".join(p.text for p in pages)
    sections: list[Section] = []
    pre_lines: list[str] = []
    current: Section | None = None
    for line in text.splitlines():
        kind = rules.detect_section(line)
        if kind:
            if current is not None and current.kind == kind:
                # 同一题型标题只开一次块:重复的短标题(页眉)丢弃,长指令行并入当前块
                s = line.strip().lstrip("#").strip().strip("*").strip()
                if len(s) <= 25:
                    report.repeated_headings.append(line.strip()[:60])
                    continue
                current.lines.append(line)
                continue
            current = Section(kind=kind, title=KIND_TITLE[kind])
            sections.append(current)
            continue
        if current is None:
            pre_lines.append(line)
        else:
            current.lines.append(line)
    if pre_lines and any(l.strip() for l in pre_lines):
        sections.insert(0, Section(kind="其他", title=KIND_TITLE["其他"], lines=pre_lines))
        report.unknown_blocks = len(pre_lines)
    report.sections = [(s.kind, s.title) for s in sections]
    return sections


def resolve_first_q(first_q: int | None, no_ask: bool) -> int:
    if first_q is not None:
        return int(first_q)
    if no_ask:
        return 1
    try:
        s = input("语法填空未识别到题号,请输入第一个题号(默认 1): ").strip()
        return int(s) if s.isdigit() else 1
    except EOFError:
        return 1


def clean_section(sec: Section, report: Report, first_q, no_ask) -> None:
    """就地清洗: 下划线 → 去重 → 空位归一/编号 → 选项行规整。"""
    sec.lines = [rules.clean_underlines(l, sec.kind, report) for l in sec.lines]
    sec.lines = rules.dedupe_lines(sec.lines, report)
    if sec.kind in ("完形", "语法填空"):
        sec.lines = [rules.normalize_numbered_blanks(l) for l in sec.lines]
        if sec.kind == "语法填空":
            text = "\n".join(sec.lines)
            text = rules.mark_missed_blanks(text, report)
            text = rules.finalize_grammar_numbering(text, report, first_q, no_ask)
            sec.lines = text.split("\n")
    if sec.kind == "完形":
        sec.lines = rules.rebuild_option_table(sec.lines, report)


def split_read_passages(sec: Section, report: Report) -> list[Section]:
    """阅读分篇: 独立字母行 / Passage A / A篇 为标签。"""
    if sec.kind != "阅读":
        return [sec]
    labels = [(i, l.strip().strip(".").strip()) for i, l in enumerate(sec.lines) if rules.PASSAGE_LABEL_RE.match(l)]
    if not labels:
        report.reading_not_split = True
        return [sec]
    idxs = [i for i, _ in labels]
    titles = [f"阅读{x.upper()}" for _, x in labels]
    passages = []
    for k, i in enumerate(idxs):
        end = idxs[k + 1] if k + 1 < len(idxs) else len(sec.lines)
        body = sec.lines[i + 1:end]
        if k == 0:
            body = sec.lines[0:i] + body  # 首个标签前的指令/题头并入 A
        passages.append(Section(kind="阅读", title=titles[k], lines=body))
    report.reading_passages = titles
    return passages


def wrap_questions(sec: Section) -> list[str]:
    """阅读题号行 → <!-- qN --> … <!-- /qN --> 注释块。"""
    if sec.kind != "阅读":
        return sec.lines
    blocks: list = []
    pending_text: list[str] = []
    qnum: int | None = None
    qlines: list[str] = []

    def flush_text():
        if pending_text:
            blocks.append(("text", pending_text[:]))
            pending_text.clear()

    def flush_q():
        nonlocal qnum
        if qnum is not None:
            blocks.append(("q", qnum, qlines[:]))
            qnum = None
            qlines.clear()

    for line in sec.lines:
        m = rules.QUESTION_RE.match(line)
        if m:
            flush_text()
            flush_q()
            qnum = int(m.group(1))
            qlines = [line]
        elif qnum is not None:
            qlines.append(line)
        else:
            pending_text.append(line)
    flush_text()
    flush_q()

    out: list[str] = []
    for b in blocks:
        if b[0] == "text":
            out.extend(b[1])
        else:
            _, num, ls = b
            out.append(f"<!-- q{num} -->")
            out.extend(ls)
            out.append(f"<!-- /q{num} -->")
            out.append("")
    return out


def wrap_options(sec: Section) -> list[str]:
    """七选五选项行 → <!-- optX --> … <!-- /optX --> 注释块。

    选项块在空行或超长行处结束(正文开始)。
    """
    if sec.kind != "七选五":
        return sec.lines
    out: list[str] = []
    cur: tuple[str, list] | None = None

    def close():
        nonlocal cur
        if cur:
            out.extend([f"<!-- /opt{cur[0]} -->", ""])
            cur = None

    for line in sec.lines:
        m = re.match(r"^\s*([A-Ga-g])\s*[.、]\s", line)
        if m:
            close()
            cur = (m.group(1).upper(), [line])
            out.append(f"<!-- opt{cur[0]} -->")
            out.append(line)
        elif cur and (not line.strip() or len(line) > 100):
            close()
            if line.strip():
                out.append(line)
        elif cur:
            out.append(line)
            cur[1].append(line)
        else:
            out.append(line)
    close()
    return out


# 阅读选项行统一前置缩进(与题干视觉分层)
OPTION_INDENT_RE = re.compile(r"^\s*[A-Da-d][.、]\s")
OPTION_INDENT = "    "  # 4 空格(原 tab,改为空格便于打印预览)


def indent_option_lines(lines: list[str]) -> list[str]:
    """选项行(A. … / B. …)前置 4 空格缩进。完形选项表行以数字开头,不受影响。"""
    return [OPTION_INDENT + ln.lstrip() if OPTION_INDENT_RE.match(ln) else ln for ln in lines]


def build(pages, stem: str, report: Report, first_q=None, no_ask=False) -> str:
    """pages(ocr.Page) → 结构化错题 md 文本。"""
    sections = split_sections(pages, report)
    expanded: list[Section] = []
    for sec in sections:
        clean_section(sec, report, first_q, no_ask)
        if sec.kind == "阅读":
            expanded.extend(split_read_passages(sec, report))
        else:
            expanded.append(sec)

    blocks: list[str] = []
    for sec in expanded:
        lines = wrap_questions(sec) if sec.kind == "阅读" else wrap_options(sec)
        lines = indent_option_lines(lines)
        body = "\n".join(lines).strip("\n")
        blocks.append(f"## {sec.title}\n\n{body}".rstrip())
    md = f"# {stem}\n\n" + "\n\n---\n\n".join(blocks)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md
