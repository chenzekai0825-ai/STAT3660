#!/usr/bin/env python3
"""Rebuild every SAS input file from the frozen official JSON.

    python3 tools/prepare_inputs.py              # offline, verifies SHA-256 first
    python3 tools/prepare_inputs.py --download   # refreshes the raw JSON snapshot

Outputs (all inside data/input/):
    economies.xlsx        metadata catalogue, built with openpyxl
    life_expectancy.csv   life expectancy, delimited text
    gdp_ppp.dat           GDP per capita, 44-byte fixed width ASCII
    indicator_notes.csv   the real indicator definitions (long free text)
    indicator_vintage.csv the real API vintage dates (lastupdated / retrieval)

The Excel workbook is built here with openpyxl, so the whole pipeline can be
reproduced with public tools only.  Nothing in this repository depends on a
private or vendor-specific service.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
RAW, INPUT = ROOT / 'data/raw', ROOT / 'data/input'
URLS = {
    'countries.json': 'https://api.worldbank.org/v2/country?format=json&per_page=400',
    'life_2023.json': 'https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?date=2023&format=json&per_page=400&source=2',
    'gdp_2023.json': 'https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?date=2023&format=json&per_page=400&source=2',
    'life_metadata.json': 'https://api.worldbank.org/v2/indicator/SP.DYN.LE00.IN?format=json&source=2',
    'gdp_metadata.json': 'https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.PP.KD?format=json&source=2',
}


def read(name):
    payload = json.loads((RAW / name).read_text())
    assert len(payload) == 2 and int(payload[0]['pages']) == 1
    assert len(payload[1]) == int(payload[0]['total'])
    return payload[1]


def write_csv(name, columns, rows):
    with (INPUT / name).open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(columns)
        w.writerows(rows)


def build_excel(countries):
    """Countries JSON -> one workbook, one sheet, six columns, nothing derived."""
    columns = ['iso3', 'country_name', 'region_id', 'region', 'income_group', 'is_aggregate']
    wb = Workbook()
    ws = wb.active
    ws.title = 'Economies'
    ws.append(columns)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    for r in sorted(countries, key=lambda x: x['id']):
        ws.append([
            r['id'],
            r['name'],
            r['region']['id'],
            r['region']['value'],
            r['incomeLevel']['value'],
            1 if r['region']['id'] == 'NA' else 0,
        ])
    for i, width in enumerate([6, 56, 10, 34, 22, 12], start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = 'A2'
    wb.save(INPUT / 'economies.xlsx')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if not args.download and (RAW / 'manifest.json').exists():
        frozen = json.loads((RAW / 'manifest.json').read_text())
        for source in frozen['sources']:
            digest = hashlib.sha256((RAW / source['file']).read_bytes()).hexdigest()
            if digest != source['sha256']:
                raise ValueError(f"Frozen raw source changed: {source['file']}; restore it before offline conversion")
    if args.download:
        for name, url in URLS.items():
            content = urlopen(url, timeout=60).read()
            json.loads(content)
            (RAW / name).write_bytes(content)
    countries = read('countries.json')
    by_iso2 = {r['iso2Code']: r['id'] for r in countries}
    assert len(by_iso2) == len(countries)
    mapping_audit = []

    def indicators(name):
        result = []
        for r in read(name):
            # WB leaves countryiso3code blank for some aggregates. Resolve using
            # the API's own iso2 -> id mapping, never by names or invented IDs.
            key = r['countryiso3code'] or by_iso2[r['country']['id']]
            if not r['countryiso3code']:
                mapping_audit.append([name, r['country']['id'], key, r['country']['value']])
            assert len(key) == 3 and key.isascii() and r['date'] == '2023'
            result.append((key, 2023, r['value']))
        assert len({(r[0], r[1]) for r in result}) == len(result)
        return sorted(result)

    life, gdp = indicators('life_2023.json'), indicators('gdp_2023.json')
    write_csv('life_expectancy.csv', ['iso3', 'year', 'period_start_raw', 'life_raw'],
              [[k, y, f'{y}-01-01', '' if v is None else repr(v)] for k, y, v in life])
    with (INPUT / 'gdp_ppp.dat').open('w', encoding='ascii', newline='') as f:
        for k, y, v in gdp:
            token = 'NA' if v is None else format(v, '.17g')
            assert len(token) <= 24
            line = f'{k} {y:04d} {y}-01-01 {token:>24s}'
            assert len(line) == 44
            f.write(line + '\n')

    # Real indicator definitions. Only the two columns that the source actually
    # provides are kept; the SAS program derives its own length audit from the text.
    notes = []
    for name in ['life_metadata.json', 'gdp_metadata.json']:
        m = read(name)[0]
        desc = ' '.join(m['sourceNote'].replace('\\n', ' ').split())
        assert 0 < len(desc.encode('utf-8')) < 4096
        notes.append([m['id'], desc])
    write_csv('indicator_notes.csv', ['indicator_id', 'description'], notes)

    # Real vintage dates from the API response header and the download manifest.
    manifest_path = RAW / 'manifest.json'
    # Files are saved immediately after each HTTP response. The latest raw-file
    # timestamp records completion of the five downloads, not conversion time.
    stamp = datetime.fromtimestamp(max((RAW / n).stat().st_mtime for n in URLS),
                                   ZoneInfo('Asia/Hong_Kong')).isoformat(timespec='seconds')
    if manifest_path.exists() and not args.download:
        stamp = json.loads(manifest_path.read_text())['downloaded_at_hong_kong']
    retrieved_date = stamp[:10]
    vintage = []
    # lastupdated comes from the DATA endpoint header; the indicator name from
    # the indicator metadata endpoint.  Both are real values returned by the API.
    for meta_name, data_name in [('life_metadata.json', 'life_2023.json'),
                                 ('gdp_metadata.json', 'gdp_2023.json')]:
        meta = json.loads((RAW / meta_name).read_text())[1][0]
        header = json.loads((RAW / data_name).read_text())[0]
        vintage.append([meta['id'], meta['name'], header['lastupdated'], retrieved_date])
    write_csv('indicator_vintage.csv',
              ['indicator_id', 'indicator_name', 'last_updated', 'retrieved_date'], vintage)
    write_csv('key_mapping_audit.csv', ['source_file', 'api_iso2', 'resolved_wb_code', 'source_name'], mapping_audit)

    # The manifest freezes exact download bytes and reference counts, not estimates.
    lm, gm = {k: v for k, _, v in life}, {k: v for k, _, v in gdp}
    eligible = [r for r in countries if r['region']['id'] != 'NA']
    expected = {
        'metadata_rows': len(countries), 'life_rows': len(life), 'gdp_rows': len(gdp),
        'economies': len(eligible),
        'life_missing': sum(lm.get(r['id']) is None for r in eligible),
        'gdp_missing': sum(gm.get(r['id']) is None for r in eligible),
        'complete_cases': sum(lm.get(r['id']) is not None and gm.get(r['id']) is not None and gm[r['id']] > 0 for r in eligible),
        'max_note_bytes': max(len(r[1].encode('utf-8')) for r in notes),
        'vintage_rows': len(vintage),
    }
    manifest = {'downloaded_at_hong_kong': stamp, 'study_year': 2023, 'sources': [], 'expected': expected}
    for name, url in URLS.items():
        data = (RAW / name).read_bytes()
        manifest['sources'].append({'file': name, 'url': url, 'bytes': len(data),
                                    'sha256': hashlib.sha256(data).hexdigest(),
                                    'api_header': json.loads(data)[0]})
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    (RAW / 'source_urls.json').write_text(json.dumps(URLS, indent=2) + '\n')

    build_excel(countries)

    (ROOT / 'sas/snapshot_expectations.sas').write_text(
        '/* Generated from frozen raw JSON by tools/prepare_inputs.py. */\n' +
        ''.join(f'%let expected_{k}={v};\n' for k, v in expected.items()))
    print(json.dumps(expected, indent=2))


if __name__ == '__main__':
    main()
