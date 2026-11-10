#!/usr/bin/env python3
"""Check downloaded SAS output after running run_all.sas; never emulates SAS.
Usage: python3 tools/check_sas_run.py [path/to/results/sas]
Exit 0=checks passed; 1=missing/failed checks or log messages need review.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'results/sas'


def main():
    failures = []
    warnings = []
    required = ['RUN_STATUS.txt', 'run_all.log', 'analysis.html', 'assertions.csv',
                'final_analysis.csv', 'row_counts.csv', 'input_types.csv',
                'date_audit.csv', 'long_field_audit.csv', 'merge_audit.csv',
                'unmatched_rows.csv', 'analysis_sample_flow.csv',
                'descriptive_statistics.csv', 'life_expectancy_extremes.csv',
                'extreme_cutoff_audit.csv', 'regression_sample_size.csv',
                'regression_fit.csv', 'regression_parameters.csv',
                'regression_specification_test.csv', 'regression_slope_test_hc3.csv',
                'regression_diagnostics.csv']
    for name in required:
        if not (OUT / name).is_file() or (OUT / name).stat().st_size == 0:
            failures.append(f'Missing/empty SAS output: {name}')
    for prefix in ['01_income_life_scatter','02_life_expectancy_by_region',
                   '03_residuals_vs_fitted','04_residual_normal_qq',
                   '05_cooks_distance','06_leverage_studentized_residual']:
        if not list(OUT.glob(prefix + '*.png')):
            failures.append(f'Missing PNG: {prefix}')
    log = (OUT / 'run_all.log').read_text(errors='replace') if (OUT/'run_all.log').exists() else ''
    # Match real log messages, not MPRINT echoes of the error-handling source.
    danger = re.compile(r'^\s*(?:ERROR(?:\s+\d+-\d+)?:|WARNING:|NOTE:.*(?:uninitialized|Invalid data|converted to|repeats of BY values|Missing values were generated|Division by zero))',re.I)
    warnings = [line for line in log.splitlines() if danger.search(line)]
    if 'NOTE: PROJECT_COMPLETED.' not in log:
        failures.append('No PROJECT_COMPLETED marker in actual SAS log')
    if (OUT/'RUN_STATUS.txt').exists() and not (OUT/'RUN_STATUS.txt').read_text().startswith('COMPLETED:'):
        failures.append('RUN_STATUS does not show completion')
    def rows(name):
        with (OUT/name).open(encoding='utf-8-sig',newline='') as f:
            return [{k.lower():v for k,v in r.items()} for r in csv.DictReader(f)]
    try:
        e=json.loads((ROOT/'data/raw/manifest.json').read_text())['expected']
        if (OUT/'assertions.csv').exists():
            a=rows('assertions.csv')
            if not a or any(float(r['passed'])!=1 for r in a): failures.append('At least one SAS assertion failed')
        if (OUT/'final_analysis.csv').exists():
            r=rows('final_analysis.csv')
            if len(r)!=e['economies']: failures.append('Final economy count mismatch')
            if len({(v['iso3'],v['year']) for v in r})!=len(r): failures.append('Duplicate final keys')
            if sum(float(v['complete_case'])==1 for v in r)!=e['complete_cases']: failures.append('Regression sample mismatch')
            countries=json.loads((ROOT/'data/raw/countries.json').read_text())[1]
            eligible={c['id'] for c in countries if c['region']['id']!='NA'}
            iso2={c['iso2Code']:c['id'] for c in countries}
            if {v['iso3'] for v in r}!=eligible: failures.append('Final economy keys differ from raw snapshot')
            for filename,column in [('life_2023.json','life_exp'),('gdp_2023.json','gdp_ppp')]:
                original=json.loads((ROOT/'data/raw'/filename).read_text())[1]
                source={v['countryiso3code'] or iso2[v['country']['id']]:v['value'] for v in original}
                for v in r:
                    expected=source.get(v['iso3'])
                    token=v[column].strip()
                    observed=None if token in ('','.') else float(token)
                    if expected is None:
                        if observed is not None: failures.append(f"Missing value changed: {v['iso3']} {column}")
                    elif observed is None or not math.isclose(observed,expected,rel_tol=1e-12,abs_tol=1e-12):
                        failures.append(f"Raw numeric value changed: {v['iso3']} {column}")
            if any(v['period_start']!='2023-01-01' for v in r): failures.append('Final annual date format/value mismatch')
        if (OUT/'life_expectancy_extremes.csv').exists():
            r=rows('life_expectancy_extremes.csv')
            if len(r)!=8: failures.append('Expected exactly eight extreme records')
    except (ValueError,KeyError,OSError) as exc:
        failures.append(f'Cannot validate output structure: {exc}')
    result={'sas_outputs_directory':str(OUT),'passed':not failures and not warnings,
            'failures':failures,'log_messages_requiring_review':warnings}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    sys.exit(main())
