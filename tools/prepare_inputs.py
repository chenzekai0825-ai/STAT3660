#!/usr/bin/env python3
"""Rebuild CSV/DAT from the frozen official JSON. --download explicitly refreshes it.
XLSX is independently built by build_metadata.mjs; normal SAS runs need neither tool.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo

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
    notes = []
    for name in ['life_metadata.json', 'gdp_metadata.json']:
        m = read(name)[0]
        # Normalize literal backslash-n and actual whitespace for one CSV line.
        desc = ' '.join(m['sourceNote'].replace('\\n', ' ').split())
        assert 0 < len(desc.encode('utf-8')) < 4096
        notes.append([m['id'], desc, len(desc.encode('utf-8')), desc[-40:]])
    write_csv('indicator_notes.csv', ['indicator_id', 'description', 'expected_bytes', 'expected_suffix'], notes)
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
        'max_note_bytes': max(r[2] for r in notes),
    }
    manifest_path = RAW / 'manifest.json'
    # Files are saved immediately after each HTTP response. The latest raw-file
    # timestamp records completion of the five downloads, not conversion time.
    stamp = datetime.fromtimestamp(max((RAW / n).stat().st_mtime for n in URLS),
                                   ZoneInfo('Asia/Hong_Kong')).isoformat(timespec='seconds')
    if manifest_path.exists() and not args.download:
        stamp = json.loads(manifest_path.read_text())['downloaded_at_hong_kong']
    manifest = {'downloaded_at_hong_kong': stamp, 'study_year': 2023, 'sources': [], 'expected': expected}
    for name, url in URLS.items():
        data = (RAW / name).read_bytes()
        manifest['sources'].append({'file': name, 'url': url, 'bytes': len(data),
                                    'sha256': hashlib.sha256(data).hexdigest(),
                                    'api_header': json.loads(data)[0]})
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    (RAW / 'source_urls.json').write_text(json.dumps(URLS, indent=2) + '\n')
    (ROOT / 'sas/snapshot_expectations.sas').write_text(
        '/* Generated from frozen raw JSON by tools/prepare_inputs.py. */\n' +
        ''.join(f'%let expected_{k}={v};\n' for k, v in expected.items()))
    print(json.dumps(expected, indent=2))


if __name__ == '__main__':
    main()
