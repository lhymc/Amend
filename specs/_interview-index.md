# Interview: 高中英语试卷错题录入工作流(Amend)

**Date:** 2026-08-15
**Status:** Complete(8 轮,medium)
**Depth:** medium

## Themes Discovered
1. 概览与目标:OCR 后手工清理 → 自动化;打印复习 + 存档;VS Code/Obsidian/Typora 编辑
2. 颗粒度:一份试卷一个 md;文章 `---` 分隔;题型 = 阅读/七选五/完形/语法填空;只留题目
3. MD 结构:文章 = `##` 标题块(大纲调序);删题 = `<!-- qNN -->` 注释边界;完形选项表逐行
4. 清洗规则:删手写下划线(数字序号、词义猜测词保留);剥答案前缀;去重;语法填空序号补全
5. 管线:纯规则 v1,LLM 可选;input/ 批处理;output/ 输出 + report.md
6. 项目规划:命名 Amend;src 包结构;清洗报告
7. 边界:跨页标题驱动合并;配图保留;命名 `日期-输入名`
8. 完形填回:非错题选项行标 `→ A`,脚本填回正文加粗、删选项行

## Files Created
- `_interview-index.md` — 本索引
- `overview.md` — 角色、现状、用途、编辑环境
- `granularity.md` — 文件/文章/题目粒度、题型范围、内容字段
- `md-structure.md` — 标题、分割线、注释边界、调序/删题机制
- `cleaning-rules.md` — 下划线判定、答案剥离、序号补全、去重
- `project-plan.md` — 项目名 Amend、src 目录结构、清洗报告
- `fill-in.md` — 完形非错题填回原文机制
- `_summary.md` — 综合摘要(需求映射表)
- `_open-questions.md` — 待决细节与实现验证清单

## 输出
访谈产物即设计规格,位于:
`~/Documents/interviews/exam-wrong-questions-2026-08-15/`
