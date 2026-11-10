# STAT 3660SEF 小组项目：2023 年经济水平与预期寿命

**研究问题：2023 年各经济体的人均实际 GDP（购买力平价）与出生时预期寿命有什么关联？各地区的寿命分布有何差异？**

使用世界银行 WDI 的公开年度数据。以经济体为单位，包括香港等地区，排除汇总区域；每个经济体等权。描述统计使用各变量的非缺失观测，回归使用完整案例。回归式为 `life_exp = intercept + beta × ln(gdp_ppp)`，关联不作因果解释。

**执行状态：SAS 源码与输入文件已完成；当前机器未发现可用 SAS 运行环境，未执行 SAS。** 已实际运行 Python，逐项核对输入并独立计算参考统计和图表，放在 `validation/python_reference/`。这些文件不冒充 SAS 输出。正式 SAS 运行后，结果写入 `results/sas/`。本项目不包含 PPT 或书面报告。工作区初始为空，未发现老师项目说明或已有选题，覆盖的是用户提供的评分清单。

## 最短运行步骤（SAS Studio）

1. 解压并将整个 `stat3660sef-group-project/` 目录上传到 SAS Studio **服务器端**文件区，保留目录结构。若平台不支持上传文件夹，先创建相应目录再上传文件。
2. 使用支持 Base SAS 9.4、SAS/STAT、ODS Graphics、`PROC IMPORT DBMS=XLSX` 的 SAS 会话。建议 UTF-8 会话；代码、CSV 和 Excel 采用 UTF-8/Unicode。
3. 打开 `run_all.sas`，只修改开头的 `%let project_root=...;` 为服务器实际路径。例如 SAS OnDemand 常见形式 `/home/u12345678/stat3660sef-group-project`；不要照抄 macOS 本机路径。路径不要含 `%` 或 `&`。
4. 在新会话中运行**整个** `run_all.sas`，无需事先运行 Python、Node 或联网下载数据。
5. 打开 `results/sas/run_all.log` 和 `RUN_STATUS.txt`。状态须为 `COMPLETED`，日志应有 `NOTE: PROJECT_COMPLETED.`；检查所有 `ERROR`、`WARNING`、无效数据、隐式类型转换、未初始化变量和重复 BY 值信息。失败时看保存的 `assertions.csv` 和审计 CSV，修复后重新整段运行。若初始路径错误，错误会出现在 Studio 原日志中。
6. 打开 `results/sas/analysis.html`，核对 CSV 和 6 类 PNG。下载结果供小组制作 PPT 和报告。下载到本机后可运行 `python3 tools/check_sas_run.py /实际下载的/results/sas`，自动检查日志、文件、断言和关键行数。

重跑会覆盖同名结果并更新完成标记。不要用旧文件的存在代替检查本次日志。若提示 XLSX 引擎或 SAS/STAT 未授权，需要改用具备这些组件的学校/OnDemand 会话；本项目不跳过 Excel 或回归要求。

## 数据与目录

| 路径 | 内容 |
|---|---|
| `run_all.sas` | 唯一入口与集中路径配置 |
| `sas/00_helpers.sas` | 导出、断言、错误停止 |
| `sas/10_import.sas` | Excel、CSV、固定宽度 DAT，类型/日期/长字段审计 |
| `sas/20_merge.sas` | 唯一键、完整连接、未匹配及样本标记 |
| `sas/30_analysis.sas` | 描述统计、极端值、回归及图表诊断 |
| `sas/snapshot_expectations.sas` | 根据冻结原始数据生成的预期行数 |
| `data/raw/` | 5 份原始 API JSON、下载链接、时间及 SHA-256 清单 |
| `data/input/` | 实际 SAS 输入：`economies.xlsx`、`life_expectancy.csv`、`gdp_ppp.dat`、`indicator_notes.csv`；另附代码映射审计 |
| `results/sas/` | 正式运行后：日志、HTML、CSV、PNG 和永久 SAS 数据集 |
| `validation/python_reference/` | 本地实际执行的 Python 参考数据、统计表及图表 |
| `docs/DATA_SOURCES.md` | 来源、转换规则、字段字典、连接键和研究限制 |
| `docs/VALIDATION.md` | 实际本地验证结果与 SAS 待验证项目 |
| `tools/` | 可重建输入、独立验证、检查下载后 SAS 输出的脚本 |

数据来源及定义：[预期寿命](https://data.worldbank.org/indicator/SP.DYN.LE00.IN)、[人均 GDP PPP（2021 年不变国际元）](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD)、[经济体 API](https://api.worldbank.org/v2/country?format=json&per_page=400)。保存的 WDI 返回头显示更新于 **2026-10-08**；选用固定 2023 年截面，下载日期和文件哈希见 `data/raw/manifest.json`。

## 评分清单对应

| 要求 | 代码位置 | SAS 运行后证据（`results/sas/`） |
|---|---|---|
| 三种输入格式 | `10_import.sas` I1–I3 | `row_counts.csv`、`metadata_import_types.csv` |
| 超长字段、缺失值 | `10_import.sas` I4；`20_merge.sas` M3 | `long_field_audit.csv`（完整4096字节与故意200字节副本对照）、`analysis_sample_flow.csv`、`final_analysis.csv` |
| 字符、数值、日期 | `10_import.sas` I1–I3 | `input_types.csv`、`date_audit.csv`、`parse_issues.csv` |
| 合并、重复键、未匹配、行数 | `20_merge.sas` M1–M4 | `duplicates_*.csv`、`merge_audit.csv`、`unmatched_rows.csv`、`row_counts.csv` |
| 导出 CSV | `run_all.sas` 末段和 `%export_csv` | `final_analysis.csv`（保留全部217经济体） |
| 最大/最小各4条 | `30_analysis.sas` C | `life_expectancy_extremes.csv`、`extreme_cutoff_audit.csv`、`extreme_cutoff_ties.csv` |
| 标题、列标签、单位 | `10_import.sas` 和 `30_analysis.sas` 的 `TITLE`/`LABEL`/`PROC PRINT` | `analysis.html` |
| 条件/循环 | `20_merge.sas` M3 的 IF；`30_analysis.sas` B 的 ARRAY/DO | 样本标记、整理后的描述统计表 |
| 至少两种可视化 | `30_analysis.sas` D | `01_income_life_scatter*.png`、`02_life_expectancy_by_region*.png` |
| 两种分析、样本量、诊断 | `30_analysis.sas` B、E、F | `descriptive_statistics.csv`、`regression_*.csv`、`03`–`06`诊断图 |

## 预期核对值与解释边界

冻结数据：Excel **296** 行（217 经济体、79 汇总项），CSV **266** 行，DAT **266** 行；指标连接 **266** 行，加入全部目录后 **296** 行，其中 **30** 行仅有目录且均属汇总项。排除79汇总项后仍保留 **217** 行；寿命缺失 **0**，GDP缺失 **20**；回归 **197** 行。唯一键、日期解析错误和未找到目录的指标行均应为 **0**。最长说明为 **1,342字节**。这些是实际本地核对值；SAS 仍须复核。

极端值只排除寿命缺失，按寿命排序，遇并列按代码升序恰取4条；另列第四位所有并列成员。缺失不填零、不均值插补、不自动删异常值。HC3处理标准误的异方差稳健性；CLB配合HCC请求常规和稳健置信区间，普通ANOVA仍基于常规OLS，读取参数表时要分清两套结果。SPEC是联合模型设定检验，拒绝不能单独归因于异方差。残差、Q-Q、Cook距离和杠杆值图用于审查模型。地区/收入分组来自下载时目录，不是2023历史分类。完整案例可能有选择偏差，模型未控制其他社会经济因素。

本地验证可重跑：`python3 tools/prepare_inputs.py`（离线重建CSV/DAT）及 `python tools/validate_inputs.py`（需 pandas、numpy、scipy、statsmodels、matplotlib、openpyxl；openpyxl仅读取）。只有明确需要更新数据时才用 `prepare_inputs.py --download`；刷新后必须同时重建Excel并重新核对样本。Excel转换脚本为 `tools/build_metadata.mjs`，需要提供 `@oai/artifact-tool` 的Node环境；正常SAS复现直接使用已提供的Excel。
