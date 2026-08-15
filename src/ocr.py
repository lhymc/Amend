"""PaddleOCR-VL API 封装,基于 ~/Desktop/.drop/ocr.py。

提交本地文件(PDF / 图片),轮询至完成,返回逐页 markdown 文本与图片映射。
"""
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

JOB_URL = os.environ.get(
    "AMEND_OCR_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
)
# Token 优先级: 环境变量 AMEND_OCR_TOKEN > 项目根 .token 文件(gitignored,不入库)
TOKEN = os.environ.get("AMEND_OCR_TOKEN", "")
if not TOKEN:
    _token_file = Path(__file__).resolve().parent.parent / ".token"
    if _token_file.exists():
        TOKEN = _token_file.read_text(encoding="utf-8").strip()
if not TOKEN:
    raise RuntimeError(
        "未配置 OCR token: 请设置环境变量 AMEND_OCR_TOKEN,或在项目根目录创建 .token 文件"
    )
MODEL = "PaddleOCR-VL-1.6"
POLL_INTERVAL = 5  # 秒
JOB_TIMEOUT = 1800  # 秒

OPTIONAL_PAYLOAD = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}


@dataclass
class Page:
    text: str
    images: dict = field(default_factory=dict)  # 相对路径(如 imgs/x.jpg) -> URL


def ocr_file(file_path: Path, timeout: int = JOB_TIMEOUT) -> list[Page]:
    """OCR 一个本地文件,返回逐页结果。失败抛异常。"""
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    headers = {"Authorization": f"bearer {TOKEN}"}
    data = {"model": MODEL, "optionalPayload": json.dumps(OPTIONAL_PAYLOAD)}
    with open(file_path, "rb") as f:
        resp = requests.post(JOB_URL, headers=headers, data=data, files={"file": f})
    if resp.status_code != 200:
        raise RuntimeError(f"OCR 提交失败 ({resp.status_code}): {resp.text}")
    job_id = resp.json()["data"]["jobId"]
    print(f"  OCR job: {job_id}")

    jsonl_url = None
    deadline = time.time() + timeout
    while True:
        if time.time() > deadline:
            raise TimeoutError(f"OCR 超时 ({timeout}s): {file_path.name}")
        r = requests.get(f"{JOB_URL}/{job_id}", headers=headers)
        r.raise_for_status()
        state = r.json()["data"]["state"]
        if state in ("pending", "running"):
            try:
                p = r.json()["data"]["extractProgress"]
                print(
                    f"  OCR {state}: {p.get('extractedPages')}/{p.get('totalPages')} 页"
                )
            except (KeyError, AttributeError):
                print(f"  OCR {state}...")
            time.sleep(POLL_INTERVAL)
            continue
        if state == "failed":
            raise RuntimeError(f"OCR 失败: {r.json()['data'].get('errorMsg')}")
        if state == "done":
            jsonl_url = r.json()["data"]["resultUrl"]["jsonUrl"]
            break

    jsonl = requests.get(jsonl_url)
    jsonl.raise_for_status()
    pages = []
    for line in jsonl.text.splitlines():
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
        for res in result.get("layoutParsingResults", []):
            md = res.get("markdown", {}) or {}
            pages.append(
                Page(text=md.get("text", "") or "", images=dict(md.get("images", {}) or {}))
            )
    if not pages:
        raise RuntimeError("OCR 未返回任何页面结果")
    return pages


def download_images(pages: list[Page], out_dir: Path) -> int:
    """按 markdown 中引用的相对路径下载图片到 out_dir,返回下载数。"""
    n = 0
    for page in pages:
        for rel, url in page.images.items():
            target = out_dir / rel
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            resp = requests.get(url)
            resp.raise_for_status()
            target.write_bytes(resp.content)
            n += 1
    return n
