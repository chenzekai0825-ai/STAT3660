# 图表对照表（本次 SAS 运行产出）

`results/sas/` 里的 PNG 由图名直接标识（`01`–`07`）。其中 **`04_residual_normal_qq.png` 本次没有落到磁盘**（PROC UNIVARIATE 的 QQ 图未按 imagename 写出），已由 `tools/extract_pngs.py` 从 `analysis.html` 补齐。

运行 `python3 tools/extract_pngs.py results/sas` 会在 `results/sas/figures/` 生成 17 张按文档顺序编号的图，对照如下：

| 提取文件 | 对应 SAS 图 | 内容 | 报告/PPT 用途 |
|---|---|---|---|
| figure_01.png | `01_income_life_scatter` | ln(人均GDP) 与预期寿命散点 + OLS 拟合线（N=197） | **报告图 1**、PPT 第 7 页 |
| figure_02.png | `02_life_expectancy_by_region` | 七个地区的寿命箱线图 | **报告图 2**（Dataset 节配图）、PPT 第 9 页 |
| figure_03.png | `03_residuals_vs_fitted` | 残差 vs 拟合值 | 报告图 3（诊断） |
| figure_04.png | `04_residual_normal_qq` | 残差正态 Q-Q 图（**仅有提取版**） | 报告图 4（诊断） |
| figure_05.png | `05_cooks_distance` | Cook 距离 + 4/N 参考线 | 报告图 5（诊断） |
| figure_06.png | `06_leverage_studentized_residual` | 杠杆值 vs 外部学生化残差 | 报告图 6（诊断） |
| figure_07.png | — | NPAR1WAY：按地区的寿命箱线图 | 备选 |
| figure_08–12.png | — | NPAR1WAY 的 Wilcoxon / 中位数 / Van der Waerden / Savage / EDF 评分图 | 备选，答辩可用来说明"换评分方式结论不变" |
| figure_13–14.png | — | GLM 的地区均值拟合图与分布图 | 备选 |
| figure_15–16.png | — | TTEST 的汇总面板与 Q-Q 图 | 备选 |
| figure_17.png | `07_life_by_region_mean_clm` | 地区均值 + 95% 置信限柱状图 | **报告图 7**、PPT 第 8 页 |

## 注意

- 报告只需要 7 张：图 1、2、7（主结果）+ 图 3–6（诊断）。其余是 SAS 附带的默认图，**不要全部塞进 15 页报告**。
- 插入 Word 前把 `figure_NN.png` 重命名为 `fig1_scatter.png` 这类可读名字，并在图注里写清 N 和数据年份。
- 如果重新跑过 SAS，`figures/` 里的顺序可能与上表不同——重跑后先看 `extract_pngs.py` 打印的 alt 文本再对号。
