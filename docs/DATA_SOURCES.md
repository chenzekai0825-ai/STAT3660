# 数据来源、转换与字段

## 选题依据和实际下载

两个指标都来自世界银行 World Development Indicators（WDI，source=2），取2023年。选择该年是为了使用较完整、固定的年度截面，避免混合“各经济体最新年份”。GDP采用购买力平价和2021年不变国际元，适合比较经济体的实际产出水平；寿命是总人口出生时预期寿命（年）。数据量适中，两个指标均覆盖217个非汇总经济体的记录，其中197个有完整数值，可支持总体/地区描述统计及对数GDP回归。

原始文件保留API原始字节，不重新序列化。下载和重建分离，SAS不依赖网络。准确下载时间（香港时区）、URL、SHA-256、字节数和API版本头见 `data/raw/manifest.json`。数据会被来源修订，使用归档快照才能复现本次数据。

| 原始文件 | 官方下载地址 |
|---|---|
| countries.json | https://api.worldbank.org/v2/country?format=json&per_page=400 |
| life_2023.json | https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?date=2023&format=json&per_page=400&source=2 |
| gdp_2023.json | https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?date=2023&format=json&per_page=400&source=2 |
| life_metadata.json | https://api.worldbank.org/v2/indicator/SP.DYN.LE00.IN?format=json&source=2 |
| gdp_metadata.json | https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.PP.KD?format=json&source=2 |

指标定义：[寿命官方词汇表](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/SP.DYN.LE00.IN)、[GDP官方词汇表](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/NY.GDP.PCAP.PP.KD)。API结构：[Country API Queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898590-country-api-queries)。数据署名：World Bank, World Development Indicators，2023年观测，下载快照见manifest。授权与使用条件：[World Bank Dataset Terms of Use](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets)。保留原始来源组织说明于两个 `*_metadata.json` 中。

## 转换过程

本项目的三种输入格式是**由上述同一套真实公开数据透明转换而来**，不是三个独立调查，不暗示世界银行直接发布了这些DAT/Excel文件。

1. `countries.json` → `economies.xlsx`：`tools/build_metadata.mjs`选取代码、名称、地区、收入组，将 `region.id == 'NA'` 记为汇总项1，其余0。按代码排序；单工作表 `Economies`，首行是6个变量名，全部296行保留。名称、地区等源文本保留原样。收入组只作为目录信息，不作为2023历史收入分类分析。
2. `life_2023.json` → `life_expectancy.csv`：`tools/prepare_inputs.py`选取代码、年份、数值。JSON null写为空字段，原数值以可往返解析的十进制写出。`period_start_raw=2023-01-01`是从年度派生的**年度标记日期**，并非实际测量或采集日。
3. `gdp_2023.json` → `gdp_ppp.dat`：同脚本将每条记录写成44字节ASCII固定宽度行，无表头。代码列1–3，空格4，年份5–8，空格9，年度标记日期10–19，空格20，GDP数值或NA列21–44（右对齐）。数值用17位有效数字，避免粗略四舍五入；null写为NA。
4. 两个 `*_metadata.json` 的 `sourceNote` → `indicator_notes.csv`：保留真实说明，规范化真实换行、字面 `\n` 和空白为单空格，变为一行CSV。附独立计算的UTF-8字节数和末40字符。最长说明1342字节；SAS用4096字节接收并核对长度和结尾。故意生成200字节副本只用于展示截断损失，不进入研究分析。原说明仍在JSON中。
5. 个别汇总项在指标API的 `countryiso3code` 为空。用其 `country.id`（两位WB代码）连接目录的 `iso2Code`，取目录 `id`；不使用名称猜测。两指标各5条映射保存为 `key_mapping_audit.csv`。`iso3`变量实际指**三字符World Bank代码**，不保证每个条目都是ISO主权国家代码。

## 字段字典和键

| 字段 | SAS类型/长度 | 含义与规则 |
|---|---|---|
| iso3 | 字符3 | World Bank经济体/汇总代码；元数据唯一键 |
| country_name | 字符180 | 经济体或汇总名称 |
| region_id / region | 字符3 / 100 | 下载时地区代码及名称；NA表示汇总项 |
| income_group | 字符60 | 下载时收入分组，仅保留目录用途 |
| is_aggregate | 数值 | 1=汇总，0=经济体；分析仅用0 |
| year | 数值 | 2023；两个指标的唯一键均为(iso3,year) |
| period_start_raw / gdp_date_raw | 字符10 | 年度标记ISO日期文本，不是实际观测日 |
| period_start / gdp_date | SAS数值日期 | `YYMMDD10.`读取，以`YYMMDD10.`显示，2023-01-01内部数值为23011 |
| life_raw / gdp_raw | 字符32 / 24 | 解析前原数值字段，空白/NA保留用于审计 |
| life_exp | 数值 | 出生时预期寿命，年；SP.DYN.LE00.IN |
| gdp_ppp | 数值 | 人均GDP，PPP、2021年不变国际元；NY.GDP.PCAP.PP.KD |
| log_gdp | 数值 | GDP>0时的自然对数；缺失/非正值不取对数 |
| has_life_row / has_gdp_row / has_metadata | 数值 | 对应源**记录**是否存在，与值缺失不同 |
| merge_status | 字符32 | 三表匹配、仅目录、仅指标或缺少一个指标 |
| missing_life / missing_gdp | 数值 | 变量缺失标记1/0 |
| invalid_life / invalid_gdp | 数值 | 寿命不在(0,120]或GDP非正；本快照均0 |
| complete_case | 数值 | 可纳入回归1；否则0 |
| exclusion_reason | 字符100 | 纳入或排除原因；最终CSV保留全部经济体 |
| indicator_id / description | 字符24 / 4096 | 指标代码、规范化后的原始长说明 |

SAS先按(iso3,year)完整连接两个指标，再按iso3完整连接目录。由于固定单一年份，指标合并表也对iso3唯一；代码会验证这一点。所有重复键均导出并停止运行，不通过删重掩盖问题。30条仅目录记录均为汇总项，审计后随其余49个汇总项一起排除。指标null仍是“有记录但数值缺失”，不记作连接失败。

## 分析约定

- 描述统计：各变量分别使用可用数据，输出N、缺失N、均值、样本标准差、最小/最大值、四分位数和中位数。SAS `QNTLDEF=5`；Python用`averaged_inverted_cdf`核对。
- 回归：217经济体中197完整案例，每经济体权重相同。斜率表示GDP增加一个自然对数单位所关联的寿命变化；GDP翻倍对应 `beta × ln(2)` 年的拟合差异。不能外推为个人收入效应或因果效应。
- 诊断：常规OLS估计、普通ANOVA和CLB区间；HC3稳健标准误/检验；SPEC联合设定检验；残差图、正态Q-Q、Cook距离、杠杆值和外部学生化残差。Cook D>4/N、杠杆值>2p/N（p=2）、|外部学生化残差|>2仅标记，不自动排除。
- 完整案例可能不同于缺失GDP的经济体；地理依赖、未纳入混杂因素与线性设定均限制推断。区域分组来自当前目录。参考Python诊断的具体检验不冒充SAS SPEC，正式解释以实际SAS输出为准。
