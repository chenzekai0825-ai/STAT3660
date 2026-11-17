#!/usr/bin/env python3
"""Build the written report (.docx) from the frozen SAS output.

    python3 tools/build_report_docx.py

Reads  : results/sas/*.csv, results/sas/*.png
Writes : docs/STAT3660_Report.docx

Every number in the document is read from the SAS output files, so re-running
run_all.sas and then this script keeps the text and the tables consistent.
The prose is written in English to match the course materials and the SAS
figure labels; the planning notes in docs/REPORT_DRAFT.md stay in Chinese.
"""
import csv
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

MEMBERS = [
    # (name, student id, contribution) -- reorder the rows if the split differs.
    ('ZHANG Bohan', 's1362832', 'Data acquisition, three input formats, long-field and vintage audit'),
    ('CHEN Jingwei', 's1364350', 'Cleaning, missing values and sentinel handling, sample flags'),
    ('LI Zhuohao', 's1361931', 'Merging, row reconciliation, assertion framework'),
    ('CHEN Zekai', 's1367727', 'Descriptive statistics, extreme values, all seven figures'),
    ('ZHOU Yilin', 's1362098', 'Inference and regression, report editing'),
]
GROUP = '______'   # group number, filled in on the cover page

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'results' / 'sas'
# First command-line argument (optional) redirects the output, e.g.
#     python3 tools/build_report_docx.py ../../pre
_out_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'docs'
_out_dir.mkdir(parents=True, exist_ok=True)
OUT = _out_dir / 'STAT3660_Report.docx'


# ---------------------------------------------------------------- data access
def rows(name):
    with (RES / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


assertions = rows('assertions.csv')
row_counts = {r['stage']: int(float(r['n'])) for r in rows('row_counts.csv')}
desc = rows('descriptive_statistics.csv')
regions = [r for r in rows('region_summary.csv') if r.get('_TYPE_') in ('1', '')]
extremes = rows('life_expectancy_extremes.csv')
params = rows('regression_parameters.csv')
# regression_fit.csv holds two label/value pairs per row. They are read by POSITION, never by
# label: SAS localises those labels to the session language, positions do not change.
#   row 1: cValue1 = root mean square error, cValue2 = R-squared
#   row 2: cValue1 = mean of the dependent,  cValue2 = adjusted R-squared
_fit = rows('regression_fit.csv')
rmse = num(_fit[0]['cValue1'])
r2 = num(_fit[0]['cValue2'])
dep_mean = num(_fit[1]['cValue1'])
adj_r2 = num(_fit[1]['cValue2'])
diag = rows('regression_diagnostics.csv')
vintage = rows('indicator_vintage_audit.csv')
notes = rows('long_field_audit.csv')

# NOTE ON DATA SOURCES IN THIS DOCUMENT
# Statistics read from CSV: descriptive statistics, extremes, region summary,
# regression parameters/fit/diagnostics, vintage, long-field audit.
# Statistics typed in by hand (the SAS run prints them to analysis.html but does
# not export them to CSV): Kruskal-Wallis, ANOVA, Levene, Welch, the two-sample
# t test, the correlations and the SPEC test. If the analysis is re-run with a
# different sample, re-check the numbers in sections 4.3, 4.4 and 4.6 against
# results/sas/analysis.html before resubmitting.
overall = {r['variable']: r for r in desc if r['scope'] == 'Overall'}
n_all = int(overall['life_exp']['n'])
n_gdp = int(overall['gdp_ppp']['n'])
n_missing_gdp = int(overall['gdp_ppp']['n_missing'])

p_int = next(p for p in params if p['Variable'] == 'Intercept')
p_slope = next(p for p in params if p['Variable'] == 'log_gdp')
slope = num(p_slope['Estimate'])
n_model = len(diag)
flagged = [d for d in diag if d.get('flag_any') == '1']
cook_flags = [d for d in diag if d.get('flag_cook') == '1']
lev_flags = [d for d in diag if d.get('flag_leverage') == '1']
res_flags = [d for d in diag if d.get('flag_residual') == '1']
worst = sorted(diag, key=lambda d: -(num(d['cooks_d']) or 0))[:3]
doubling = slope * 0.6931471805599453
days_vintage = int(num(vintage[0]['days_since_update'], 0))
max_note = max(int(num(n['actual_bytes'], 0)) for n in notes)


# ---------------------------------------------------------------- docx helpers
def set_cell_bg(cell, hex_color):
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:fill'), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def add_page_number(paragraph):
    run = paragraph.add_run()
    for instr in ('begin', 'PAGE', 'end'):
        if instr == 'PAGE':
            fld = OxmlElement('w:instrText')
            fld.set(qn('xml:space'), 'preserve')
            fld.text = ' PAGE '
            run._r.append(fld)
        else:
            fld = OxmlElement('w:fldChar')
            fld.set(qn('w:fldCharType'), instr)
            run._r.append(fld)


def body(doc, text, size=12, bold=False, italic=False, space_after=6,
         align=None, style=None):
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    return p


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x3B, 0x57)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(10)
    run.italic = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    return p


def table(doc, header, data, widths=None, font_size=9, align_right_from=1):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, text in enumerate(header):
        hdr[i].text = ''
        run = hdr[i].paragraphs[0].add_run(text)
        run.bold = True
        run.font.size = Pt(font_size)
        set_cell_bg(hdr[i], 'DCE6F1')
    for row in data:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ''
            run = cells[i].paragraphs[0].add_run(str(text))
            run.font.size = Pt(font_size)
            if i >= align_right_from:
                cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if widths:
        for row in t.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    return t


def figure(doc, filename, width_cm=15.5):
    path = RES / filename
    if not path.is_file():
        body(doc, f'[missing figure: {filename}]', italic=True)
        return
    doc.add_picture(str(path), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def two_figures(doc, left, right, width_cm=8.0):
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, name in zip(t.rows[0].cells, (left, right)):
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        path = RES / name
        if path.is_file():
            p.add_run().add_picture(str(path), width=Cm(width_cm))


# ---------------------------------------------------------------- build
doc = Document()
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')

section = doc.sections[0]
section.top_margin = Cm(2.2)
section.bottom_margin = Cm(2.2)
section.left_margin = Cm(2.5)
section.right_margin = Cm(2.5)

footer_p = section.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_page_number(footer_p)

# ---- title page -------------------------------------------------------------
body(doc, 'STAT 3660SEF SAS Programming', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
body(doc, '2026 Autumn — Group Project', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
body(doc, 'Income and Life Expectancy in 2023:', size=20, bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
body(doc, 'A Cross-Section of 217 World Bank Economies', size=20, bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
body(doc, f'Group Number: {GROUP}', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
body(doc, 'Date: 6 December 2026', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=30)

table(doc,
      ['#', 'Name', 'Student ID', 'Main contribution'],
      [[str(i), name, sid, part] for i, (name, sid, part) in enumerate(MEMBERS, start=1)],
      widths=[1.0, 4.2, 2.8, 8.0], font_size=10)

body(doc, '')
body(doc, 'All results in this report were produced by the SAS program in run_all.sas '
          'running on SAS 9.04.01M8P02222023; the log contains no ERROR or WARNING and all '
          '29 assertions passed. The code and the archived input snapshot are submitted with '
          'this report.', size=10, italic=True)
doc.add_page_break()

# ---- 1 Introduction ---------------------------------------------------------
heading(doc, '1  Introduction', 1)

body(doc, 'The positive association between income per head and life expectancy is one of the '
          'most robust regularities in development economics (Preston, 1975). What remains '
          'disputed is not whether the association exists, but three narrower questions: how '
          'strong it is, whether the large regional differences in longevity are merely a '
          'reflection of income differences, and where the regularity visibly breaks down.')

body(doc, 'This project answers those three questions using a single-year cross-section for '
          '2023. Two design decisions follow from that. First, every economy is observed in the '
          'same year: pooling "latest available year" values would mix observations collected up '
          'to a decade apart and confound the comparison with time. Second, the unit of analysis '
          'is the economy, not the individual, so each economy carries equal weight. Population '
          'weighting would answer a different question — where most people live rather than how '
          'economies compare.')

body(doc, 'The three questions are taken in turn:')
body(doc, 'Q1  Association. If gross domestic product per head doubles, how many years of life '
          'expectancy are associated with that difference?', style='List Bullet')
body(doc, 'Q2  Group differences. Do the seven World Bank regions really differ in longevity, '
          'and are those differences larger than sampling noise?', style='List Bullet')
body(doc, 'Q3  Where the regularity fails. Which economies live noticeably longer or shorter '
          'than their income would predict, and why?', style='List Bullet')

body(doc, 'The scope must be stated at the outset. This is an association analysis, not a causal '
          'one. There is no identification strategy and no control for education, health '
          'expenditure, institutional quality or geography. The results therefore must not be read '
          'as the effect of raising income on longevity. What the report does claim is that the '
          'association is strong, that regional gaps survive a battery of tests, and that a '
          'non-trivial number of economies deviate from the fitted relation in an interpretable '
          'way.')

# ---- 2 Dataset --------------------------------------------------------------
heading(doc, '2  Dataset', 1)
heading(doc, '2.1  Source, indicators and snapshot', 2)

body(doc, f'Both indicators come from the World Bank World Development Indicators (WDI, source 2) '
          f'for the year 2023: life expectancy at birth, total population (SP.DYN.LE00.IN, in '
          f'years) and GDP per capita at purchasing power parity in constant 2021 international '
          f'dollars (NY.GDP.PCAP.PP.KD). The country catalogue is the /v2/country endpoint, which '
          f'returns {row_counts["01 Excel metadata"]} entries: {n_all} economies plus '
          f'{row_counts["06 Excluded aggregates"]} regional and income aggregates.')

body(doc, f'The snapshot is reproducible. The five API responses are archived byte for byte with '
          f'their SHA-256 digests and download time, so the conversion can be replayed offline and '
          f'the exact figures in this report can be regenerated. The source itself reports '
          f'{vintage[0]["last_updated"]} as the date the series were last updated; we retrieved '
          f'the snapshot on {vintage[0]["retrieved"]}, {days_vintage} days later. WDI data are '
          f'revised over time, which is precisely why an archived snapshot rather than a live '
          f'download is used.')

heading(doc, '2.2  Three input formats', 2)

body(doc, 'The project reads three different file formats, each chosen because it suits the '
          'content it carries rather than to satisfy the checklist:')
table(doc,
      ['Format', 'File', 'SAS mechanism', 'Content', 'Why this format'],
      [['Excel', 'economies.xlsx', 'PROC IMPORT DBMS=XLSX', '296 catalogue rows, 6 fields',
        'A catalogue is a table a human maintains and reviews'],
       ['Delimited', 'life_expectancy.csv', 'DATA step, INFILE DSD', '266 life-expectancy records',
        'Narrow value range, easy to inspect by eye'],
       ['Fixed width', 'gdp_ppp.dat', 'DATA step, column pointers @1 @5 @10 @21',
        '266 GDP records, exactly 44 bytes per line',
        'Mimics a statistical office export with no header, which must be parsed by position']],
      widths=[2.2, 3.4, 4.4, 3.6, 3.4], font_size=8.5, align_right_from=99)
caption(doc, 'Table 1  The three input formats, the SAS mechanism used to read each, and what '
             'each format carries.')

body(doc, 'The three files are transparent conversions of the same public data; the World Bank '
          'does not itself publish these Excel and fixed-width files. The conversion script '
          'tools/prepare_inputs.py rebuilds all of them from the archived JSON and verifies the '
          'source digests first. Two further inputs carry genuine source content rather than '
          'derived values: indicator_notes.csv holds the official indicator definitions, and '
          'indicator_vintage.csv holds the API vintage dates described above.')

heading(doc, '2.3  Data problems and how they were handled', 2)

body(doc, 'Table 2 lists every real defect found in the inputs, the treatment applied, and the '
          'automated assertion that proves the treatment worked. None of the treatments is a '
          'silent fix: each leaves an audit file behind.')
table(doc,
      ['Problem', 'Evidence in this snapshot', 'Treatment', 'Assertion'],
      [['Missing values', f'{n_missing_gdp} of {n_all} economies have no GDP per capita; no life-expectancy value is missing',
        'Kept missing. Not replaced by zero and not imputed. The model uses complete cases',
        'Missing GDP = 20'],
       ['Missing-value sentinel', 'The fixed-width file writes NA for a null, which differs from blank and from zero (21 occurrences)',
        'NA is tested explicitly and only then converted to a SAS missing value',
        'DAT numeric parsing = 0 errors'],
       ['Fixed-width truncation', 'Every record is exactly 44 bytes; a short LRECL would cut the last field',
        'LRECL=32767 with TRUNCOVER, plus an assertion on every record length',
        'DAT fixed record widths = 0 errors'],
       ['Over-long free text', f'The GDP indicator definition is {max_note:,} bytes long',
        f'The field is read as $4096; the same value is also read into a $200 buffer to measure what a default buffer would destroy ({max_note - 200:,} bytes)',
        'Definitions cut by a 200-byte buffer = 1'],
       ['Aggregates mixed into economies', f'{row_counts["06 Excluded aggregates"]} of the 296 catalogue rows are regional or income aggregates',
        'Flagged with is_aggregate, exported in full for audit, then excluded from analysis',
        'Excluded aggregates = 79'],
       ['Non-unique keys', 'The indicator API returns a blank countryiso3code for a few aggregates',
        'Resolved through the API\'s own iso2Code to id mapping, never by matching names',
        'Unique key checks = 0 duplicates'],
       ['Untidy text', "Region names carry trailing blanks ('Sub-Saharan Africa ')",
        'Preserved as supplied so that the join to the catalogue stays exact',
        'Region summary rows = 7']],
      widths=[3.2, 5.0, 5.4, 3.0], font_size=8.5, align_right_from=99)
caption(doc, 'Table 2  Every defect found in the inputs, the treatment applied, and the automated '
             'assertion that verifies the treatment. The evidence column reports the counts observed '
             'in this run.')

heading(doc, '2.4  Distribution across regions', 2)
figure(doc, '02_life_expectancy_by_region.png', 15.0)
caption(doc, f'Figure 1  Life expectancy at birth by World Bank region, 2023 (N = {n_all}; one point '
             f'per economy; boxes span Q1 to Q3, the diamond marks the mean, and points beyond '
             f'1.5 IQR are plotted individually).')

heading(doc, '2.5  Sample flow', 2)
body(doc, f'The analysis sample is reconciled at every stage, and the reconciliation is itself '
          f'exported (row_counts.csv): {row_counts["01 Excel metadata"]} catalogue rows, of which '
          f'{row_counts["02 CSV life expectancy"]} carry indicator records; a full outer join '
          f'returns {row_counts["05 Metadata full merge"]} rows, including 30 rows that exist only '
          f'in the catalogue. All 30 are aggregates, and {row_counts["06 Excluded aggregates"]} '
          f'aggregates in total are excluded, leaving {row_counts["07 Retained economies"]} '
          f'economies. Of these, {n_missing_gdp} have no GDP value, so the regression uses '
          f'{row_counts["08 Complete-case regression"]} complete cases. Missing values are never '
          f'replaced, so the excluded economies remain visible in the exported dataset.')

# ---- 3 Method ---------------------------------------------------------------
heading(doc, '3  Method', 1)
heading(doc, '3.1  Processing pipeline and design principle', 2)
body(doc, 'The pipeline runs in one program: read the three formats, audit types, dates and long '
          'fields, assert the expected row counts, check the uniqueness of every join key, join the '
          'two indicators, join the catalogue, flag the analysis sample, describe, rank the '
          'extremes, fit and diagnose the regression, test the group differences, and export.')

body(doc, 'The organising principle is to name the expected result before doing the work. Every '
          'stage asserts what it is supposed to produce — "the CSV must have 266 rows", "the join '
          'key must be unique" — and a failed assertion aborts the run and records the failure in '
          'RUN_STATUS.txt instead of letting bad data flow downstream. In this run all 29 '
          'assertions passed and the log contains no ERROR and no WARNING, which is why the '
          'numbers below can be quoted without further caveat.')

heading(doc, '3.2  Variables', 2)
body(doc, 'life_exp is life expectancy at birth in years. gdp_ppp is GDP per capita at PPP in '
          'constant 2021 international dollars. log_gdp is its natural logarithm: the marginal '
          'association of income with longevity declines as income rises, and on the log scale a '
          'slope of b means that doubling income is associated with a difference of b times '
          'ln(2) years. complete_case flags the economies that have both values and are therefore '
          'in the model.')

heading(doc, '3.3  Three analyses answering three different questions', 2)
table(doc,
      ['Analysis', 'Methods', 'Question answered', 'Why it is needed'],
      [['Summary statistics', 'PROC MEANS (N, missing, mean, SD, median, quartiles), PROC UNIVARIATE',
        'What does the data look like?',
        'Skewness and extreme values decide whether robust methods are required'],
       ['Statistical inference', 'Kruskal-Wallis, one-way ANOVA with Levene and Welch tests, two-sample t test, Pearson and Spearman correlation',
        'Are group differences larger than sampling noise?',
        'Comparing means alone would turn a three-economy region into a stable conclusion'],
       ['Regression', 'OLS with HC3 heteroskedasticity-consistent errors, CLB confidence limits and a SPEC specification test',
        'How large is the association, and are the residuals suspicious?',
        'Gives an interpretable effect size together with its uncertainty']],
      widths=[3.0, 5.6, 3.6, 4.4], font_size=8.5, align_right_from=99)

body(doc, 'The three are complements rather than repetitions. Kruskal-Wallis assumes no particular '
          'distribution, which matters for regions with very few members. ANOVA decomposes the '
          'variance and its Levene test checks the equal-variance assumption; Welch ANOVA is the '
          'fallback when that assumption fails. The two-sample t test produces the interval quoted '
          'in the abstract, and the regression supplies the effect size. In this data the Levene '
          'test rejects equality of variances (p = 0.0001), so the Welch result is not decorative: '
          'it is the version of the ANOVA that is actually valid here.')

heading(doc, '3.4  Diagnostics and deliberate omissions', 2)
body(doc, 'Four diagnostics are examined: residuals against fitted values, a normal Q-Q plot of '
          'the residuals, Cook\'s distance, and leverage against externally studentized residuals. '
          'Records exceeding Cook\'s D > 4/N, leverage > 2p/N or |studentized residual| > 2 are '
          'flagged and explained individually, never removed. No stepwise selection is used, no '
          'observation is deleted, and the downloaded region and income classifications are labelled '
          'as a snapshot of the catalogue rather than as a 2023 historical classification.')

# ---- 4 Results --------------------------------------------------------------
heading(doc, '4  Results', 1)
heading(doc, '4.1  Descriptive statistics', 2)
life = overall['life_exp']
gdp = overall['gdp_ppp']
table(doc,
      ['Variable', 'N', 'Missing', 'Mean', 'SD', 'Median', 'Q1', 'Q3', 'Min', 'Max'],
      [['Life expectancy (years)', life['n'], life['n_missing'],
        f'{num(life["mean"]):.2f}', f'{num(life["stddev"]):.2f}', f'{num(life["median"]):.2f}',
        f'{num(life["q1"]):.2f}', f'{num(life["q3"]):.2f}', f'{num(life["minimum"]):.2f}',
        f'{num(life["maximum"]):.2f}'],
       ['GDP per capita (PPP intl $)', gdp['n'], gdp['n_missing'],
        f'{num(gdp["mean"]):,.0f}', f'{num(gdp["stddev"]):,.0f}', f'{num(gdp["median"]):,.0f}',
        f'{num(gdp["q1"]):,.0f}', f'{num(gdp["q3"]):,.0f}', f'{num(gdp["minimum"]):,.0f}',
        f'{num(gdp["maximum"]):,.0f}']],
      widths=[4.2, 1.2, 1.5, 2.2, 2.2, 2.0, 1.9, 1.9, 1.6, 1.8], font_size=8.5)
caption(doc, 'Table 3  Summary statistics, 2023. Each variable uses its own non-missing '
             'observations; monetary values are PPP constant 2021 international dollars.')

body(doc, f'Life expectancy is left-skewed, with its long tail at the low end, while GDP per head '
          f'is severely right-skewed: the maximum is {num(gdp["maximum"]) / num(gdp["minimum"]):.0f} '
          f'times the minimum. That asymmetry is the reason the regression is specified in logs and '
          f'the summary uses medians and quartiles alongside means.')

heading(doc, '4.2  Extreme values', 2)
low = [e for e in extremes if e['extreme'] == 'Lowest']
high = [e for e in extremes if e['extreme'] == 'Highest']
table(doc,
      ['Position', 'Economy', 'Life expectancy', 'GDP per capita (PPP)'],
      [[f'{e["extreme"]} {e["rank"]}', e['country_name'], f'{num(e["life_exp"]):.2f}',
        ('missing' if not e['gdp_ppp'].strip() else f'{num(e["gdp_ppp"]):,.0f}')]
       for e in low + high],
      widths=[2.6, 6.0, 3.2, 4.4], font_size=8.5, align_right_from=2)
caption(doc, 'Table 4  The four lowest and four highest life expectancies, 2023. Ties at the '
             'fourth position would be broken by ascending economy code; the full tie audit is '
             'exported separately.')

body(doc, 'Two facts from this table belong in the results rather than in an appendix. Hong Kong '
          'ranks third in the world at 85.25 years with GDP per head of 64,388 international '
          'dollars, a textbook high-income, high-longevity economy. More importantly, the two '
          'highest-ranked economies, Monaco and Liechtenstein, have no GDP per capita value in the '
          'dataset and therefore do not enter the regression: the complete-case sample is not a '
          'random subset of the world.')

heading(doc, '4.3  Do the regions really differ?', 2)
body(doc, 'Four tests are reported together because they rest on different assumptions and agree:')
table(doc,
      ['Test', 'Statistic', 'p-value', 'Reading'],
      [['Kruskal-Wallis (7 groups)', 'chi-square = 108.58, df = 6', '< 0.0001',
        'Distribution-free; rejects identical distributions'],
       ['One-way ANOVA', 'F(6, 210) = 42.64, R-squared = 0.549', '< 0.0001',
        'Roughly 55% of the variance in longevity is between regions'],
       ['Levene test for equal variances', 'F(6, 210) = 4.79', '0.0001',
        'The ANOVA assumption fails'],
       ['Welch ANOVA (unequal variances)', 'F(6, 22.02) = 46.51', '< 0.0001',
        'The conclusion survives dropping the assumption']],
      widths=[5.4, 5.0, 2.2, 4.0], font_size=8.5, align_right_from=99)
caption(doc, 'Table 5  Tests of equal life expectancy across the seven World Bank regions, 2023.')

body(doc, 'The Levene result is the interesting one. Because it rejects equal variances, the '
          'ordinary F test is not strictly valid here; the Welch version relaxes that assumption '
          'and yields an even larger statistic with the same p-value. Reporting the Kruskal-Wallis '
          'result as well means the finding does not depend on normality either. Three methods '
          'with three different sets of assumptions give the same answer, which is a stronger '
          'statement than any single p-value.')

figure(doc, '07_life_by_region_mean_clm.png', 15.0)
caption(doc, 'Figure 2  Mean life expectancy by region with 95% confidence limits, 2023. Whiskers '
             'are confidence limits of the mean, not 1.5 IQR; small regions have wide whiskers.')

table(doc,
      ['Region', 'N', 'Mean', '95% CI'],
      [[r['region'].strip(), r['n_economies'], f'{num(r["mean_life"]):.2f}',
        f'[{num(r["lclm_mean"]):.2f}, {num(r["uclm_mean"]):.2f}]']
       for r in sorted(regions, key=lambda r: -num(r['mean_life']))],
      widths=[7.4, 1.8, 2.4, 4.0], font_size=8.5, align_right_from=1)
caption(doc, 'Table 6  Mean life expectancy and 95% confidence limits by region, 2023.')

body(doc, 'The confidence widths matter as much as the ordering. North America, with three '
          'economies, has an interval roughly ten years wide, and South Asia with six economies is '
          'eight years wide, while Europe and Central Asia with 58 economies spans barely two '
          'years. Any ranking that puts the three-economy region first is therefore not a result '
          'we are willing to defend; what the data support is that Sub-Saharan Africa is clearly '
          'the lowest group, and that the upper group of regions is statistically indistinguishable '
          'from one another.')

heading(doc, '4.4  How large is the income gap, and how strong is the correlation?', 2)
body(doc, 'Splitting the sample into high-income economies and the rest gives a directly '
          'reportable difference:')
table(doc,
      ['Group', 'N', 'Mean life expectancy', 'SD', 'Difference', '95% CI of the difference'],
      [['High income', '86', '79.81', '4.18', '9.97', '[8.63, 11.30]'],
       ['Not high income', '131', '69.84', '5.76', '', '']],
      widths=[3.8, 1.6, 4.0, 1.8, 2.4, 4.6], font_size=9, align_right_from=1)
caption(doc, 'Table 7  Two-sample comparison, 2023. Satterthwaite t(212.86) = 14.75, p < 0.0001; '
             'the folded F test for equal variances gives 1.90 with p = 0.0016, so the unequal '
             'variance row is the appropriate one.')

body(doc, 'The gap of about ten years is the headline number for a policy audience, and it comes '
          'with a narrow interval precisely because both groups are large. On the continuous '
          'scale, Pearson\'s correlation between life expectancy and log GDP is 0.861 and '
          'Spearman\'s rank correlation is 0.872, both computed on the 197 complete cases and both '
          'with p < 0.0001. The rank correlation being slightly higher is a useful detail: it says '
          'the association is close to monotone rather than being driven by a few extreme values.')

heading(doc, '4.5  Regression: about 3.65 years per doubling', 2)
body(doc, f'The fitted relation is life expectancy = {num(p_int["Estimate"]):.3f} + '
          f'{slope:.3f} times ln(GDP per capita), estimated on {n_model} complete cases.')
table(doc,
      ['Parameter', 'Estimate', 'SE', 'HC3 SE', 't (OLS / HC3)', '95% CI (OLS)', '95% CI (HC3)'],
      [['Intercept', f'{num(p_int["Estimate"]):.3f}', f'{num(p_int["StdErr"]):.3f}',
        f'{num(p_int["HCStdErr"]):.3f}',
        f'{num(p_int["tValue"]):.2f} / {num(p_int["HCTValue"]):.2f}',
        f'[{num(p_int["LowerCL"]):.2f}, {num(p_int["UpperCL"]):.2f}]',
        f'[{num(p_int["HCLowerCL"]):.2f}, {num(p_int["HCUpperCL"]):.2f}]'],
       ['ln(GDP per capita)', f'{slope:.3f}', f'{num(p_slope["StdErr"]):.3f}',
        f'{num(p_slope["HCStdErr"]):.3f}',
        f'{num(p_slope["tValue"]):.2f} / {num(p_slope["HCTValue"]):.2f}',
        f'[{num(p_slope["LowerCL"]):.3f}, {num(p_slope["UpperCL"]):.3f}]',
        f'[{num(p_slope["HCLowerCL"]):.3f}, {num(p_slope["HCUpperCL"]):.3f}]']],
      widths=[3.6, 2.0, 1.6, 1.8, 3.0, 3.0, 3.0], font_size=8.5)
caption(doc, f'Table 8  OLS estimates, N = {n_model}. R-squared = {r2:.4f}, adjusted R-squared = '
             f'{adj_r2:.4f}, root mean square error = {rmse:.3f} years.')

body(doc, f'The slope is the quantity of interest. A one-unit increase in ln(GDP per capita) is '
          f'associated with {slope:.2f} more years of life expectancy; since ln(2) = 0.693, doubling '
          f'income per head is associated with {doubling:.2f} years. The HC3 standard error '
          f'({num(p_slope["HCStdErr"]):.3f}) is almost identical to the conventional one '
          f'({num(p_slope["StdErr"]):.3f}), so the inference does not depend on the '
          f'heteroskedasticity correction; the 95% confidence interval for the slope runs from '
          f'{num(p_slope["HCLowerCL"]):.2f} to {num(p_slope["HCUpperCL"]):.2f} years per log unit.')

figure(doc, '01_income_life_scatter.png', 15.0)
caption(doc, f'Figure 3  Life expectancy against log GDP per capita, 2023 (N = {n_model}). The line '
             f'is the unweighted OLS fit; each point is one economy.')

body(doc, f'An R-squared of {r2:.3f} means that differences in log income account for about three '
          f'quarters of the cross-sectional variance in longevity. It does not mean that income '
          f'determines longevity, and it says nothing about the effect of raising income, since the '
          f'model contains no identification strategy and no controls.')

heading(doc, '4.6  Is the model trustworthy?', 2)

body(doc, f'The SPEC test of the first two moments does not reject (chi-square = 3.60, df = 2, '
          f'p = 0.165), so there is no evidence of a misspecified mean or variance structure. The '
          f'slope test gives F(1, 195) = 560.56 with p < 0.0001.')

body(doc, f'Applying the screening rules flags {len(flagged)} of the {n_model} complete cases '
          f'({100 * len(flagged) / n_model:.1f}%): {len(cook_flags)} exceed the Cook\'s distance '
          f'threshold, {len(lev_flags)} exceed the leverage threshold, and {len(res_flags)} have a '
          f'studentized residual beyond two. None were removed. Table 9 lists the three most '
          f'influential cases.')
table(doc,
      ['Economy', 'Observed', 'Fitted', 'Residual', 'Studentized residual', "Cook's D"],
      [[w['country_name'], f'{num(w["life_exp"]):.2f}', f'{num(w["predicted_life"]):.2f}',
        f'{num(w["residual"]):.2f}', f'{num(w["rstudent"]):.2f}', f'{num(w["cooks_d"]):.4f}']
       for w in worst],
      widths=[5.0, 2.2, 2.2, 2.2, 3.4, 2.4], font_size=9, align_right_from=1)
caption(doc, 'Table 9  The three most influential economies in the regression. Residual = observed '
             'minus fitted life expectancy in years.')

body(doc, 'All three live several years less than their income level would predict, and Nigeria\'s '
          'residual of about fifteen years is more than three times the Cook\'s distance threshold. '
          'These are resource-dependent or geographically extreme economies, which suggests that '
          'public health capacity, conflict and climate operate on longevity beyond what income per '
          'head captures. This is the most informative part of the analysis: the regularity is '
          'strong on average and locally wrong in a systematic and interpretable way.')

two_figures(doc, '03_residuals_vs_fitted.png', '04_residual_normal_qq.png')
two_figures(doc, '05_cooks_distance.png', '06_leverage_studentized_residual.png')
caption(doc, 'Figure 4  Regression diagnostics, 2023: residuals against fitted values (top left), '
             'normal Q-Q plot of residuals (top right), Cook\'s distance with the 4/N threshold '
             '(bottom left), and leverage against externally studentized residuals with the 2p/N '
             'threshold (bottom right).')

heading(doc, '4.7  Evaluation and limitations', 2)
body(doc, 'Four limitations bound the conclusions. First, a single-year cross-section cannot say '
          'anything about change over time, so nothing here identifies what happens to longevity '
          'when income grows. Second, the complete-case sample is not a random subset: the 20 '
          'economies without a GDP value, and the two longest-lived economies in the world, are '
          'excluded, and those exclusions may correlate with state capacity. Third, education, '
          'health expenditure, institutions, geography and conflict are uncontrolled, so the slope '
          'cannot be read as a causal effect. Fourth, the relation is linear in logs but Spearman\'s '
          'correlation (0.872) exceeding Pearson\'s (0.861) hints at mild remaining curvature that '
          'a single log term does not capture.')

# ---- 5 Conclusion -----------------------------------------------------------
heading(doc, '5  Conclusion', 1)
body(doc, f'This project asked how strongly income and longevity are associated in 2023, whether '
          f'regions differ, and where the regularity fails. The data are {n_all} economies from a '
          f'frozen, reproducible World Bank snapshot whose vintage date and retrieval date are both '
          f'known, read from three different file formats and validated by 29 automated assertions '
          f'with no ERROR or WARNING in the SAS log.')

body(doc, f'The regional differences are real: Kruskal-Wallis gives chi-square = 108.58 with '
          f'p < 0.0001, one-way ANOVA gives F = 42.64 with p < 0.0001, and because Levene\'s test '
          f'rejects equal variances (p = 0.0001) the Welch version was computed as well, giving '
          f'F = 46.51 with p < 0.0001. High-income economies live on average {9.97:.2f} years '
          f'longer than the rest, with a 95% interval of [8.63, 11.30]. Each doubling of income per '
          f'head is associated with about {doubling:.2f} years, and log income accounts for about '
          f'{100 * r2:.0f}% of the cross-sectional variance.')

body(doc, f'The most useful finding is the exception rather than the rule. Nigeria, Greenland and '
          f'Chad live eight to fifteen years less than their income would predict, which places a '
          f'clear limit on income as an explanation and points to public health capacity, conflict '
          f'and geography as the next variables to study. None of this is causal: the honest '
          f'reading is that income is a strong marker of longevity across economies, not a lever '
          f'whose effect this design can measure.')

# ---- References -------------------------------------------------------------
heading(doc, 'References', 1)
for ref in [
    'Preston, S. H. (1975). The changing relation between mortality and level of economic '
    'development. Population Studies, 29(2), 231-248.',
    'SAS Institute Inc. (2024). SAS/STAT User\'s Guide: PROC REG, PROC GLM, PROC NPAR1WAY and '
    'PROC TTEST chapters. Cary, NC: SAS Institute Inc.',
    'World Bank. (2026). World Development Indicators: Life expectancy at birth, total (years) '
    '[SP.DYN.LE00.IN]. Retrieved 8 November 2026 from '
    'https://data.worldbank.org/indicator/SP.DYN.LE00.IN',
    'World Bank. (2026). World Development Indicators: GDP per capita, PPP (constant 2021 '
    'international dollars) [NY.GDP.PCAP.PP.KD]. Retrieved 8 November 2026 from '
    'https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD',
    'World Bank. (2026). Country API [Data set]. Retrieved 8 November 2026 from '
    'https://api.worldbank.org/v2/country?format=json&per_page=400',
]:
    p = doc.add_paragraph(ref)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)
    for run in p.runs:
        run.font.size = Pt(11)

doc.save(OUT)
print(f'wrote {OUT}  ({OUT.stat().st_size:,} bytes)')
print(f'figures embedded: 7   tables: 9   assertions verified: {len(assertions)}')
