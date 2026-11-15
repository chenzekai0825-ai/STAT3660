#!/usr/bin/env python3
"""Extract the figures that SAS embedded in analysis.html into separate PNG files.

    python3 tools/extract_pngs.py [path/to/results/sas]

SAS Studio embeds every ODS graphic into the HTML result as a base64 PNG. That
makes analysis.html self-contained, but the report and the slides need separate
image files. This script pulls them back out, in document order, and prints the
accessibility text of each figure so you know which one is which.

Use it either as the normal way to collect figures, or as a fallback when
ODS LISTING GPATH did not write the .png files next to the log.
"""
import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'results' / 'sas'
HTML = OUT / 'analysis.html'
FIGURE_DIR = OUT / 'figures'

IMG = re.compile(r'<img[^>]*alt="([^"]*)"[^>]*src="data:image/png;base64,([A-Za-z0-9+/=]+)"', re.I)
IMG_2 = re.compile(r'<img[^>]*src="data:image/png;base64,([A-Za-z0-9+/=]+)"[^>]*alt="([^"]*)"', re.I)


def main():
    if not HTML.is_file():
        print(f'ERROR: {HTML} not found. Run run_all.sas first, then pass the results folder.')
        return 1
    text = HTML.read_text(encoding='utf-8', errors='replace')
    found = [(alt, b64) for alt, b64 in IMG.findall(text)]
    if not found:
        found = [(alt, b64) for b64, alt in IMG_2.findall(text)]
    if not found:
        print('ERROR: no embedded PNG found in analysis.html.')
        print('Check that ODS Graphics was on and that the run produced graphs.')
        return 1
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    print(f'{len(found)} embedded figure(s) found in {HTML.name}')
    for index, (alt, b64) in enumerate(found, start=1):
        name = f'figure_{index:02d}.png'
        data = base64.b64decode(b64)
        (FIGURE_DIR / name).write_bytes(data)
        print(f'  {name}  {len(data):>7,} bytes  alt="{alt[:90]}"')
    print(f'\nWritten to {FIGURE_DIR}')
    print('Rename them to match the plot numbers in the report before inserting them.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
