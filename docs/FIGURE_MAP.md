# Figure map (output of the recorded SAS run)

The PNG files in `results/sas/` are identified by name (`01` to `07`). **`04_residual_normal_qq.png`
was missing from disk in the first run** because `PROC UNIVARIATE` ignores `IMAGENAME`; it is
recovered from `analysis.html` by `tools/extract_pngs.py`.

Running `python3 tools/extract_pngs.py results/sas` writes 17 figures, numbered in document order,
into `results/sas/figures/`:

| Extracted file | SAS figure | Content | Use |
|---|---|---|---|
| figure_01.png | `01_income_life_scatter` | Life expectancy against ln(GDP per capita), with the OLS line (N = 197) | **Report figure 3**, deck slide 7 |
| figure_02.png | `02_life_expectancy_by_region` | Box plot of life expectancy by region | **Report figure 1** (the dataset figure), deck slide 9 |
| figure_03.png | `03_residuals_vs_fitted` | Residuals against fitted values | Report figure 4 (top left) |
| figure_04.png | `04_residual_normal_qq` | Normal Q-Q plot of the residuals (**extracted copy only**) | Report figure 4 (top right) |
| figure_05.png | `05_cooks_distance` | Cook's distance with the 4/N reference line | Report figure 4 (bottom left) |
| figure_06.png | `06_leverage_studentized_residual` | Leverage against externally studentized residuals | Report figure 4 (bottom right) |
| figure_07.png | — | NPAR1WAY box plot of life expectancy by region | optional |
| figure_08-12.png | — | NPAR1WAY Wilcoxon, median, Van der Waerden, Savage and EDF plots | optional; useful in Q&A to show the conclusion does not depend on the scoring function |
| figure_13-14.png | — | GLM region mean plot and distribution plot | optional |
| figure_15-16.png | — | TTEST summary panel and Q-Q plot | optional |
| figure_17.png | `07_life_by_region_mean_clm` | Region means with 95% confidence limits | **Report figure 2**, deck slide 8 |

## Notes

- The report needs seven figures: figures 1, 2 and 17 as the main results, plus figures 3 to 6 as the
  diagnostics. The remaining SAS defaults should **not** be pasted into a 15-page report.
- Rename them to something readable (for example `fig_scatter.png`) before inserting them into Word,
  and state N and the data year in every caption.
- If SAS is re-run, the numbering inside `figures/` can change: read the captions printed by
  `extract_pngs.py` before matching them to this table.
