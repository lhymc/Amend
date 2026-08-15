# Amend

High-school English exam wrong-question workflow: scan images (PDF / photos) → structured Markdown wrong-question notebook, pure-rule cleaning, zero dependencies beyond `requests`.

## Features

- **Input**: image-only PDFs / images, dropped into `input/` and batch-processed; one exam paper → one Markdown file
- **Article structure**: each passage is a `##` heading block, blocks separated by `---`; reorder by dragging in your editor's outline view
- **Quick question deletion**: every question is wrapped in `<!-- qN -->` comment boundaries — delete the whole block, no text-box selection needed
- **Cloze options, one question per line**: multi-line options auto-merged, missing numbers filled in sequence, un-scanned options left blank (`44. A.  B. familiar …`), LaTeX `array` options auto-parsed
- **Cloze fill-back**: for questions you got right, append an answer marker at the end of the option line (`→ A`, `= A`, `> A`, `(A)`, or a bare trailing letter), run fill.py to fill the answer into the passage (bold) and remove that option line
- **Grammar-fill numbering**: known numbers anchor positions and gaps are filled (e.g. `58` at the 3rd blank → 56-63); answers whose handwriting underline OCR missed are auto-restored as blanks; handwritten Chinese notes (e.g. “伴随状语”) are removed without taking a blank slot
- **Handwriting removal**: handwritten underlines/wavy lines stripped, while cloze/grammar blank numbers and word-guess target words are kept (stem keywords like `underlined` / `下划线` / `加粗`; rule table extensible)
- **Cleaning report**: every run produces `report.md` listing deduped lines, stripped answer prefixes, removed underlines, filled numbers and restored blanks for manual spot-checks

## Install

```bash
pip install -r requirements.txt
```

## OCR Token

We use PaddleOCR, so please access https://aistudio.baidu.com/account/accessToken to get your own token.

`src/ocr.py` reads the token (never committed) in this order:

1. Environment variable `AMEND_OCR_TOKEN`
2. `.token` file at the project root (file content is the token string; gitignored)

```bash
echo "your-token" > .token   # or: export AMEND_OCR_TOKEN=your-token
```

## Usage

```bash
# Process every PDF/image in input/
python -m src.main

# Process specific files
python -m src.main paper.pdf 1.jpeg

# Grammar-fill with no numbers at all: number from 1 without prompting
python -m src.main --no-ask --first-q 1

# Cloze fill-back: mark an option line first (21. A. … D. … → A), then run
python -m src.fill output/<date>-<paper>/<date>-<paper>.md
```

Output: `output/<date>-<input-name>/` contains `<date>-<input-name>.md`, `report.md`, and `imgs/` (paper figures).

### Output Example

```markdown
# 2026-08-15-paper

## Reading

Passage text…

<!-- q1 -->
1. What is the passage mainly about?
A. … B. … C. … D. …
<!-- /q1 -->

---

## Cloze

Marcus was the type of person … $ \underline{21} $ …

21. A. decent B. tolerant C. distant D. selfish
22. …

---

## Grammar Fill-in

… who  $ \underline{36} $ (brave) face sandstorms …

$ \underline{37} $ (ensure) safe and smooth journeys.
```

## Project Structure

```
Amend/
├── input/            # drop PDFs / images here
├── output/           # generated notes + report.md + imgs/ (gitignored)
├── specs/            # design specs (interview artifacts)
├── src/
│   ├── ocr.py        # PaddleOCR-VL API wrapper
│   ├── rules.py      # cleaning rules (section titles / word-guess stem patterns, grow with cases)
│   ├── structure.py  # section splitting, headings, comment boundaries, md assembly
│   ├── fill.py       # cloze fill-back
│   ├── report.py     # cleaning report
│   └── main.py       # batch entry point
└── requirements.txt
```

## Known Limits

- Pages missing a section title (e.g. mid-article continuation) fall into the “其他(未识别区块)” block, flagged in the report; add a `##` heading manually
- Printed underlines on word-guess words are kept only when the stem matches keywords; add new forms to `WORD_GUESS_STEM` in `src/rules.py`
- OCR artifacts (mojibake, math-mode options such as `\begin{array}`) pass through as-is, listed in the report for manual fixes
- LLM post-processing (`src/llm.py`) is a reserved spec item, not implemented; the pure-rule pipeline covers the core flow
