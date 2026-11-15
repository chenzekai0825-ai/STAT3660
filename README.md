# STAT 3660SEF 小组项目：2023 年经济水平与预期寿命

**研究问题：2023 年各经济体的人均实际 GDP（购买力平价）与出生时预期寿命有什么关联？各地区的寿命分布有何差异？收入水平的差异能不能解释这些地区差异？**

使用世界银行 WDI 的公开年度数据。以经济体为单位，包括香港等地区，排除汇总区域；每个经济体等权。描述统计使用各变量的非缺失观测，回归使用完整案例。回归式为 `life_exp = intercept + beta × ln(gdp_ppp)`，关联不作因果解释。

## 执行状态

- **SAS 已实际运行并通过全部断言**：SAS 9.04.01M8P02222023，2026-11-16 跑完，`results/sas/RUN_STATUS.txt` 首行为 `COMPLETED`，`run_all.log` 中 **0 ERROR / 0 WARNING**，29 项断言全部 `passed=1`。
- 输入侧另有 45 项独立 Python 核对，见 `docs/VALIDATION.md`。
- 报告与 PPT 骨架已用真实 SAS 输出填好：`docs/REPORT_DRAFT.md`（15 页）、`docs/PPT_OUTLINE.md`（12 页 + Q&A）。
- 已知两个可接受的小瑕疵，均已处理：
  1. `04_residual_normal_qq.png` 本次未落到磁盘（PROC UNIVARIATE 的 QQ 图不遵循 `imagename`），已用 `tools/extract_pngs.py` 从 `analysis.html` 提取；
  2. `07_life_by_region_mean_clm` 的 `DATALABEL` 会把三个统计量以全精度叠印在坐标轴上，已在该图去掉 `DATALABEL`（重跑后即生效）。
  图表对照见 `docs/FIGURE_MAP.md`。

## 最短运行步骤（SAS Studio）

1. 把整个 `STAT3660/` 目录上传到 SAS Studio **服务器端**文件区，保留目录结构（`data/`, `sas/`, `run_all.sas`）。
2. 使用支持 Base SAS 9.4、SAS/STAT、ODS Graphics、`PROC IMPORT DBMS=XLSX` 的会话。建议 UTF-8 会话。
3. 打开 `run_all.sas`。默认路径是 `/home/&sysuserid/STAT3660`，如果你上传到了别处，只改这一行 `%let project_root=...;`。路径不要含 `%` 或 `&`。
4. 在新会话中运行**整个** `run_all.sas`。不需要先跑 Python，也不需要联网。
5. 检查 `results/sas/run_all.log` 与 `RUN_STATUS.txt`：状态须为 `COMPLETED`，日志应有 `NOTE: PROJECT_COMPLETED.`；逐个看 `ERROR`、`WARNING`、`NOTE: Invalid data`、`NOTE: ... converted to`、`NOTE: repeats of BY values`。
6. 打开 `results/sas/analysis.html`，核对 CSV 和 7 张 PNG。下载结果后运行 `python3 tools/check_sas_run.py /实际下载的/results/sas` 自动验收（退出码 0 才算通过）。

重跑会覆盖同名结果并更新完成标记。不要用旧文件的存在代替检查本次日志。

## 数据与目录

| 路径 | 内容 |
|---|---|
| `run_all.sas` | 唯一入口与集中路径配置 |
| `sas/00_helpers.sas` | 导出、断言、失败即停 |
| `sas/10_import.sas` | Excel / CSV / 固定宽度 DAT 读取，类型、日期、长字段审计 |
| `sas/20_merge.sas` | 唯一键、完整连接、未匹配与样本标记 |
| `sas/30_analysis.sas` | 描述统计、极端值、OLS 回归与诊断图 |
| `sas/35_inference.sas` | 统计推断：Kruskal-Wallis、ANOVA（Levene/Welch）、双样本 t、相关系数、均值置信区间图 |
| `sas/snapshot_expectations.sas` | 由冻结原始数据生成的预期行数 |
| `data/raw/` | 5 份原始 API JSON、下载链接、时间与 SHA-256 清单 |
| `data/input/` | SAS 实际输入：`economies.xlsx`、`life_expectancy.csv`、`gdp_ppp.dat`、`indicator_notes.csv`、`indicator_vintage.csv`；另附代码映射审计 |
| `results/sas/` | 真实 SAS 输出：日志、HTML、CSV、PNG（`figures/` 为从 HTML 提取的图） |
| `validation/python_reference/` | 本地实际执行的 Python 参考数据、统计表与图表 |
| `docs/DATA_SOURCES.md` | 来源、转换规则、字段字典、连接键与研究限制 |
| `docs/VALIDATION.md` | 实际本地验证结果与 SAS 尚待验证项 |
| `docs/REPORT_DRAFT.md` | 15 页报告骨架（按评分表的六节结构） |
| `docs/PPT_OUTLINE.md` | 10 分钟汇报的 12 页大纲与分工，数字已填好 |
| `docs/FIGURE_MAP.md` | 17 张提取图与 7 张报告图的对照表 |
| `tools/` | 重建输入（openpyxl）、独立验证、下载后 SAS 输出验收、从 HTML 提取图 |

数据来源及定义：[预期寿命](https://data.worldbank.org/indicator/SP.DYN.LE00.IN)、[人均 GDP PPP（2021 年不变国际元）](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD)、[经济体 API](https://api.worldbank.org/v2/country?format=json&per_page=400)。保存的 WDI 返回头显示更新于 **2026-10-08**，下载于 **2026-11-08**；选用固定 2023 年截面，下载日期和文件哈希见 `data/raw/manifest.json`。

## 三种输入格式的来历（要能答出来）

三种格式都来自**同一套真实公开数据**，不是三个独立调查，也不暗示世行直接发布了这些 DAT/Excel 文件：

| 格式 | 文件 | 读取方式 | 承担的内容 |
|---|---|---|---|
| Excel | `economies.xlsx` | `PROC IMPORT DBMS=XLSX` | 296 个经济体/汇总项的目录（代码、名称、地区、收入组） |
| 分隔符 | `life_expectancy.csv` | `DATA` 步 + `INFILE DSD` | 预期寿命观测值 |
| 定宽原始 | `gdp_ppp.dat` | `DATA` 步 + 列指针 `@1 @5 @10 @21` | 人均 GDP，44 字节定宽，`NA` 为缺失哨兵 |

另外两份是**真实的源数据字段**，不是为评分造的：`indicator_notes.csv` 是世界银行指标定义原文（最长 1,342 字节），`indicator_vintage.csv` 是 API 返回的 `lastupdated`（2026-10-08）与我们下载快照的日期（2026-11-08），两列都读成 SAS 日期。

## 评分清单对应

| 要求 | 代码位置 | SAS 运行后证据（`results/sas/`） |
|---|---|---|
| 三种输入格式 | `10_import.sas` I1–I3 | `row_counts.csv`、`metadata_import_types.csv`、`input_types.csv` |
| 超长字段、缺失值 | `10_import.sas` I4；`20_merge.sas` M3 | `long_field_audit.csv`（1,342 字节 vs 200 字节缓冲的损失）、`analysis_sample_flow.csv` |
| 字符、数值、日期 | `10_import.sas` I1–I5 | `input_types.csv`、`date_audit.csv`、`indicator_vintage_audit.csv`、`parse_issues.csv` |
| 合并、重复键、未匹配、行数 | `20_merge.sas` M1–M4 | `duplicates_*.csv`、`merge_audit.csv`、`unmatched_rows.csv`、`row_counts.csv` |
| 导出 CSV | `run_all.sas` 末段和 `%export_csv` | `final_analysis.csv`（保留全部 217 经济体） |
| 最大/最小各 4 条 | `30_analysis.sas` C | `life_expectancy_extremes.csv`、`extreme_cutoff_audit.csv`、`extreme_cutoff_ties.csv` |
| 标题、列标签、单位 | `10_import.sas`、`30_analysis.sas`、`35_inference.sas` 的 `TITLE`/`LABEL`/`PROC PRINT` | `analysis.html` |
| 条件/循环 | `20_merge.sas` M3 的 IF；`30_analysis.sas` B 的 ARRAY/DO | 样本标记、整理后的描述统计表 |
| 至少两种可视化（实为 3 类 7 张） | `30_analysis.sas` D；`35_inference.sas` H6 | 散点+回归线、分组箱线图、**带 95% 置信限的柱状图**，以及 4 张回归诊断图 |
| 两种以上分析（实为统计推断+描述统计+回归） | `30_analysis.sas` B/E/F；`35_inference.sas` H1–H4 | `descriptive_statistics.csv`、`regression_*.csv`、`region_summary.csv`、`analysis.html` 里的 KW/ANOVA/t/相关结果 |

## 预期核对值与解释边界

冻结数据：Excel **296** 行（217 经济体、79 汇总项），CSV **266** 行，DAT **266** 行；指标连接 **266** 行，加入全部目录后 **296** 行，其中 **30** 行仅有目录且均属汇总项。排除 79 汇总项后保留 **217** 行；寿命缺失 **0**，GDP 缺失 **20**；回归 **197** 行。唯一键、日期解析错误和未找到目录的指标行均应为 **0**。最长说明为 **1,342 字节**；vintage 表 **2** 行。这些是实际本地核对值；SAS 仍须复核。

极端值只排除寿命缺失，按寿命排序，遇并列按代码升序恰取 4 条；另列第四位所有并列成员。缺失不填零、不均值插补、不自动删异常值。HC3 处理标准误的异方差稳健性；CLB 配合 HCC 请求常规和稳健置信区间，普通 ANOVA 仍基于常规 OLS，读取参数表时要分清两套结果。SPEC 是联合模型设定检验，拒绝不能单独归因于异方差。残差、Q-Q、Cook 距离和杠杆值图用于审查模型。地区/收入分组来自下载时目录，不是 2023 历史分类。完整案例可能有选择偏差，模型未控制其他社会经济因素。**地区间检验（KW/ANOVA/t）回答"差异是否大于随机波动"，回归回答"关联有多大"，两者不能互相替代。**

## 本地复现

```
python3 tools/prepare_inputs.py     # 从冻结 JSON 重建全部输入（含 openpyxl 生成 Excel）
python3 tools/validate_inputs.py    # 45 项独立核对 + Python 参考输出
python3 tools/check_sas_run.py results/sas   # SAS 跑完后验收
python3 tools/extract_pngs.py results/sas    # 从 analysis.html 提取图（PNG 没落到磁盘时用）
```

需要 pandas、numpy、scipy、statsmodels、matplotlib、openpyxl（版本见 `tools/python-reference-versions.txt`）。只有明确需要更新数据时才用 `prepare_inputs.py --download`；刷新后必须重新核对样本与期望行数。
