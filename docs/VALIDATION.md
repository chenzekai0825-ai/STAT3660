# 实际验证记录

本文件由 `tools/validate_inputs.py` 实际运行生成。**验证引擎为 Python**：它独立重算输入与参考统计，不读 SAS、不复用 SAS 逻辑。

SAS 侧已另有真实运行记录（2026-11-16，SAS 9.04.01M8P02222023）：`results/sas/RUN_STATUS.txt` 首行为 `COMPLETED`，`run_all.log` 中 0 ERROR / 0 WARNING，29 项断言全部 `passed=1`。本文档只负责输入侧核对，两者互为独立证据。

- 验证时间（香港）：2026-11-16T01:05:44+08:00
- 原始数据下载时间：2026-11-08T03:47:12+08:00
- 共 45 项检查通过；0 项失败。逐项记录见 `validation/input_checks.csv`。
- 5 个原始 JSON 文件的 SHA256 与冻结清单一致，分页均完整。
- Excel：296 行、6 字段，逐单元格与原始元数据对照通过。
- 寿命 CSV：266 行；GDP DAT：266 行，每行恰好 44 个 ASCII 字节。
- 两个指标表 `(iso3, year)` 唯一，逐个值与原始 JSON 对照通过，无截断或人为填补。
- 两份输入的全部日期均解析为 2023-01-01。这是年度起始标记，并非采集日期。
- 长字段最大 1,342 字节，与原始 `sourceNote` 逐字符一致；输入文件本身不含任何"预期长度"列，200 字节缓冲会截断 GDP 指标说明（SAS 侧现场验证）。
- 指标 vintage 日期：`last_updated` = SP.DYN.LE00.IN = 2026-10-08, NY.GDP.PCAP.PP.KD = 2026-10-08，取自 API 响应头 `lastupdated`，与冻结 JSON 一致。
- 指标合并为 266 行，未匹配 0 行。与元数据完整合并后 296 行，其中 30 行只存在元数据，全部为汇总项目。共排除 79 个汇总项目。
- 排除汇总项目后 217 个经济体：寿命缺失 0 个、GDP 缺失 20 个；回归完整案例 197 个。GDP 缺失保持缺失，未替为 0。
- 最终参考 CSV 已重新读回并确认 217 行；含是否进入回归及排除原因。使用 17 位有效数字导出，全部数值字段读回后与内存值完全一致，缺失值保持缺失。

## 实际算出的 Python 参考结果

等权横截面 OLS：`life_exp = intercept + slope × ln(gdp_ppp)`。样本量 197，截距 22.567093，斜率 5.267173，R² = 0.741913，RMSE = 3.613387 年。斜率 HC3 标准误 0.210675。这些是关联，不能解释为收入增长造成寿命增长。

参考文件都放在 `validation/python_reference/`，文件名包含 `reference`。包括最终参考 CSV、分区域描述统计、最大最小各 4 条、边界并列审计、回归系数/置信区间/拟合统计、逐经济体诊断，以及散点图、箱线图、残差/QQ图。正式 SAS 输出目录是 `results/sas/`，两者分开保存。

模型标记 Cook's D > 4/n、leverage > 4/n、|外部学生化残差| > 2，标记不导致自动删行。Python 额外输出 White LM、Koenker-Breusch-Pagan LM 和 Shapiro-Wilk 检验；White LM **不是** SAS `SPEC` 联合模型设定检验，不能要求两者 p 值一致。HC3 参考区间使用残差自由度的 t 分布。核对 SAS 输出时，应按实际列标签区分常规 OLS 与 HC3 区间，分别比较 `ols_ci_*` 与 `hc3_ci_*`，同时确认 t 分布或渐近分布约定，不混用两类标准误。描述统计采用样本标准差及 NumPy `averaged_inverted_cdf` 分位数，与 SAS `QNTLDEF=5` 对应。

## SAS 侧的验收方式（已执行一次）

1. 按主 README 上传整个项目并运行 `run_all.sas`；`results/sas/` 下的日志、CSV 与 PNG 就是本文档对应的 SAS 证据。
2. 下载结果后运行 `python3 tools/check_sas_run.py results/sas`：检查完成标记、断言、行数、每个原始数值是否与冻结 JSON 一致。
3. 核对系数、R²、RMSE、样本量是否与本参考结果一致——实际运行值：截距 22.56709、斜率 5.26717、R² 0.7419、RMSE 3.61339、N 197，与本文档完全一致。
4. SAS 的 SPEC 与 TEST 结果只存在于 `analysis.html`（其 ODS 表名随版本变化），核对方法见 `docs/FIGURE_MAP.md` 与 README。

重跑本地验证：安装上述 Python 包后执行 `python tools/validate_inputs.py`。本次使用 Python 3.12.7，主要依赖版本见 `validation/validation_summary.json`。
