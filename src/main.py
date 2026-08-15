"""Amend 批处理入口。

用法:
  python -m src.main                 # 处理 input/ 下所有 PDF/图片
  python -m src.main a.pdf b.jpg     # 处理指定文件
  python -m src.main --first-q 1     # 语法填空无序号时从 1 自动编号(跳过询问)
"""
import argparse
import sys
from datetime import date
from pathlib import Path

from . import ocr, structure
from .report import Report

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def process_file(path: Path, out_root: Path, first_q, no_ask) -> Path:
    stem = path.stem
    stamp = date.today().isoformat()
    out_dir = out_root / f"{stamp}-{stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = Report()
    report.title = f"{stamp}-{stem}"
    print(f"== {path.name}")
    pages = ocr.ocr_file(path)
    report.ocr_pages = len(pages)
    report.images = ocr.download_images(pages, out_dir)
    md_text = structure.build(pages, stem, report, first_q=first_q, no_ask=no_ask)
    md_path = out_dir / f"{stamp}-{stem}.md"
    md_path.write_text(md_text, encoding="utf-8")
    (out_dir / "report.md").write_text(report.render(), encoding="utf-8")
    print(f"  ✓ {md_path.relative_to(ROOT)}")
    return md_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Amend: 高中英语试卷错题录入工作流")
    ap.add_argument("files", nargs="*", help="输入文件;缺省处理 input/ 目录")
    ap.add_argument("--first-q", type=int, default=None, help="语法填空无序号时的首题号(免询问)")
    ap.add_argument("--no-ask", action="store_true", help="不交互询问,自动编号从 1 起")
    args = ap.parse_args(argv)

    if args.files:
        files = [Path(f) for f in args.files]
    else:
        files = sorted(
            p for p in INPUT_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.startswith(".")
        )
    if not files:
        print(f"input/ 下没有可处理的 PDF/图片: {INPUT_DIR}")
        return 1
    for f in files:
        try:
            process_file(f, OUTPUT_DIR, args.first_q, args.no_ask)
        except Exception as e:  # noqa: BLE001 — 单文件失败不影响批处理
            print(f"  ✗ {f.name}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
