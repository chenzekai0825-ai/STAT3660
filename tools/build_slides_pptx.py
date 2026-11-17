#!/usr/bin/env python3
"""Build the presentation for the group project.

    python3 tools/build_slides_pptx.py

Reads  : results/sas/*.png, results/sas/*.csv
Writes : docs/STAT3660_Slides.pptx   (12 slides, 16:9, slide numbers, speaker notes)

The deck is in English to match the course materials and the SAS figure labels.
The .pptx is a local deliverable: it is git-ignored and never committed, because
the slides are submitted to OLE rather than kept in the repository.
"""
import csv
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'results' / 'sas'
OUT = ROOT / 'docs' / 'STAT3660_Slides.pptx'

NAVY = RGBColor(0x1F, 0x3B, 0x57)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
GREY = RGBColor(0x40, 0x40, 0x40)
LIGHT = RGBColor(0xDC, 0xE6, 0xF1)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT = RGBColor(0xC0, 0x39, 0x2B)
FAINT = RGBColor(0x90, 0x90, 0x90)


def num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def rows(name):
    with (RES / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


params = rows('regression_parameters.csv')
slope = num(next(p for p in params if p['Variable'] == 'log_gdp')['Estimate'])
doubling = slope * 0.6931471805599453
# regression_fit.csv holds two label/value pairs per row: read them by position,
# because the labels are localised to the SAS session language.
_fit = rows('regression_fit.csv')
r2 = num(_fit[0]['cValue2'])
diag = rows('regression_diagnostics.csv')
n_model = len(diag)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


# ------------------------------------------------------------------ helpers
def textbox(slide, left, top, width, height, text, size=18, bold=False, italic=False,
            color=GREY, align=PP_ALIGN.LEFT, font='Calibri', line_spacing=1.15):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    para = frame.paragraphs[0]
    para.alignment = align
    para.line_spacing = line_spacing
    run = para.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font
    return box


def slide_title(slide, title, subtitle=None):
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), prs.slide_width, Inches(1.05))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    bar.shadow.inherit = False
    textbox(slide, 0.5, 0.18, 12.3, 0.7, title, size=28, bold=True, color=WHITE)
    if subtitle:
        textbox(slide, 0.5, 1.15, 12.3, 0.4, subtitle, size=14, italic=True, color=BLUE)


def bullets(slide, items, top=1.7, left=0.65, width=12.0, size=19, gap=0.62):
    for index, item in enumerate(items):
        if isinstance(item, tuple):
            text, level = item
        else:
            text, level = item, 0
        marker = '>  ' if level == 0 else '-  '
        textbox(slide, left + 0.45 * level, top + gap * index, width - 0.45 * level, 0.55,
                marker + text, size=size if level == 0 else size - 2,
                color=GREY if level == 0 else RGBColor(0x60, 0x60, 0x60))


def table(slide, header, data, left, top, width, height, font=13, col_widths=None):
    shape = slide.shapes.add_table(len(data) + 1, len(header), Inches(left), Inches(top),
                                   Inches(width), Inches(height))
    tbl = shape.table
    if col_widths:
        total = sum(col_widths)
        for i, w in enumerate(col_widths):
            tbl.columns[i].width = Emu(int(Inches(width) * w / total))
    for c, text in enumerate(header):
        cell = tbl.cell(0, c)
        cell.text = str(text)
        cell.fill.solid()
        cell.fill.fore_color.rgb = BLUE
        para = cell.text_frame.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        for run in para.runs:
            run.font.size = Pt(font)
            run.font.bold = True
            run.font.color.rgb = WHITE
    for r, row in enumerate(data, start=1):
        for c, text in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = str(text)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.RIGHT if c > 0 and len(str(text)) < 18 else PP_ALIGN.LEFT
            for run in para.runs:
                run.font.size = Pt(font)
                run.font.color.rgb = GREY
    return tbl


def picture(slide, name, left, top, height=None, width=None):
    path = RES / name
    if not path.is_file():
        textbox(slide, left, top, 4, 0.6, f'[missing {name}]', size=12, color=ACCENT)
        return
    if height:
        slide.shapes.add_picture(str(path), Inches(left), Inches(top), height=Inches(height))
    else:
        slide.shapes.add_picture(str(path), Inches(left), Inches(top), width=Inches(width))


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def slide_number(slide, index, total):
    """Bottom-right page number. A plain text box rather than a placeholder field,
    so that it is visible in every viewer and survives export to PDF."""
    textbox(slide, 11.85, 7.02, 1.05, 0.34, f'{index} / {total}', size=11,
            color=FAINT, align=PP_ALIGN.RIGHT)


# ------------------------------------------------------------------ 1 title
s = prs.slides.add_slide(BLANK)
band = s.shapes.add_shape(1, Inches(0), Inches(0), prs.slide_width, Inches(4.3))
band.fill.solid()
band.fill.fore_color.rgb = NAVY
band.line.fill.background()
band.shadow.inherit = False
textbox(s, 0.9, 1.15, 11.6, 1.0, 'Income and Life Expectancy in 2023', size=40, bold=True,
        color=WHITE)
textbox(s, 0.9, 2.25, 11.6, 0.8, 'A cross-section of 217 World Bank economies',
        size=24, color=RGBColor(0xBD, 0xD7, 0xEE))
textbox(s, 0.9, 3.15, 11.6, 0.6, 'STAT 3660SEF SAS Programming  |  2026 Autumn  |  Group ______',
        size=16, color=RGBColor(0xBD, 0xD7, 0xEE))
textbox(s, 0.9, 4.7, 11.6, 0.5,
        'Member 1  |  Member 2  |  Member 3  |  Member 4  |  Member 5', size=18, color=GREY)
textbox(s, 0.9, 5.25, 11.6, 0.5, 'Student IDs: replace this line with the five IDs',
        size=14, italic=True, color=FAINT)
textbox(s, 0.9, 6.2, 11.6, 0.5,
        'SAS 9.04.01M8  |  29 automated assertions passed  |  0 ERROR, 0 WARNING in the log',
        size=13, color=BLUE)
notes(s, 'Opening, 15 seconds. We study an old question: the link between money and longevity. We do '
         'not run yet another textbook regression; we answer three things at once: how strong the '
         'association is, whether regional differences are real, and where the regularity fails. The '
         'line at the bottom establishes credibility first: the code really ran, 29 assertions passed, '
         'and the log has no ERROR and no WARNING.')

# ------------------------------------------------------------------ 2 why
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Why this question is still worth asking',
            'The regularity is famous; the interesting part is where it breaks')
bullets(s, [
    'Preston (1975): income and longevity are strongly associated, one of the most robust regularities in development economics',
    'Three mistakes are still common when quoting it:',
    ('treating the association as a causal effect', 1),
    ('comparing group means without looking at the distributions', 1),
    ('ranking regions that contain three economies', 1),
    'Our three design decisions:',
    ('one single year (2023), so no mixing of "latest available year" across economies', 1),
    ('one economy = one observation, equal weight and not population-weighted', 1),
    ('inference and regression reported separately, not merged into one p-value', 1),
])
notes(s, 'Twenty seconds. Why list the mistakes first? Because the most common question is whether '
         'this is causal, so we answer it before it is asked: it is an association analysis. Also '
         'explain the equal weighting: population weighting would answer where most people live, which '
         'is a different question.')

# ------------------------------------------------------------------ 3 data
s = prs.slides.add_slide(BLANK)
slide_title(s, 'One snapshot, three file formats',
            'World Bank WDI 2023  |  source updated 2026-10-08  |  snapshot retrieved 2026-11-08')
table(s, ['Format', 'File', 'SAS mechanism', 'Content'],
      [['Excel', 'economies.xlsx', 'PROC IMPORT DBMS=XLSX', '296 catalogue rows'],
       ['Delimited', 'life_expectancy.csv', 'DATA step, INFILE DSD', '266 life records'],
       ['Fixed width', 'gdp_ppp.dat', 'column pointers @1 @5 @10 @21', '266 GDP records, 44 bytes/line']],
      left=0.65, top=1.75, width=12.0, height=2.1, font=14, col_widths=[1.6, 3.2, 4.2, 3.4])
textbox(s, 0.65, 4.15, 12.0, 0.5,
        'All three are transparent conversions of the same public data, not three independent surveys.',
        size=15, italic=True, color=BLUE)
bullets(s, [
    'Why three formats: real data arrives from different systems, and a headerless fixed-width export must be parsed by column position',
    'The snapshot is reproducible: five raw API responses frozen byte for byte with SHA-256 and download time',
    'Every number in this deck can be regenerated offline from that archive',
], top=4.75, size=16, gap=0.55)
notes(s, 'Thirty seconds. Explain the three formats before anyone asks: this is not box-ticking, it is '
         'how real data arrives. The fixed-width point matters most: 44 bytes, no header, so reading it '
         'with a delimiter gives nonsense. Then the snapshot: source updated 2026-10-08, retrieved '
         '2026-11-08, raw JSON archived with hashes.')

# ------------------------------------------------------------------ 4 dirty data
s = prs.slides.add_slide(BLANK)
slide_title(s, 'The data is messy, here is what we did about it',
            'Every treatment leaves an audit file; nothing is a silent fix')
table(s, ['Problem', 'Evidence', 'Treatment', 'Assertion'],
      [['Missing values', '20 of 217 economies lack GDP', 'kept missing, never zero-filled', 'Missing GDP = 20'],
       ['Sentinel', 'NA used for null (21 cases)', 'tested explicitly, then set missing', 'parse errors = 0'],
       ['Fixed width', 'exactly 44 bytes per record', 'LRECL + TRUNCOVER, assert 44', 'width errors = 0'],
       ['Over-long text', 'definition is 1,342 bytes', '$4096 read; a $200 buffer loses 1,142', 'truncated = 1'],
       ['Aggregates', '79 of 296 rows are aggregates', 'flagged, exported, then excluded', 'excluded = 79'],
       ['Non-unique keys', '10 blank iso3 codes', "resolved via the API's own mapping", 'duplicates = 0']],
      left=0.65, top=1.7, width=12.0, height=3.4, font=12,
      col_widths=[2.4, 3.6, 4.2, 2.6])
textbox(s, 0.65, 5.45, 12.0, 0.45,
        '29 automated assertions in total, all passed; RUN_STATUS.txt = COMPLETED',
        size=17, bold=True, color=NAVY)
textbox(s, 0.65, 5.95, 12.0, 0.8,
        'The last row is the one that matters: matching names instead of codes gives results that look right and are wrong.',
        size=14, italic=True, color=BLUE)
notes(s, 'Forty seconds, this is the slide that earns implementation marks. Pick two rows. First, the '
         'over-long field: the definition is 1,342 bytes, a 200-byte buffer loses 1,142 of them, and we '
         'measure that at run time instead of asserting a pre-computed answer. Second, the last row: '
         'the World Bank API leaves iso3 blank for some aggregates, so matching by name produces '
         'results that look right and are wrong. Close with: all 29 checks are program assertions, not '
         'something we eyeballed.')

# ------------------------------------------------------------------ 5 sample flow
s = prs.slides.add_slide(BLANK)
slide_title(s, 'From 296 catalogue rows to 197 complete cases',
            'Reconciled at every stage in row_counts.csv')
steps = ['296 catalogue rows', '266 with indicator records', '296 after the full outer join',
         '79 aggregates excluded', '217 economies', '20 without GDP', '197 complete cases']
for i, step in enumerate(steps):
    top = 1.75 + i * 0.66
    box = s.shapes.add_shape(1, Inches(1.3), Inches(top), Inches(6.4), Inches(0.5))
    box.fill.solid()
    box.fill.fore_color.rgb = LIGHT if i % 2 == 0 else WHITE
    box.line.color.rgb = BLUE
    box.shadow.inherit = False
    box.text_frame.text = step
    for para in box.text_frame.paragraphs:
        for run in para.runs:
            run.font.size = Pt(15)
            run.font.color.rgb = NAVY
textbox(s, 8.2, 1.9, 4.4, 3.4,
        '30 rows exist only in the catalogue and are all aggregates. We classify them first, then '
        'exclude them, and keep them in the exported file.',
        size=15, color=GREY)
textbox(s, 8.2, 4.5, 4.4, 2.0,
        'Excluding is not deleting: the exported dataset keeps all 217 economies, including the 20 '
        'without a GDP value, so the exclusion stays visible and reversible.',
        size=13, italic=True, color=BLUE)
notes(s, 'Twenty-five seconds. The purpose of this slide is to show that we did not quietly drop data. '
         'Emphasise that excluding is not deleting: the final CSV keeps all 217 economies including the '
         '20 without GDP; they simply do not enter the regression.')

# ------------------------------------------------------------------ 6 methods
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Three analyses, three different questions',
            'Chosen because each answers something the others cannot')
table(s, ['Analysis', 'Methods', 'Question answered'],
      [['Summary statistics', 'PROC MEANS, PROC UNIVARIATE', 'What does the data look like?'],
       ['Statistical inference', 'Kruskal-Wallis, ANOVA (+Levene, Welch),\ntwo-sample t, Pearson and Spearman',
        'Are group differences larger than noise?'],
       ['Regression', 'OLS with HC3, CLB and a SPEC test', 'How large is the association?']],
      left=0.65, top=1.75, width=12.0, height=2.6, font=14, col_widths=[3.0, 5.4, 3.6])
textbox(s, 0.65, 4.65, 12.0, 0.5,
        'Levene rejects equal variances (p = 0.0001), so the Welch ANOVA is not decorative.',
        size=17, bold=True, color=ACCENT)
bullets(s, [
    'Kruskal-Wallis assumes no distribution, which protects the three-economy regions',
    'Welch ANOVA is valid when variances differ, which they do here',
    'The t test supplies the interval we quote; the regression supplies the effect size',
], top=5.25, size=15, gap=0.52)
notes(s, 'Thirty-five seconds. These three are complements, not repetition: each covers something the '
         'others cannot. The red line is the point: Levene rejects equal variances, so the ordinary F '
         'test is not strictly valid and Welch is required, not optional. If asked why we do not just '
         'report one p-value, this is the answer.')

# ------------------------------------------------------------------ 7 regression
s = prs.slides.add_slide(BLANK)
slide_title(s, f'Q1  About {doubling:.2f} more years per doubling of income',
            'OLS on 197 complete cases, 95% confidence intervals')
picture(s, '01_income_life_scatter.png', 0.55, 1.6, height=5.1)
textbox(s, 8.9, 1.75, 4.2, 0.6, f'Slope  {slope:.3f}', size=26, bold=True, color=NAVY)
textbox(s, 8.9, 2.3, 4.2, 0.5, 'HC3 SE 0.211   |   95% CI [4.85, 5.68]', size=14, color=GREY)
textbox(s, 8.9, 3.05, 4.2, 0.6, f'R-squared  {r2:.3f}', size=26, bold=True, color=NAVY)
textbox(s, 8.9, 3.6, 4.2, 0.5, 'about three quarters of the cross-sectional variance', size=13,
        color=GREY)
textbox(s, 8.9, 4.35, 4.2, 0.6, 'RMSE  3.61 years', size=20, bold=True, color=NAVY)
textbox(s, 8.9, 5.25, 4.2, 1.6,
        'Association, not causation. There is no identification strategy and no controls.',
        size=14, italic=True, color=ACCENT)
notes(s, f'Forty seconds, this is the main result. Be precise: a slope of {slope:.2f} means that one '
         f'natural-log unit of GDP per capita is associated with 5.27 more years; since ln(2) = 0.693, '
         f'doubling income corresponds to {doubling:.2f} years. The HC3 standard error of 0.211 is '
         f'nearly identical to the conventional 0.222, so the inference does not depend on the '
         f'heteroskedasticity correction. Finish with the caveat: average difference, not raising income '
         f'lengthens life.')

# ------------------------------------------------------------------ 8 regions
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Q2  The regional gaps are real, and assumption-free',
            'Three tests, three sets of assumptions, the same answer')
picture(s, '07_life_by_region_mean_clm.png', 0.5, 1.6, height=4.5)
table(s, ['Test', 'Statistic', 'p'],
      [['Kruskal-Wallis', 'chi2 = 108.58 (df 6)', '< .0001'],
       ['ANOVA', 'F(6, 210) = 42.64', '< .0001'],
       ['Levene', 'F(6, 210) = 4.79', '0.0001'],
       ['Welch ANOVA', 'F(6, 22.02) = 46.51', '< .0001']],
      left=7.6, top=1.75, width=5.3, height=2.0, font=12, col_widths=[2.2, 3.0, 1.4])
textbox(s, 7.6, 4.0, 5.3, 1.4,
        'Levene rejects equal variances, so the ordinary F test is not strictly valid. Welch relaxes '
        'that assumption and the statistic gets larger, so the conclusion does not depend on it.',
        size=12, color=GREY)
textbox(s, 7.6, 5.5, 5.3, 1.2,
        'North America: 3 economies, CI width about 10 years.\n'
        'Sub-Saharan Africa is clearly lowest (64.56).',
        size=12, italic=True, color=BLUE)
notes(s, 'Forty-five seconds. This is the slide that scores and the slide that can trip us up. Go in '
         'order: Kruskal-Wallis assumes no distribution, ANOVA decomposes the variance, Levene rejects '
         'equal variances, so we switch to Welch, and Welch gives a larger F with the same p-value. '
         'Three methods with three assumptions agree. Then state the weakness ourselves: North America '
         'has only 3 economies and an interval about ten years wide, so we do not rank regions; what '
         'the data support is that Sub-Saharan Africa is clearly lowest.')

# ------------------------------------------------------------------ 9 income gap
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Q3  A gap of about ten years, and a correlation of 0.86',
            'High income (86 economies) against the rest (131)')
table(s, ['Group', 'N', 'Mean', 'SD'],
      [['High income', '86', '79.81', '4.18'],
       ['Not high income', '131', '69.84', '5.76'],
       ['Difference', '', '9.97', '95% CI [8.63, 11.30]']],
      left=0.65, top=1.75, width=6.1, height=2.2, font=14, col_widths=[2.6, 1.0, 1.3, 2.4])
textbox(s, 0.65, 4.1, 6.1, 1.2,
        'Satterthwaite t(212.86) = 14.75, p < .0001\n'
        'Folded F = 1.90, p = 0.0016, so variances differ and the unequal-variance row is correct',
        size=12, color=GREY)
textbox(s, 0.65, 5.5, 6.1, 1.1,
        'Pearson r = 0.861    Spearman rho = 0.872\n(both n = 197, p < .0001)',
        size=15, bold=True, color=NAVY)
picture(s, '02_life_expectancy_by_region.png', 7.05, 2.05, width=5.9)
notes(s, 'Thirty seconds. Report the interval, not the p-value: a difference of 9.97 years with a 95% '
         'interval of 8.63 to 11.30. Add the technical detail: the folded F test gives p = 0.0016, so '
         'the variances differ and the Satterthwaite row is the one to quote. Both correlations sit near '
         '0.87 with Spearman slightly higher, which means the relation is close to monotone rather than '
         'driven by extreme values.')

# ------------------------------------------------------------------ 10 diagnostics
s = prs.slides.add_slide(BLANK)
slide_title(s, 'The model holds up, and the exceptions are the finding',
            'SPEC p = 0.165  |  22 of 197 cases flagged  |  none removed')
picture(s, '03_residuals_vs_fitted.png', 0.5, 1.6, height=2.6)
picture(s, '05_cooks_distance.png', 4.7, 1.6, height=2.6)
table(s, ['Economy', 'Observed', 'Fitted', 'Residual'],
      [['Nigeria', '54.46', '69.80', '-15.34'],
       ['Greenland', '70.97', '81.41', '-10.43'],
       ['Chad', '55.07', '63.64', '-8.57']],
      left=0.65, top=4.5, width=7.4, height=1.7, font=13, col_widths=[2.6, 1.6, 1.6, 1.6])
textbox(s, 8.4, 4.35, 4.4, 2.2,
        'All three live well below their income prediction. Nigeria is 15 years low, with a '
        "studentized residual of -4.46 and a Cook's D three times the threshold.\n\n"
        'Resource dependence, conflict and geography bite beyond income per head.',
        size=12, color=GREY)
notes(s, 'Forty seconds. First, the model is fine: the SPEC joint test gives p = 0.165 and does not '
         'reject. Of 197 cases, 22 are flagged (9 Cook, 13 leverage, 6 residual) and none is removed, '
         'because deleting them would improve R-squared while making the conclusion indefensible. Then '
         'pivot to the three economies: Nigeria sits 15 years below its income prediction, with a '
         'studentized residual of -4.46 and a Cook distance three times the threshold. This is the most '
         'informative result in the project: income is strong on average and systematically wrong in '
         'specific places.')

# ------------------------------------------------------------------ 11 conclusions
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Three conclusions, four limits', 'What we can defend, and what we cannot')
textbox(s, 0.65, 1.65, 5.9, 0.4, 'Conclusions', size=18, bold=True, color=NAVY)
bullets(s, [
    'Regional gaps survive every test (chi2 = 108.58; F = 42.64; Welch F = 46.51)',
    'High income: +9.97 years (95% CI 8.63 to 11.30)',
    f'Each doubling of income: about {doubling:.2f} years, R-squared = {r2:.3f}',
    'But three economies miss by 8 to 15 years',
], top=2.1, left=0.65, width=5.9, size=13, gap=0.62)
textbox(s, 6.95, 1.65, 5.8, 0.4, 'Limitations', size=18, bold=True, color=ACCENT)
bullets(s, [
    'One year only, so it says nothing about change',
    'Complete cases exclude 20 economies without GDP, and the two longest-lived countries',
    'No control for education, health spending, institutions or geography',
    'Still linear in logs; Spearman above Pearson hints at curvature',
], top=2.1, left=6.95, width=5.8, size=13, gap=0.95)
textbox(s, 0.65, 6.35, 12.0, 0.6,
        'We state the limits ourselves: income is a strong marker of longevity, not a lever this design can measure.',
        size=15, italic=True, color=BLUE)
notes(s, 'Thirty seconds. Three conclusions and four limitations, all volunteered rather than dragged '
         'out. The second limitation is the one most likely to be probed: the 20 economies without GDP, '
         'and the two longest-lived countries in the world, are outside the regression, so the complete '
         'cases are not a random sample. Better that we say it first.')

# ------------------------------------------------------------------ 12 close
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Who did what, and how to reproduce it',
            'One command rebuilds the inputs, one command runs the analysis')
table(s, ['Member', 'Responsibility'],
      [['A', 'Data acquisition, three input formats, long-field and vintage audit'],
       ['B', 'Cleaning, missing values and sentinel handling, sample flags'],
       ['C', 'Merging, row reconciliation, assertion framework'],
       ['D', 'Descriptive statistics, extreme values, all seven figures'],
       ['E', 'Inference and regression, report editing']],
      left=0.65, top=1.7, width=7.3, height=3.0, font=13, col_widths=[1.4, 5.9])
bullets(s, [
    'prepare_inputs.py rebuilds every input offline from the frozen JSON',
    'validate_inputs.py runs 45 independent Python checks',
    'run_all.sas runs once, makes 29 assertions and writes RUN_STATUS.txt',
    'check_sas_run.py verifies the downloaded SAS output',
], top=4.9, left=0.65, width=12.0, size=14, gap=0.5)
notes(s, 'Twenty seconds to close. Make the division of labour concrete and checkable rather than a '
         'generic responsible-for-analysis line. End on reproducibility: four scripts, one command to '
         'rebuild the inputs, one to run the analysis, one to verify the output. Then stop and take '
         'questions.')

total = len(prs.slides)
for index, slide in enumerate(prs.slides, start=1):
    slide_number(slide, index, total)

prs.save(OUT)
print(f'wrote {OUT}  ({OUT.stat().st_size:,} bytes)')
print(f'slides: {total}   page numbers added to every slide')
