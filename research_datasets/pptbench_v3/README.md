
# PPTBench V3

PPT 排版修复评测数据集：134 个 deck × 3 难度档(medium/hard/max) × 4 信息量档 = 1608 个任务
（范围 = COMPLETED_TASKS.md 的 134 个全流程完成 case；easy 档不交付）。
每个任务给出「注入过排版缺陷的 pptx」与一句用户口径的修复请求，评测 coding agent 的修复能力。

## 目录
- `dataset_final/` — 数据主体（7.2GB）：`<deck>/input.pptx`、`defective_<tier>.delta.zip`、
  `eval_<tier>.py`、`rubric_<tier>.json`、`renders/*.webp`、`annotated/*.webp`；
  任务矩阵 `eval_tasks.jsonl`，构建记录 `build_manifest.json`，验收报告 `verify_report.json`
- `env_libreoffice/` — 渲染环境迁移包（LibreOffice 24.2.7 + 全量字体，zip 0.50GB）

## 使用
代码与完整说明：https://github.com/mrwwk/PPTBenchmark （`eval_final/` 目录）
本数据集 **revision**: `d44f4be4e4db8c66a626a1bcf74de0f2ffdd3566`

```bash
hf download Wenkaiwang/PPTBench-V3 --repo-type dataset --local-dir ./PPTBench-V3
```

## 验收
全量 1608 任务：delta 重建 sha256 1608/1608 一致；PERFECT 锚点 1608/1608；
ZERO 锚点 1608/1608（报告见 `dataset_final/verify_report.json`）。

## 来源与许可
deck 原稿来自公开模板站点/数据集（SlidesCarnival、MS Create、academic_stem 等），版权归原作者；
本仓库分发的是**派生评测工件**（缺陷稿、渲染图、标注、判分脚本）。如原作者提出异议请联系删除。

