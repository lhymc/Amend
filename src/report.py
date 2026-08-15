"""清洗报告:记录每次处理的清理项,便于人工抽查遗漏。"""


class Report:
    def __init__(self):
        self.title = ""
        self.ocr_pages = 0
        self.images = 0
        self.sections = []  # (kind, title)
        self.unknown_blocks = 0
        self.repeated_headings = []
        self.deduped = []
        self.stripped_prefix = []
        self.underline_kept_number = 0
        self.underline_kept_guess = []
        self.underline_removed = []
        self.grammar_answer_removed = []
        self.grammar_missed_blanks = []
        self.grammar_known = []
        self.grammar_autonumbered = []
        self.grammar_numjumps = []
        self.grammar_excluded = 0
        self.grammar_first_q = None
        self.reading_passages = []
        self.reading_not_split = False
        self.cloze_rebuilt = 0
        self.cloze_renumbered = []
        self.cloze_blank_options = []
        self.cloze_numjumps = []
        self.cloze_dropped = []
        self.cloze_gloss_removed = []
        self.filled = []  # "21→decent"
        self.fill_warnings = []

    def render(self) -> str:
        p = []
        p.append(f"# 清洗报告: {self.title}")
        p.append("")
        p.append(f"- OCR 页数: {self.ocr_pages}")
        p.append(f"- 下载图片: {self.images}")
        p.append("")
        p.append("## 文章结构")
        kinds = [k for k, _ in self.sections]
        p.append(f"- 识别区块(按序): {', '.join(kinds) if kinds else '无'}")
        if self.reading_passages:
            p.append(f"- 阅读分篇: {', '.join(self.reading_passages)}")
        elif self.reading_not_split:
            p.append("- 阅读未自动分篇(无 A/B/C/D 标签),整节为一块")
        if self.unknown_blocks:
            p.append(f"- 未识别区块: {self.unknown_blocks} 行(已放入「其他」块,请人工检查)")
        if self.repeated_headings:
            p.append(f"- 丢弃重复页眉标题: {len(self.repeated_headings)} 行")
        p.append("")
        p.append("## 清洗")
        p.append(f"- 相邻重复行去重: {len(self.deduped)} 行")
        if self.deduped:
            p.append(f"  - 示例: {self._sample(self.deduped)}")
        p.append(f"- 剥离答案前缀: {len(self.stripped_prefix)} 行")
        if self.stripped_prefix:
            p.append(f"  - 示例: {self._sample(self.stripped_prefix)}")
        p.append(f"- 下划线删除(保留印刷文本): {len(self.underline_removed)} 处")
        if self.underline_removed:
            p.append(f"  - 示例: {self._sample(self.underline_removed)}")
        p.append(f"- 下划线保留(题目序号): {self.underline_kept_number} 处")
        p.append(f"- 下划线保留(词义猜测): {len(self.underline_kept_guess)} 处")
        if self.underline_kept_guess:
            p.append(f"  - 示例: {self._sample(self.underline_kept_guess)}")
        p.append(f"- 语法填空删除手写答案: {len(self.grammar_answer_removed)} 处")
        if self.grammar_answer_removed:
            p.append(f"  - 示例: {self._sample(self.grammar_answer_removed)}")
        p.append("")
        p.append("## 语法填空编号")
        if self.grammar_first_q is not None:
            total = len(self.grammar_known) + len(self.grammar_autonumbered)
            p.append(f"- 编号: 首序号 {self.grammar_first_q},共 {total} 题")
            if self.grammar_known:
                p.append(f"- 保留原序号: {', '.join(map(str, self.grammar_known))}")
            if self.grammar_autonumbered:
                p.append(f"- 补全序号: {', '.join(map(str, self.grammar_autonumbered))}")
            if self.grammar_missed_blanks:
                p.append(f"- 漏识别空位补上: {len(self.grammar_missed_blanks)} 处({self._sample(self.grammar_missed_blanks)})")
            if self.grammar_excluded:
                p.append(f"- 题号行/选项行空位不编号(原样保留): {self.grammar_excluded} 处")
            if self.grammar_numjumps:
                p.append(f"- 题号异常(请核对): {self.grammar_numjumps}")
        else:
            p.append("- 无空位")
        p.append("## 完形选项表")
        if self.cloze_rebuilt:
            p.append(f"- 重构题目行: {self.cloze_rebuilt} 题(每行一题)")
            if self.cloze_renumbered:
                p.append(f"- 补题号: {', '.join(map(str, self.cloze_renumbered))}")
            if self.cloze_blank_options:
                p.append(f"- 缺选项留空: {', '.join(map(str, dict.fromkeys(self.cloze_blank_options)))}")
            if self.cloze_numjumps:
                p.append(f"- 题号跳变(检查是否漏题): {self.cloze_numjumps}")
            if self.cloze_dropped:
                p.append(f"- 丢弃杂行: {len(self.cloze_dropped)} 行")
                p.append(f"  - 示例: {self._sample(self.cloze_dropped)}")
            if self.cloze_gloss_removed:
                p.append(f"- 删除选项手写中文注释: {len(self.cloze_gloss_removed)} 处")
                p.append(f"  - 示例: {self._sample(self.cloze_gloss_removed)}")
        else:
            p.append("- 无完形选项表或无需重构")
        p.append("")
        p.append("## 填回(fill.py)")
        if self.filled:
            p.append(f"- 已填充: {', '.join(self.filled)}")
        else:
            p.append("- 本次未运行 fill.py")
        if self.fill_warnings:
            p.append(f"- 警告: {', '.join(self.fill_warnings)}")
        return "\n".join(p).rstrip() + "\n"

    @staticmethod
    def _sample(items: list[str], n: int = 3) -> str:
        return "; ".join(repr(x) for x in items[:n])
