# Amend

高中英语试卷错题录入工作流:试卷扫描件(PDF / 图片)→ 结构化 Markdown 错题本,纯规则清洗,零依赖(仅 requests)。

## 特性

- **输入**:全图片 PDF / 图片,丢进 `input/` 批处理;一份试卷输出一个 md
- **文章结构**:每篇文章一个 `##` 标题块,块间 `---` 分隔,编辑器大纲里拖拽即可调序
- **快速删题**:每题用 `<!-- qN -->` 注释边界包裹,删除整个注释块即可,不用框选文字
- **完形选项表每行一题**:跨行选项自动合并、缺失题号按序补上、未扫到的选项留空(`44. A.  B. familiar …`)、LaTeX array 选项自动解析
- **完形填回**:做对的题在选项行尾写答案标记(`→ A`、`= A`、`> A`、`(A)` 或行尾直接写字母),运行 fill.py 把答案填回正文(加粗)并删除该选项行
- **语法填空编号**:已知题号锚定位置补全缺口(如 `58` 在第 3 空 → 56-63);OCR 漏识别的手写答案自动补为空位;中文手写笔记(如"伴随状语")删除但不占空位
- **去手写**:手写下划线/波浪线删除,保留完形/语法填空的题目序号下划线与词义猜测词(题干含 `underlined`/`下划线`/`加粗` 等,规则表可扩展)
- **清洗报告**:每次生成 `report.md`,列出去重行、剥离的答案前缀、删除的划线、补的题号、漏识别空位,便于人工抽查

## 安装

```bash
pip install -r requirements.txt
```

## 配置 OCR Token

OCR 使用 PaddleOCR, 请在 https://aistudio.baidu.com/account/accessToken 获取访问令牌

`src/ocr.py` 按以下优先级读取 token(不入库):

1. 环境变量 `AMEND_OCR_TOKEN`
2. 项目根目录 `.token` 文件(文件内容为 token 字符串,已被 .gitignore 排除)

```bash
echo "你的token" > .token   # 或 export AMEND_OCR_TOKEN=你的token
```

## 使用

```bash
# 处理 input/ 下所有 PDF/图片
python -m src.main

# 处理指定文件
python -m src.main 试卷.pdf 1.jpeg

# 语法填空无任何题号时,免询问从 1 自动编号
python -m src.main --no-ask --first-q 1

# 完形填回:先在 md 选项行尾加标记(21. A. … D. … → A,或 = A / > A / (A) / 裸字母),再执行
python -m src.fill output/<日期>-<卷名>/<日期>-<卷名>.md
```

输出:`output/<日期>-<输入名>/` 下含 `<日期>-<输入名>.md`、`report.md`、`imgs/`(试卷配图)。

### 输出示例

```markdown
# 2026-08-15-试卷

## 阅读理解

Passage text…

<!-- q1 -->
1. What is the passage mainly about?
A. … B. … C. … D. …
<!-- /q1 -->

---

## 完形填空

Marcus was the type of person … $ \underline{21} $ …

21. A. decent B. tolerant C. distant D. selfish
22. …

---

## 语法填空

… who  $ \underline{36} $ (brave) face sandstorms …

$ \underline{37} $ (ensure) safe and smooth journeys.
```

## 项目结构

```
Amend/
├── input/            # 放入待处理的 PDF / 图片
├── output/           # 生成的错题 md + report.md + imgs/(gitignored)
├── specs/            # 设计规格文档(访谈产物)
├── src/
│   ├── ocr.py        # PaddleOCR-VL API 封装
│   ├── rules.py      # 清洗规则(题型标题/词义猜测题干模式集中维护,随案例扩展)
│   ├── structure.py  # 文章分割、标题、注释边界、md 组装
│   ├── fill.py       # 完形填回
│   ├── report.py     # 清洗报告
│   └── main.py       # 批处理入口
└── requirements.txt
```

## 已知边界

- 页面缺少题型标题(如跨页续接)时,内容进入「其他(未识别区块)」并在报告中标注,可手动补 `##` 标题
- 词义猜测题的印刷下划线仅在题干命中关键词时保留;新形态在 `src/rules.py` 的 `WORD_GUESS_STEM` 中追加
- OCR 自身的乱码/公式化选项(如 `\begin{array}`)原样透传,报告可查,手动修正
- LLM 后处理(`src/llm.py`)为规格预留项,暂未实现;纯规则已覆盖核心流程
