#!/usr/bin/env python3
"""Validate frozen inputs and execute an independent Python reference analysis.

This is NOT a SAS runtime or SAS-log validation. Requires numpy, pandas, scipy,
statsmodels, matplotlib and openpyxl. Writes only validation/ and docs/VALIDATION.md.
Run from any directory: python tools/validate_inputs.py
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import hashlib
import json
import platform
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
import scipy
from scipy import stats
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan, het_white

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
INPUT = ROOT / 'data/input'
VALIDATION = ROOT / 'validation'
OUT = VALIDATION / 'python_reference'
OUT.mkdir(parents=True, exist_ok=True)
checks = []


def check(name, condition, detail):
    checks.append({'check': name, 'status': 'PASS' if condition else 'FAIL', 'detail': detail})
    if not condition:
        pd.DataFrame(checks).to_csv(VALIDATION / 'input_checks.csv', index=False)
        raise AssertionError(f'{name}: {detail}')


def write(name, frame):
    frame.to_csv(OUT / f'{name}.csv', index=False, float_format='%.17g')


def raw_rows(name):
    data = json.loads((RAW / name).read_text(encoding='utf-8'))
    check(f'{name}: complete API page', int(data[0]['pages']) == 1 and len(data[1]) == int(data[0]['total']),
          f"rows={len(data[1])}, total={data[0]['total']}, pages={data[0]['pages']}")
    return data[1]


def main():
    manifest = json.loads((RAW / 'manifest.json').read_text())
    for source in manifest['sources']:
        content = (RAW / source['file']).read_bytes()
        check(f"{source['file']}: SHA256", hashlib.sha256(content).hexdigest() == source['sha256'], source['sha256'])
        check(f"{source['file']}: bytes", len(content) == source['bytes'], str(len(content)))
    countries = raw_rows('countries.json')
    by_iso2 = {row['iso2Code']: row['id'] for row in countries}
    by_iso3 = {row['id']: row for row in countries}
    check('country metadata keys unique', len(by_iso2) == len(by_iso3) == len(countries), str(len(countries)))
    # Read XLSX using a different engine from the workbook author.
    wb = openpyxl.load_workbook(INPUT / 'economies.xlsx', read_only=True, data_only=True)
    check('XLSX sheet schema', wb.sheetnames == ['Economies'], repr(wb.sheetnames))
    values = list(wb['Economies'].values)
    columns = ['iso3', 'country_name', 'region_id', 'region', 'income_group', 'is_aggregate']
    check('XLSX header', list(values[0]) == columns, repr(values[0]))
    meta = pd.DataFrame(values[1:], columns=columns)
    check('XLSX rows and keys', len(meta) == len(countries) and not meta.iso3.duplicated().any(), str(len(meta)))
    for row in meta.itertuples(index=False):
        source = by_iso3[row.iso3]
        expected = (source['id'], source['name'], source['region']['id'], source['region']['value'],
                    source['incomeLevel']['value'], int(source['region']['id'] == 'NA'))
        if tuple(row) != expected:
            check('XLSX all cells equal source', False, repr((row, expected)))
    check('XLSX all cells equal source', True, f'{len(meta)} rows x 6 fields; exact text and numeric 0/1')
    check('XLSX numeric flag', all(isinstance(v, (int, float)) and v in (0, 1) for v in meta.is_aggregate), 'All aggregate flags numeric')
    # Verify .csv explicitly; keep NA as data text until controlled conversion.
    with (INPUT / 'life_expectancy.csv').open(newline='', encoding='utf-8') as f:
        life_records = list(csv.DictReader(f))
    life = pd.DataFrame(life_records)
    check('CSV exact schema', life.columns.tolist() == ['iso3', 'year', 'period_start_raw', 'life_raw'], repr(life.columns.tolist()))
    life['year'] = life.year.astype(int)
    life['life_exp'] = life.life_raw.apply(lambda v: np.nan if v == '' else float(v))
    life['period_start'] = pd.to_datetime(life.period_start_raw, format='%Y-%m-%d', errors='raise')
    check('CSV date parse', life.period_start.eq(pd.Timestamp('2023-01-01')).all(), '266 ISO dates; annual period marker, not measurement day')
    # Positional fixed-width read, not delimiter splitting.
    lines = (INPUT / 'gdp_ppp.dat').read_bytes().splitlines()
    check('DAT record widths', all(len(line) == 44 and line.isascii() for line in lines), f'{len(lines)} records, exactly 44 ASCII bytes each')
    check('DAT separator positions', all(line[3:4] == line[8:9] == line[19:20] == b' ' for line in lines), 'Blanks in columns 4, 9, 20')
    gdp_rows = []
    for line in lines:
        line = line.decode('ascii')
        token = line[20:44].strip()
        gdp_rows.append({'iso3': line[:3], 'year': int(line[4:8]), 'period_start_gdp': line[9:19],
                         'gdp_raw': token, 'gdp_ppp': np.nan if token == 'NA' else float(token)})
    gdp = pd.DataFrame(gdp_rows)
    gdp['period_start_gdp'] = pd.to_datetime(gdp.period_start_gdp, format='%Y-%m-%d', errors='raise')
    check('DAT date parse', gdp.period_start_gdp.eq(pd.Timestamp('2023-01-01')).all(), '266 valid period-start markers')
    for df, raw_name, value_column in [(life, 'life_2023.json', 'life_exp'), (gdp, 'gdp_2023.json', 'gdp_ppp')]:
        source = raw_rows(raw_name)
        expected = {(r['countryiso3code'] or by_iso2[r['country']['id']], int(r['date'])): r['value'] for r in source}
        actual_keys = set(zip(df.iso3, df.year))
        check(f'{raw_name}: input keys', len(df) == len(actual_keys) == len(expected) and actual_keys == set(expected), f'{len(df)} unique (WB code, year) keys')
        for row in df.itertuples(index=False):
            actual, original = getattr(row, value_column), expected[(row.iso3, row.year)]
            if not ((original is None and pd.isna(actual)) or (original is not None and actual == original)):
                check(f'{raw_name}: exact values', False, repr((row.iso3, actual, original)))
        check(f'{raw_name}: exact values', True, f'{len(df)} values preserved; null stays missing, no zero replacement')
    # Source-note audit: compare the full text with the normalized raw source and
    # measure what a 200-byte buffer would have lost. The input file carries no
    # reference columns; the expectation is derived here from the frozen JSON.
    notes = pd.read_csv(INPUT / 'indicator_notes.csv', keep_default_na=False)
    note_sources = {m['id']: m for name in ['life_metadata.json', 'gdp_metadata.json'] for m in raw_rows(name)}
    note_audit = []
    for row in notes.itertuples(index=False):
        raw_note = note_sources[row.indicator_id]['sourceNote']
        expected_note = ' '.join(raw_note.replace('\\n', ' ').split())
        check(f'{row.indicator_id}: full long field', row.description == expected_note, 'Full content compared to normalized raw source')
        encoded = row.description.encode('utf-8')
        note_audit.append({'indicator_id': row.indicator_id, 'actual_bytes': len(encoded),
                           'narrow_200_bytes': min(200, len(encoded)),
                           'bytes_lost_at_200': max(0, len(encoded) - 200),
                           'would_truncate_at_200': int(len(encoded) > 200), 'full_field_verified': 1})
    write('long_field_audit_reference', pd.DataFrame(note_audit))

    # Vintage dates: lastupdated must match the frozen API response header.
    vintage = pd.read_csv(INPUT / 'indicator_vintage.csv')
    check('vintage rows', len(vintage) == 2, f'{len(vintage)} indicators')
    for row in vintage.itertuples(index=False):
        stem = 'life_2023.json' if row.indicator_id.startswith('SP.') else 'gdp_2023.json'
        header = json.loads((RAW / stem).read_text(encoding='utf-8'))[0]
        check(f'{row.indicator_id}: lastupdated matches API header', row.last_updated == header['lastupdated'],
              f'{row.last_updated} vs {header["lastupdated"]}')
    write('indicator_vintage_reference', vintage)
    # Merge all sources before excluding aggregates, preserving unmatched evidence.
    merged = life.merge(gdp, how='outer', on=['iso3', 'year'], validate='one_to_one', indicator='indicator_merge')
    check('indicator merge', merged.indicator_merge.eq('both').all() and len(merged) == len(life) == len(gdp), f'{len(merged)} both; no unmatched indicator keys')
    merged = merged.merge(meta, how='outer', on='iso3', validate='one_to_one', indicator='metadata_merge')
    merged['year'] = merged.year.fillna(2023).astype(int)
    merge_counts = merged.groupby(['indicator_merge', 'metadata_merge'], observed=True, dropna=False).size().reset_index(name='rows')
    write('merge_counts_reference', merge_counts)
    write('unmatched_records_reference', merged.loc[merged.metadata_merge.ne('both') | merged.indicator_merge.ne('both'),
          ['iso3', 'country_name', 'year', 'is_aggregate', 'indicator_merge', 'metadata_merge']])
    check('metadata join row accounting', len(merged) == len(meta) and merged.metadata_merge.eq('right_only').sum() == 30 and merged.metadata_merge.eq('left_only').sum() == 0,
          f'{len(merged)} full rows; 266 both, 30 metadata only, 0 indicators only')
    check('unmatched rows are aggregates', merged.loc[merged.metadata_merge.eq('right_only'), 'is_aggregate'].eq(1).all(), 'All 30 metadata-only rows are aggregates')
    analysis = merged.loc[merged.is_aggregate.eq(0)].copy()
    for column in ['country_name', 'region_id', 'region', 'income_group']:
        analysis[column] = analysis[column].str.strip()
    analysis['complete_case'] = (analysis.life_exp.notna() & analysis.gdp_ppp.notna() & analysis.gdp_ppp.gt(0)).astype(int)
    analysis['exclusion_reason'] = np.select([analysis.life_exp.isna() & analysis.gdp_ppp.isna(), analysis.life_exp.isna(),
                                            analysis.gdp_ppp.isna(), analysis.gdp_ppp.le(0)],
                                           ['Missing both indicators', 'Missing life expectancy', 'Missing GDP', 'Nonpositive GDP'], default='Included')
    analysis['log_gdp'] = np.log(analysis.gdp_ppp.where(analysis.gdp_ppp.gt(0)))
    check('all analysis years', analysis.year.eq(2023).all(), '2023 only')
    check('plausibility: life expectancy', analysis.life_exp.dropna().between(0, 120, inclusive='right').all(), 'Observed life expectancy >0 and <=120 years')
    check('plausibility: GDP', analysis.gdp_ppp.dropna().gt(0).all(), 'All observed GDP values >0')
    measured = {'metadata_rows': len(meta), 'life_rows': len(life), 'gdp_rows': len(gdp), 'economies': len(analysis),
                'life_missing': int(analysis.life_exp.isna().sum()), 'gdp_missing': int(analysis.gdp_ppp.isna().sum()),
                'complete_cases': int(analysis.complete_case.sum()),
                'max_note_bytes': max(n['actual_bytes'] for n in note_audit),
                'vintage_rows': len(vintage)}
    check('all counts equal frozen manifest', measured == manifest['expected'], repr(measured))
    final_columns = ['iso3', 'country_name', 'region_id', 'region', 'income_group', 'year', 'period_start', 'life_exp', 'gdp_ppp', 'log_gdp', 'complete_case', 'exclusion_reason']
    analysis = analysis.sort_values('iso3')
    write('final_analysis_reference', analysis[final_columns])
    write('missingness_reference', analysis.groupby('exclusion_reason').size().reset_index(name='economies'))
    descriptions = []
    for group_name, group in [('All economies', analysis)] + list(analysis.groupby('region', sort=True)):
        for var, unit in [('life_exp', 'years'), ('gdp_ppp', 'constant 2021 international dollars')]:
            x = group[var].dropna()
            descriptions.append({'group': group_name, 'variable': var, 'unit': unit, 'total_economies': len(group), 'n': len(x),
                                 'n_missing': int(group[var].isna().sum()), 'mean': x.mean(), 'std_dev': x.std(ddof=1),
                                 'minimum': x.min(), 'q1': np.quantile(x, .25, method='averaged_inverted_cdf'),
                                 'median': np.quantile(x, .5, method='averaged_inverted_cdf'),
                                 'q3': np.quantile(x, .75, method='averaged_inverted_cdf'), 'maximum': x.max()})
    write('descriptive_reference', pd.DataFrame(descriptions))
    extremes = []
    tie_rows = []
    for direction, ascending in [('Lowest', True), ('Highest', False)]:
        ranked = analysis.loc[analysis.life_exp.notna()].sort_values(['life_exp', 'iso3'], ascending=[ascending, True])
        selected = ranked.head(4).copy()
        selected['extreme'] = direction
        selected['position'] = np.arange(1, len(selected) + 1)
        extremes.append(selected[['extreme', 'position', 'iso3', 'country_name', 'life_exp']])
        boundary = selected.life_exp.iloc[-1]
        tie_rows.append({'extreme': direction, 'fourth_value': boundary, 'all_economies_at_cutoff': int(analysis.life_exp.eq(boundary).sum()),
                         'selected_at_cutoff': int(selected.life_exp.eq(boundary).sum()), 'tie_break': 'iso3 ascending'})
    extreme_table = pd.concat(extremes, ignore_index=True)
    write('extremes_reference', extreme_table)
    write('extreme_ties_reference', pd.DataFrame(tie_rows))
    # Independently executed regression, with ordinary and HC3 uncertainty.
    sample = analysis.loc[analysis.complete_case.eq(1)].copy()
    design = sm.add_constant(sample[['log_gdp']])
    model = sm.OLS(sample.life_exp, design).fit()
    robust = model.get_robustcov_results(cov_type='HC3', use_t=True)
    coef = pd.DataFrame({'term': ['Intercept', 'log_gdp'], 'estimate': model.params.to_numpy(),
                         'ols_se': model.bse.to_numpy(), 'ols_t': model.tvalues.to_numpy(), 'ols_p': model.pvalues.to_numpy(),
                         'ols_ci_lower': model.conf_int()[0].to_numpy(), 'ols_ci_upper': model.conf_int()[1].to_numpy(),
                         'hc3_se': robust.bse, 'hc3_t': robust.tvalues, 'hc3_p_t': robust.pvalues,
                         'hc3_ci_lower_t': robust.conf_int()[:, 0], 'hc3_ci_upper_t': robust.conf_int()[:, 1]})
    write('regression_coefficients_reference', coef)
    write('model_fit_reference', pd.DataFrame([{'n': int(model.nobs), 'df_model': model.df_model, 'df_resid': model.df_resid,
         'r_squared': model.rsquared, 'adjusted_r_squared': model.rsquared_adj, 'rmse': np.sqrt(model.mse_resid),
         'ols_f': model.fvalue, 'ols_f_p': model.f_pvalue, 'intercept': model.params['const'], 'slope': model.params['log_gdp'],
         'years_per_doubling_gdp': model.params['log_gdp'] * np.log(2), 'inference': 'Unweighted cross-sectional association; no causal interpretation'}]))
    influence = model.get_influence()
    sample['predicted'] = model.fittedvalues
    sample['residual'] = model.resid
    sample['rstudent'] = influence.resid_studentized_external
    sample['leverage'] = influence.hat_matrix_diag
    sample['cooks_d'] = influence.cooks_distance[0]
    sample['flag_cook'] = (sample.cooks_d.gt(4 / len(sample))).astype(int)
    sample['flag_leverage'] = (sample.leverage.gt(4 / len(sample))).astype(int)
    sample['flag_rstudent'] = (sample.rstudent.abs().gt(2)).astype(int)
    write('model_diagnostics_reference', sample[['iso3', 'country_name', 'life_exp', 'gdp_ppp', 'log_gdp', 'predicted', 'residual', 'rstudent', 'leverage', 'cooks_d', 'flag_cook', 'flag_leverage', 'flag_rstudent']])
    # These Python tests are supplementary; White LM is NOT SAS SPEC.
    white = het_white(model.resid, design)
    bp = het_breuschpagan(model.resid, design)
    shapiro = stats.shapiro(model.resid)
    write('diagnostic_tests_reference', pd.DataFrame([
        {'test': 'White LM heteroskedasticity (Python; not SAS SPEC)', 'statistic': white[0], 'p_value': white[1]},
        {'test': 'Koenker-Breusch-Pagan LM (Python)', 'statistic': bp[0], 'p_value': bp[1]},
        {'test': 'Shapiro-Wilk residual normality (Python)', 'statistic': shapiro.statistic, 'p_value': shapiro.pvalue}]))
    # PNGs explicitly identify the engine in their footnote.
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 13, 'figure.dpi': 150})
    fig, ax = plt.subplots(figsize=(9.8, 6))
    for region, group in sample.groupby('region'):
        ax.scatter(group.log_gdp, group.life_exp, s=23, alpha=.78, label=region)
    x = np.linspace(sample.log_gdp.min(), sample.log_gdp.max(), 100)
    ax.plot(x, model.params['const'] + model.params['log_gdp'] * x, color='#222222', lw=1.6, label='OLS fit')
    ax.set(title=f'GDP per capita and life expectancy, 2023 (n={len(sample)})',
           xlabel='Natural log of GDP per capita (constant 2021 international $)', ylabel='Life expectancy at birth (years)')
    ax.legend(fontsize=7, loc='lower right', framealpha=.9)
    ax.grid(alpha=.15)
    fig.text(.5, .015, 'World Bank WDI snapshot | Python reference output; SAS execution pending', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, 1)); fig.savefig(OUT / 'scatter_reference.png'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 6.5))
    region_groups = sorted(analysis.groupby('region'), key=lambda item: item[1].life_exp.median())
    ax.boxplot([group.life_exp.dropna() for _, group in region_groups], vert=False,
               labels=[f'{region} (n={group.life_exp.notna().sum()})' for region, group in region_groups], patch_artist=True,
               boxprops={'facecolor': '#AFCADB'}, medianprops={'color': '#8B2B35'})
    ax.set(title='Life expectancy by current World Bank region, 2023', xlabel='Life expectancy at birth (years)', ylabel='Region (metadata at download)')
    ax.grid(axis='x', alpha=.15)
    fig.text(.5, .015, 'All available life expectancy values | Python reference output; SAS execution pending', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, 1)); fig.savefig(OUT / 'boxplot_reference.png'); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    axes[0].scatter(sample.predicted, sample.residual, s=18, alpha=.7)
    axes[0].axhline(0, color='black', lw=1)
    axes[0].set(title='Residuals versus fitted values', xlabel='Fitted life expectancy (years)', ylabel='Residual (years)')
    sm.qqplot(model.resid, line='s', ax=axes[1], markersize=3)
    axes[1].set(title='Normal Q-Q plot of residuals', xlabel='Theoretical normal quantile', ylabel='Observed residual (years)')
    fig.text(.5, .015, 'OLS on 197 complete economies | Python reference output; SAS execution pending', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, 1)); fig.savefig(OUT / 'residual_diagnostics_reference.png'); plt.close(fig)
    readback = pd.read_csv(OUT / 'final_analysis_reference.csv', float_precision='round_trip')
    check('reference CSV reread', len(readback) == 217, '217 exported rows')
    numeric_columns = ['year', 'life_exp', 'gdp_ppp', 'log_gdp', 'complete_case']
    check('reference numeric round trip',
          np.array_equal(readback[numeric_columns].to_numpy(dtype=float),
                         analysis[numeric_columns].to_numpy(dtype=float), equal_nan=True),
          'All exported numeric fields recover identical binary64 values; missing values preserved')
    check('model reference sample', len(sample) == 197 and np.isfinite(model.params).all(), '197 complete cases and finite coefficients')
    pd.DataFrame(checks).to_csv(VALIDATION / 'input_checks.csv', index=False)
    result = {'engine': 'Python independent reference; SAS NOT executed', 'timestamp_hong_kong': datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(timespec='seconds'),
              'python': sys.version, 'platform': platform.platform(), 'versions': {m.__name__: m.__version__ for m in [np, pd, scipy, statsmodels, matplotlib, openpyxl]},
              'checks_passed': len(checks), 'checks_failed': 0, 'measured_counts': measured,
              'regression': {'n': len(sample), 'intercept': model.params['const'], 'slope': model.params['log_gdp'],
                             'r_squared': model.rsquared, 'rmse': float(np.sqrt(model.mse_resid)), 'hc3_slope_se': float(robust.bse[1])}}
    (VALIDATION / 'validation_summary.json').write_text(json.dumps(result, indent=2) + '\n')
    notes_vintage = ', '.join(f"{r.indicator_id} = {r.last_updated}" for r in vintage.itertuples(index=False))
    summary_text = f'''# Validation record

Generated by `tools/validate_inputs.py`. **The verification engine here is Python**: it recomputes
the inputs and the reference statistics independently, without reading any SAS output and without
reusing SAS logic.

SAS has also been executed separately (16 November 2026, SAS 9.04.01M8P02222023):
`results/sas/RUN_STATUS.txt` starts with `COMPLETED`, `run_all.log` contains 0 ERROR and
0 WARNING, and all 29 assertions report `passed=1`. This document covers the input side only; the
two are independent evidence and they agree on every number.

- Validation run (Hong Kong time): {result['timestamp_hong_kong']}
- Raw data downloaded: {manifest['downloaded_at_hong_kong']}
- {len(checks)} checks passed, 0 failed. Item-by-item record in `validation/input_checks.csv`.
- The SHA-256 of all five raw JSON files matches the frozen manifest, and every page is complete.
- Excel catalogue: 296 rows and 6 fields, compared cell by cell with the raw metadata.
- Life-expectancy CSV: 266 rows. GDP DAT: 266 rows, each exactly 44 ASCII bytes.
- Both indicator tables are unique on (iso3, year); every value was compared with the raw JSON and
  no value was truncated, rounded away or imputed.
- Both inputs parse every date as 2023-01-01. That is an annual period marker, not a collection
  date, and it is labelled as such everywhere.
- The longest free-text field is 1,342 bytes and matches the raw `sourceNote` character for
  character. The input file carries no "expected length" column of its own: the 200-byte buffer
  loss is measured in SAS at run time, not asserted from a pre-baked answer.
- Indicator vintage dates: `last_updated` = {notes_vintage}, taken from the API response header
  `lastupdated` and identical to the frozen JSON.
- The indicator join returns 266 rows with 0 unmatched. The full join to the catalogue returns 296
  rows, of which 30 exist only in the catalogue and are all aggregates. 79 aggregates are excluded.
- After excluding aggregates: 217 economies, 0 missing life expectancy, 20 missing GDP, 197
  complete cases. Missing GDP stays missing and is never replaced by zero.
- The final reference CSV was read back and confirmed at 217 rows, including the regression
  inclusion flag and the exclusion reason. It is exported with 17 significant digits; every numeric
  field recovers the identical binary64 value and missing values stay missing.

## Reference results computed here

Equal-weight cross-sectional OLS: `life_exp = intercept + slope x ln(gdp_ppp)`. N = {len(sample)},
intercept {model.params['const']:.6f}, slope {model.params['log_gdp']:.6f},
R-squared = {model.rsquared:.6f}, RMSE = {np.sqrt(model.mse_resid):.6f} years,
HC3 standard error of the slope {robust.bse[1]:.6f}. These are associations and must not be read as
the effect of income growth on longevity.

Reference files live in `validation/python_reference/` and every name contains `reference`: the
final reference table, descriptive statistics by region, the four lowest and four highest records,
the boundary-tie audit, regression coefficients and confidence intervals, per-economy diagnostics,
and the scatter, box and residual/QQ charts. The official SAS output directory is `results/sas/`;
the two are kept separate on purpose so that a Python result can never be mistaken for a SAS one.

The model flags Cook's D > 4/n, leverage > 4/n and |externally studentized residual| > 2 for
inspection only; flags never delete a row. Python additionally reports White LM,
Koenker-Breusch-Pagan LM and Shapiro-Wilk tests. White LM is **not** the SAS `SPEC` joint
specification test, so the two p-values must not be expected to match. HC3 reference intervals use
a t distribution on the residual degrees of freedom. When comparing with SAS, separate the
conventional and HC3 intervals by their actual column labels (`ols_ci_*` versus `hc3_ci_*`) and
confirm the distribution convention rather than mixing the two standard errors. Descriptive
statistics use the sample standard deviation and NumPy `averaged_inverted_cdf` quantiles, which
correspond to SAS `QNTLDEF=5`.

## Verifying the SAS side (executed once)

1. Upload the project as described in the README and run `run_all.sas`; the log, CSVs and PNGs in
   `results/sas/` are the SAS evidence that corresponds to this document.
2. After downloading the output, run `python3 tools/check_sas_run.py results/sas`. It checks the
   completion marker, the assertions, the row counts and whether every raw value still equals the
   frozen JSON.
3. Confirm the coefficients, R-squared, RMSE and sample size against this reference. The actual run
   gives intercept 22.56709, slope 5.26717, R-squared 0.7419, RMSE 3.61339 and N = 197, identical to
   the numbers above.
4. The SPEC and TEST results exist only in `analysis.html`, because those ODS table names vary
   between SAS releases. See `docs/FIGURE_MAP.md` and the README.

To rerun the local validation, install the Python packages above and execute
`python3 tools/validate_inputs.py`. This run used Python {platform.python_version()}; dependency
versions are recorded in `validation/validation_summary.json`.
'''
    (ROOT / 'docs/VALIDATION.md').write_text(summary_text, encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
