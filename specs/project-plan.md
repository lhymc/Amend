# 项目规划:Amend

> Source: Deep Interview, 2026-08-15

## Key Points
- **项目名:Amend**(修正/补正,简洁大气;文件夹即项目根)。
- **目录结构:src 包结构**,规划:
  ```
  Amend/
  ├── input/           # 放入待处理的 PDF / 图片(批处理)
  ├── output/          # 生成的错题 md + 清洗报告
  ├── src/
  │   ├── ocr.py       # 封装 PaddleOCR API 调用(基于 ~/Desktop/.drop/ocr.py)
  │   ├── rules.py     # 清洗规则:去重、剥答案、下划线判定、序号补全
  │   ├── structure.py # 文章分割 / 标题生成 / 注释边界
  │   ├── llm.py       # 可选 LLM 后处理(默认关闭)
  │   └── main.py      # 批处理入口(input/ → output/)
  ├── report.md        # 清洗报告模板(输出到 output/)
  └── requirements.txt
  ```
- **清洗报告**:每次处理生成 `output/report.md`,列出:删除的下划线位置、去重的重复行、剥离的答案前缀、缺失/补全的题号,便于人工抽查遗漏。
- **运行方式**:把 PDF/图片丢进 `input/`,跑一次批处理,全部转完。

## 待定
- 阅读配图是否保留图片引用。
- 跨页文章接续策略确认。
- 输出 md 命名确认(`YYYY-MM-DD-<输入名>.md`)。

## v1 交付说明(2026-08-15)
- 已实现:ocr.py / rules.py / structure.py / fill.py / main.py,纯规则管线 + 完形填回。
- `llm.py` 未纳入 v1:可选 LLM 后处理需先定服务商与密钥;规则表(题型标题变体、词义猜测题干模式)在 `src/rules.py` 顶部集中维护,随案例追加。
- 实际目录:input/ output/ src/ specs/ requirements.txt。
