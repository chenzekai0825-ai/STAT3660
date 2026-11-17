# STAT 3660SEF Group Project — Income and Life Expectancy in 2023

**Research question.** How strongly is GDP per capita (PPP) associated with life expectancy at
birth across economies in 2023? Do the seven World Bank regions actually differ in longevity, and
are those differences larger than sampling noise? And where does the income–longevity regularity
visibly fail?

The unit of analysis is the **economy**, not the individual, so every economy carries equal weight.
All figures come from a single 2023 cross-section, which avoids mixing "latest available year"
values collected up to a decade apart. Descriptive statistics use each variable's non-missing
observations; the regression uses complete cases. The estimated relation is
`life_exp = intercept + beta × ln(gdp_ppp)` and it is reported as an **association, never as a
causal effect**.

---

## Status

- **SAS has been run and passed.** SAS 9.04.01M8P02222023, 16 November 2026.
  `results/sas/RUN_STATUS.txt` starts with `COMPLETED`, `run_all.log` contains **0 ERROR and
  0 WARNING**, and all **29 automated assertions** report `passed=1`.
- Inputs are additionally verified by 45 independent Python checks that never read SAS output
  (see `docs/VALIDATION.md`). The two verifications agree: intercept 22.56709, slope 5.26717,
  R² 0.7419, RMSE 3.61339, N = 197.
- Written report: `docs/STAT3660_Report.docx` (15 pages max, 7 figures, 9 tables).
- Presentation: `docs/STAT3660_Slides.pptx` (12 slides, speaker notes included).

Two minor blemishes, both handled and documented:

1. `04_residual_normal_qq.png` is produced by `PROC UNIVARIATE`, which ignores `IMAGENAME`, so the
   file is not written next to the other plots. It is recovered from `analysis.html` by
   `tools/extract_pngs.py`; see `docs/FIGURE_MAP.md`.
2. `DATALABEL` on the region bar chart printed all three statistics at full precision over the
   axis. It has been removed from `sas/35_inference.sas` and the chart is clean in the latest run.

---

## Quick start (SAS Studio)

1. Upload the whole `STAT3660/` folder to the SAS Studio **server-side** file area, preserving
   `data/`, `sas/` and `run_all.sas`.
2. Use a session with Base SAS, SAS/STAT, ODS Graphics and `PROC IMPORT DBMS=XLSX`. UTF-8 is
   recommended. `sas/00_environment_check.sas` tests every component the project needs and can be
   run on its own before anything else.
3. Open `run_all.sas`. The default path is `/home/&sysuserid/STAT3660`; change that single line only
   if the folder sits somewhere else. Avoid `%` and `&` in the path.
4. Run the **whole** program in a fresh session. No network access and no Python are required.
5. Note that `run_all.sas` redirects its own log with `PROC PRINTTO` and writes results through
   `ODS HTML5`, so the SAS Studio "Log" and "Results" tabs will look almost empty. Everything lands
   in `results/sas/`:
   - `RUN_STATUS.txt` — the first line must be `COMPLETED`
   - `run_all.log` — the log to inspect
   - `analysis.html` — every table and figure, self-contained
   - `assertions.csv` — 29 checks, all `passed=1`
   - about 25 CSVs, 7 PNGs and the permanent datasets in `datasets/`
6. After downloading `results/sas/`, verify it independently:

   ```
   python3 tools/check_sas_run.py results/sas
   ```

   Exit code 0 means: completion marker present, assertions all passed, row counts match the frozen
   expectations, and every raw value still equals the archived JSON.

---

## Repository layout

| Path | Contents |
|---|---|
| `run_all.sas` | Single entry point and the only place a path is configured |
| `sas/00_helpers.sas` | Export, assertion and fail-fast utilities |
| `sas/00_environment_check.sas` | Standalone test of REG / GLM / NPAR1WAY / TTEST / SGPLOT+CLM / XLSX |
| `sas/10_import.sas` | Excel, CSV and fixed-width DAT reading; type, date and long-field audit |
| `sas/20_merge.sas` | Key uniqueness, full joins, unmatched-record and sample flags |
| `sas/30_analysis.sas` | Descriptive statistics, extremes, OLS regression and diagnostics |
| `sas/35_inference.sas` | Kruskal-Wallis, ANOVA (Levene/Welch), two-sample t, correlations, CLM chart |
| `sas/snapshot_expectations.sas` | Row-count expectations generated from the frozen data |
| `data/raw/` | 5 archived API responses, download URLs, timestamps and SHA-256 manifest |
| `data/input/` | The actual SAS inputs: `economies.xlsx`, `life_expectancy.csv`, `gdp_ppp.dat`, `indicator_notes.csv`, `indicator_vintage.csv`, plus a key-mapping audit |
| `results/sas/` | Real SAS output: log, HTML, CSVs, PNGs (`figures/` holds the extracted copies) |
| `validation/python_reference/` | Python reference tables and charts used to cross-check the numbers |
| `docs/DATA_SOURCES.md` | Sources, conversion rules, field dictionary, join keys and research limits |
| `docs/VALIDATION.md` | What has been verified, by which engine, and what has not |
| `docs/REPORT_DRAFT.md` | Planning draft of the report (Chinese; same content as the .docx) |
| `docs/PPT_OUTLINE.md` | Planning draft of the deck, with speaker notes and Q&A prep (Chinese) |
| `docs/FIGURE_MAP.md` | Which extracted figure goes where in the report |
| `docs/STAT3660_Report.docx` | The written report (English, 7 figures, 9 tables) |
| `docs/STAT3660_Slides.pptx` | The slide deck (English slides, speaker notes) |
| `tools/` | Input rebuild, independent validation, output checks, figure extraction, document build |

---

## Data

### Sources and snapshot

Both indicators come from the World Bank **World Development Indicators** (WDI, source 2), annual
observations for 2023:

- [Life expectancy at birth, total (years)](https://data.worldbank.org/indicator/SP.DYN.LE00.IN)
  — `SP.DYN.LE00.IN`
- [GDP per capita, PPP (constant 2021 international dollars)](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD)
  — `NY.GDP.PCAP.PP.KD`
- [Country API](https://api.worldbank.org/v2/country?format=json&per_page=400) — 296 entries, of
  which **217 economies** and **79 regional or income aggregates**

The five API responses are archived byte for byte with SHA-256 digests and timestamps in
`data/raw/manifest.json`. The API header reports the series as last updated **2026-10-08**; the
snapshot was retrieved on **2026-11-08**, 31 days later. WDI values are revised over time, which is
exactly why an archived snapshot rather than a live download is used. The data are used under the
[World Bank Dataset Terms of Use](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets).

### The three input formats

The project reads three different file formats. All three are **transparent conversions of the same
public data** — the World Bank does not itself publish these Excel and fixed-width files, and the
report says so explicitly.

| Format | File | SAS mechanism | Content | Why this format |
|---|---|---|---|---|
| Excel | `economies.xlsx` | `PROC IMPORT DBMS=XLSX` | 296 catalogue rows, 6 fields | A catalogue is a table a human maintains and reviews |
| Delimited | `life_expectancy.csv` | `DATA` step, `INFILE DSD` | 266 life-expectancy records | Narrow value range, easy to inspect by eye |
| Fixed width | `gdp_ppp.dat` | `DATA` step, column pointers `@1 @5 @10 @21` | 266 GDP records, exactly 44 bytes per line | Mimics a statistical-office export with no header, which must be parsed by position |

Two further inputs carry genuine source content rather than derived values:
`indicator_notes.csv` holds the official indicator definitions (the longest is 1,342 bytes) and
`indicator_vintage.csv` holds the API `lastupdated` date together with the retrieval date, both read
as SAS dates.

---

## Coverage of the assessment checklist

| Requirement | Where it is implemented | Evidence in `results/sas/` |
|---|---|---|
| Three input formats | `10_import.sas` I1–I3 | `row_counts.csv`, `metadata_import_types.csv`, `input_types.csv` |
| Over-long field, missing values | `10_import.sas` I4; `20_merge.sas` M3 | `long_field_audit.csv` (1,342 bytes read in full; a 200-byte buffer loses 1,142), `analysis_sample_flow.csv` |
| Character, numeric and date types | `10_import.sas` I1–I5 | `input_types.csv`, `date_audit.csv`, `indicator_vintage_audit.csv`, `parse_issues.csv` |
| Merge, duplicate keys, unmatched rows | `20_merge.sas` M1–M4 | `duplicates_*.csv`, `merge_audit.csv`, `unmatched_rows.csv`, `row_counts.csv` |
| Export to CSV | `run_all.sas` and `%export_csv` | `final_analysis.csv` (all 217 economies retained) |
| Four largest and four smallest values | `30_analysis.sas` C | `life_expectancy_extremes.csv`, `extreme_cutoff_audit.csv`, `extreme_cutoff_ties.csv` |
| Headings, column labels and units | `TITLE` / `LABEL` / `PROC PRINT` throughout | `analysis.html` |
| Conditional statements and loops | `20_merge.sas` M3 (IF); `30_analysis.sas` B (ARRAY/DO) | Sample flags, reshaped descriptive table |
| At least two kinds of visualisation (actually 3 kinds, 7 charts) | `30_analysis.sas` D; `35_inference.sas` H6 | Scatter with OLS line, grouped box plot, bar chart with 95% confidence limits, plus four regression diagnostics |
| At least two kinds of analysis (actually summary statistics, inference and regression) | `30_analysis.sas` B/E/F; `35_inference.sas` H1–H4 | `descriptive_statistics.csv`, `region_summary.csv`, `regression_*.csv`, and the KW / ANOVA / t / correlation tables in `analysis.html` |

---

## Expected values (use these to check a run)

| Check | Value |
|---|---|
| Excel catalogue rows | **296** (217 economies + 79 aggregates) |
| CSV / DAT rows | **266** / **266** |
| Indicator join | **266** rows, 0 unmatched |
| Metadata full join | **296** rows, 30 of which carry only catalogue data (all aggregates) |
| Aggregates excluded | **79** |
| Retained economies | **217** |
| Missing life expectancy / missing GDP | **0** / **20** |
| Complete-case regression sample | **197** |
| Longest indicator definition | **1,342** bytes, 1 record truncated by a 200-byte buffer |
| Vintage rows | **2**, 31 days between source update and retrieval |
| Region summary rows | **7** |
| Duplicate keys, date parse errors, unmatched indicator rows | **0** |
| OLS slope / intercept / R² / RMSE | **5.26717** / **22.56709** / **0.7419** / **3.61339** |

---

## Interpretation boundaries

Missing values are never filled with zero and never imputed; the 20 economies without GDP per head
stay visible in the exported dataset but are outside the regression. Extreme values are identified
with an explicit, reproducible tie rule (ascending economy code) and are reported rather than
deleted: 22 of the 197 complete cases are flagged by the Cook's D, leverage or studentized-residual
screens and **none of them is removed**.

The regression reports both conventional and HC3 heteroskedasticity-consistent inference, and a SPEC
joint specification test (chi-square = 3.60, df = 2, p = 0.165). Levene's test rejects equal
variances across regions (p = 0.0001), so the Welch ANOVA is reported alongside the ordinary one
rather than instead of it. Region and income classifications are a download-time snapshot of the
catalogue, not a 2023 historical classification. Complete cases may differ systematically from the
economies with missing data, and education, health expenditure, institutions and geography are
uncontrolled, so the slope is an association and not a causal effect.

---

## Reproducing everything

```
python3 tools/prepare_inputs.py      # rebuild every input from the frozen JSON (openpyxl for the xlsx)
python3 tools/validate_inputs.py     # 45 independent checks + Python reference output
python3 tools/check_sas_run.py results/sas   # verify a downloaded SAS run
python3 tools/extract_pngs.py results/sas    # pull figures out of analysis.html, in document order
python3 tools/build_report_docx.py           # regenerate docs/STAT3660_Report.docx
python3 tools/build_slides_pptx.py           # regenerate docs/STAT3660_Slides.pptx
```

`prepare_inputs.py` requires `openpyxl`; `validate_inputs.py` requires `pandas`, `numpy`, `scipy`,
`statsmodels`, `matplotlib` and `openpyxl` (versions in `tools/python-reference-versions.txt`); the
document builders require `python-docx` and `python-pptx`. Only use
`prepare_inputs.py --download` when the data must be refreshed, and re-check the sample afterwards.

`FILE_SHA256.txt` covers every tracked file except itself. `data/input/economies.xlsx` is the one
deliberate exception: openpyxl writes new zip timestamps on every rebuild, so the byte hash changes
while the cell contents do not. That file is therefore verified cell by cell against
`countries.json` by `validate_inputs.py`, which is a stricter check than a byte hash.

---

## Notes

- The written report and the slides are in **English**, matching the course materials, the rubric and
  every axis label produced by SAS. The two planning drafts (`docs/REPORT_DRAFT.md`,
  `docs/PPT_OUTLINE.md`) are in Chinese; they carry the same content and are kept for the team.
- The documents are generated from `results/sas/`, so re-running SAS and then re-running the two
  builders keeps text and tables in step. Statistics that SAS prints to `analysis.html` but does not
  export (Kruskal-Wallis, ANOVA, Levene, Welch, the t test, the correlations and the SPEC test) are
  entered by hand in sections 4.3, 4.4 and 4.6 — re-check them if the sample changes.
