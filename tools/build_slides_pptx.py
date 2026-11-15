#!/usr/bin/env python3
"""Build the presentation (.pptx) for the group project.

    python3 tools/build_slides_pptx.py

Reads  : results/sas/*.png, results/sas/*.csv
Writes : docs/STAT3660_Slides.pptx   (12 slides, 16:9, Chinese speaker notes)

Slide text is in English because that is what is projected and what the SAS
figures are labelled in. The speaker notes are in Chinese so the team can
rehearse quickly; translate them if the presentation is delivered in English.
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


def num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def rows(name):
    with (RES / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


desc = {r['variable']: r for r in rows('descriptive_statistics.csv') if r['scope'] == 'Overall'}
params = rows('regression_parameters.csv')
slope = num(next(p for p in params if p['Variable'] == 'log_gdp')['Estimate'])
doubling = slope * 0.6931471805599453
regions = [r for r in rows('region_summary.csv') if r.get('_TYPE_') in ('1', '')]
diag = rows('regression_diagnostics.csv')
flagged = sum(1 for d in diag if d.get('flag_any') == '1')
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
        marker = '▪  ' if level == 0 else '–  '
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


def footer(slide, text):
    textbox(slide, 0.5, 7.0, 12.3, 0.35, text, size=11,
            color=RGBColor(0x90, 0x90, 0x90))


# ------------------------------------------------------------------ slide 1
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
textbox(s, 0.9, 3.15, 11.6, 0.6, 'STAT 3660SEF SAS Programming  ·  2026 Autumn  ·  Group ______',
        size=16, color=RGBColor(0xBD, 0xD7, 0xEE))
textbox(s, 0.9, 4.7, 11.6, 0.5,
        'Member 1 · Member 2 · Member 3 · Member 4 · Member 5', size=18, color=GREY)
textbox(s, 0.9, 5.25, 11.6, 0.5, 'Student IDs: replace this line with the five IDs',
        size=14, italic=True, color=RGBColor(0x90, 0x90, 0x90))
textbox(s, 0.9, 6.2, 11.6, 0.5,
        'SAS 9.04.01M8  ·  29 automated assertions passed  ·  0 ERROR, 0 WARNING in the log',
        size=13, color=BLUE)
notes(s, '开场 15 秒：我们研究一个老问题——钱和寿命的关系。'
         '但我们不做"再跑一次回归"，而是同时回答三件事：关联多大、地区差异是否真实、'
         '这条规律在哪些国家失灵。'
         '底部这行字先立住可信度：代码真跑过，29 项断言全过，日志里 0 个 ERROR、0 个 WARNING。')

# ------------------------------------------------------------------ slide 2
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Why this question is still worth asking', 'The regularity is famous; the interesting part is where it breaks')
bullets(s, [
    'Preston (1975): income and longevity are strongly associated — one of the most robust regularities in development economics',
    'Three mistakes are still common when quoting it:',
    ('treating the association as a causal effect', 1),
    ('comparing group means without looking at the distributions', 1),
    ('ranking regions that contain three economies', 1),
    'Our three design decisions:',
    ('one single year (2023) — no mixing of "latest available year" across economies', 1),
    ('one economy = one observation — equal weight, not population-weighted', 1),
    ('inference and regression reported separately, not merged into one p-value', 1),
])
notes(s, '20 秒。为什么要先讲三个错误？因为评委最常问的就是"你这算因果吗"。'
         '我们先自己说清楚：这是关联分析。'
         '"每个经济体等权"这一点也要主动解释：按人口加权回答的是"世界上多数人住在哪"，是另一个问题。')

# ------------------------------------------------------------------ slide 3
s = prs.slides.add_slide(BLANK)
slide_title(s, 'One snapshot, three file formats', 'World Bank WDI 2023 · source updated 2026-10-08 · snapshot retrieved 2026-11-08')
table(s, ['Format', 'File', 'SAS mechanism', 'Content'],
      [['Excel', 'economies.xlsx', 'PROC IMPORT DBMS=XLSX', '296 catalogue rows'],
       ['Delimited', 'life_expectancy.csv', 'DATA step, INFILE DSD', '266 life records'],
       ['Fixed width', 'gdp_ppp.dat', 'column pointers @1 @5 @10 @21', '266 GDP records, 44 bytes/line']],
      left=0.65, top=1.75, width=12.0, height=2.1, font=14, col_widths=[1.6, 3.2, 4.2, 3.4])
textbox(s, 0.65, 4.15, 12.0, 0.5,
        'All three are transparent conversions of the same public data — not three independent surveys.',
        size=15, italic=True, color=BLUE)
bullets(s, [
    'Why three formats: real data arrives from different systems; a headerless fixed-width export must be parsed by column position',
    'Snapshot is reproducible: 5 raw API responses frozen byte-for-byte with SHA-256 and download time',
    'Every number in this deck can be regenerated offline from that archive',
], top=4.75, size=16, gap=0.55)
notes(s, '30 秒。这里要抢在评委之前解释"为什么三种格式"——不是凑评分表，是因为真实数据来自不同系统。'
         '定宽文件那句是关键：44 字节、没有表头，必须用列指针解析，用分隔符读会全错。'
         '再说快照：源数据 10-08 更新、我们 11-08 下载，原始 JSON 冻结并记了哈希。')

# ------------------------------------------------------------------ slide 4
s = prs.slides.add_slide(BLANK)
slide_title(s, 'The data is messy — here is what we did about it', 'Every treatment leaves an audit file; nothing is a silent fix')
table(s, ['Problem', 'Evidence', 'Treatment', 'Assertion'],
      [['Missing values', '20 of 217 economies lack GDP', 'kept missing, never zero-filled', 'Missing GDP = 20'],
       ['Sentinel', "NA used for null (21 cases)", 'tested explicitly, then set missing', 'parse errors = 0'],
       ['Fixed width', 'exactly 44 bytes per record', 'LRECL + TRUNCOVER, assert 44', 'width errors = 0'],
       ['Over-long text', 'definition is 1,342 bytes', '$4096 read; $200 buffer loses 1,142', 'truncated = 1'],
       ['Aggregates', '79 of 296 rows are aggregates', 'flagged, exported, then excluded', 'excluded = 79'],
       ['Non-unique keys', '10 blank iso3 codes', "resolved via the API's own mapping", 'duplicates = 0']],
      left=0.65, top=1.7, width=12.0, height=3.4, font=12,
      col_widths=[2.4, 3.6, 4.2, 2.6])
textbox(s, 0.65, 5.45, 12.0, 0.45,
        '29 automated assertions in total — all passed; RUN_STATUS.txt = COMPLETED',
        size=17, bold=True, color=NAVY)
textbox(s, 0.65, 5.95, 12.0, 0.8,
        'The last row is the one that matters: matching names instead of codes gives results that look right and are wrong.',
        size=14, italic=True, color=BLUE)
notes(s, '40 秒，这页是拿分重点。挑两行讲：'
         '一是超长字段——指标定义 1342 字节，用 200 字节的缓冲会丢掉 1142 字节，我们是现场测量而不是事先写死。'
         '二是最后一行——世行 API 对个别汇总项返回空的 iso3，如果按名字猜代码，结果看起来对、其实错位。'
         '结尾强调：这 29 项都是程序断言，不是我们肉眼看的。')

# ------------------------------------------------------------------ slide 5
s = prs.slides.add_slide(BLANK)
slide_title(s, 'From 296 catalogue rows to 197 complete cases', 'Reconciled at every stage in row_counts.csv')
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
        '30 rows exist only in the catalogue and are all aggregates — we classify them first, '
        'then exclude them, and keep them in the exported file.',
        size=15, color=GREY)
textbox(s, 8.2, 4.5, 4.4, 2.0,
        'Excluding is not deleting: the exported dataset keeps all 217 economies, including the '
        '20 without a GDP value, so the exclusion is visible and reversible.',
        size=13, italic=True, color=BLUE)
notes(s, '25 秒。这页的作用是证明"我们没有悄悄丢数据"。'
         '"排除不等于删除"这句要说：最终 CSV 保留全部 217 个经济体，缺 GDP 的 20 个也在里面，只是不进回归。')

# ------------------------------------------------------------------ slide 6
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Three analyses, three different questions', 'Chosen because each answers something the others cannot')
table(s, ['Analysis', 'Methods', 'Question answered'],
      [['Summary statistics', 'PROC MEANS, PROC UNIVARIATE', 'What does the data look like?'],
       ['Statistical inference', 'Kruskal-Wallis, ANOVA (+Levene, Welch),\ntwo-sample t, Pearson / Spearman', 'Are group differences larger than noise?'],
       ['Regression', 'OLS with HC3, CLB and a SPEC test', 'How large is the association?']],
      left=0.65, top=1.75, width=12.0, height=2.6, font=14, col_widths=[3.0, 5.4, 3.6])
textbox(s, 0.65, 4.65, 12.0, 0.5,
        'Levene rejects equal variances (p = 0.0001) — so the Welch ANOVA is not decorative.',
        size=17, bold=True, color=ACCENT)
bullets(s, [
    'Kruskal-Wallis assumes no distribution — it protects the three-economy regions',
    'Welch ANOVA is valid when variances differ, which they do here',
    'The t test supplies the interval we quote; the regression supplies the effect size',
], top=5.25, size=15, gap=0.52)
notes(s, '35 秒。三个方法不是重复劳动，这页要讲清"各管一段"。'
         '重点在红色那行：Levene 拒绝了等方差，所以普通 ANOVA 前提不成立，Welch 是必须的而不是多余的。'
         '如果评委问"为什么不用一个 p 值搞定"，答案就在这里。')

# ------------------------------------------------------------------ slide 7
s = prs.slides.add_slide(BLANK)
slide_title(s, f'Q1  About {doubling:.2f} more years per doubling of income', 'OLS on 197 complete cases, 95% CI in brackets')
picture(s, '01_income_life_scatter.png', 0.55, 1.6, height=5.1)
textbox(s, 8.9, 1.75, 4.2, 0.6, f'Slope  {slope:.3f}', size=26, bold=True, color=NAVY)
textbox(s, 8.9, 2.3, 4.2, 0.5, 'HC3 SE 0.211   ·   95% CI [4.85, 5.68]', size=14, color=GREY)
textbox(s, 8.9, 3.05, 4.2, 0.6, f'R²  {num(rows("regression_fit.csv")[0]["cValue2"]):.3f}',
        size=26, bold=True, color=NAVY)
textbox(s, 8.9, 3.6, 4.2, 0.5, 'three quarters of the cross-sectional variance', size=13, color=GREY)
textbox(s, 8.9, 4.35, 4.2, 0.6, 'RMSE  3.61 years', size=20, bold=True, color=NAVY)
textbox(s, 8.9, 5.25, 4.2, 1.6,
        'Association, not causation. There is no identification strategy and no controls.',
        size=14, italic=True, color=ACCENT)
notes(s, f'40 秒，这是主干结果。'
         f'把话说死：斜率 {slope:.2f} 表示人均 GDP 每提高一个自然对数单位，寿命平均差 5.27 年；'
         f'因为 ln2=0.693，所以"翻一倍"对应 {doubling:.2f} 年。'
         f'HC3 标准误 0.211 和常规 0.222 几乎一样，说明推断不依赖异方差修正——这是个加分细节。'
         f'最后一定要说："平均差异"，不是"提高收入能延长寿命"。')

# ------------------------------------------------------------------ slide 8
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Q2  The regional gaps are real — and assumption-free', 'Three tests, three sets of assumptions, the same answer')
picture(s, '07_life_by_region_mean_clm.png', 0.5, 1.6, height=4.5)
table(s, ['Test', 'Statistic', 'p'],
      [['Kruskal-Wallis', 'χ² = 108.58 (df 6)', '< .0001'],
       ['ANOVA', 'F(6, 210) = 42.64', '< .0001'],
       ['Levene', 'F(6, 210) = 4.79', '0.0001'],
       ['Welch ANOVA', 'F(6, 22.02) = 46.51', '< .0001']],
      left=7.6, top=1.75, width=5.3, height=2.0, font=12, col_widths=[2.2, 3.0, 1.4])
textbox(s, 7.6, 4.0, 5.3, 1.3,
        'Levene rejects equal variances, so the ordinary F test is not strictly valid. '
        'Welch relaxes that assumption and the statistic gets larger — the conclusion does not '
        'depend on the assumption.', size=12, color=GREY)
textbox(s, 7.6, 5.55, 5.3, 1.2,
        'North America: 3 economies, CI width ≈ 10 years.\n'
        'Sub-Saharan Africa is clearly lowest (64.56).',
        size=12, italic=True, color=BLUE)
notes(s, '45 秒，这页最容易得分也最容易翻车。'
         '按顺序讲：KW 不假设分布、ANOVA 给出方差分解、Levene 拒绝了等方差、所以换 Welch，'
         'Welch 的 F 反而更大、p 依然小于 .0001 —— 三种方法三个假设，结论一致。'
         '然后主动交代弱点：North America 只有 3 个经济体、置信区间宽达 10 年，所以"哪个地区最好"我们不排名；'
         '能站得住的结论只有"撒哈拉以南非洲显著最低"。')

# ------------------------------------------------------------------ slide 9
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Q3  A gap of about ten years, and a correlation of 0.86', 'High income (86 economies) vs the rest (131)')
table(s, ['Group', 'N', 'Mean', 'SD'],
      [['High income', '86', '79.81', '4.18'],
       ['Not high income', '131', '69.84', '5.76'],
       ['Difference', '', '9.97', '95% CI [8.63, 11.30]']],
      left=0.65, top=1.75, width=6.1, height=2.2, font=14, col_widths=[2.6, 1.0, 1.3, 2.4])
textbox(s, 0.65, 4.1, 6.1, 1.2,
        'Satterthwaite t(212.86) = 14.75, p < .0001\n'
        'Folded F = 1.90, p = 0.0016 → unequal variances, so the unequal-variance row is correct',
        size=12, color=GREY)
textbox(s, 0.65, 5.5, 6.1, 1.1,
        'Pearson r = 0.861    Spearman ρ = 0.872\n(both n = 197, p < .0001)',
        size=15, bold=True, color=NAVY)
picture(s, '02_life_expectancy_by_region.png', 7.05, 2.05, width=5.9)
notes(s, '30 秒。报区间不报 p：差 9.97 年，95% 区间 [8.63, 11.30]。'
         '补充一句技术细节：折叠 F 检验 p=0.0016，说明两组方差不等，所以必须读 Satterthwaite 那一行——'
         '这类细节评委很爱追问。'
         '两个相关都在 0.87 左右、Spearman 略高，说明关系接近单调，不是被极端值拉出来的。')

# ------------------------------------------------------------------ slide 10
s = prs.slides.add_slide(BLANK)
slide_title(s, 'The model holds up — and the exceptions are the finding', 'SPEC p = 0.165 · 22 of 197 flagged · none removed')
picture(s, '03_residuals_vs_fitted.png', 0.5, 1.6, height=2.6)
picture(s, '05_cooks_distance.png', 4.7, 1.6, height=2.6)
table(s, ['Economy', 'Observed', 'Fitted', 'Residual'],
      [['Nigeria', '54.46', '69.80', '−15.34'],
       ['Greenland', '70.97', '81.41', '−10.43'],
       ['Chad', '55.07', '63.64', '−8.57']],
      left=0.65, top=4.5, width=7.4, height=1.7, font=13, col_widths=[2.6, 1.6, 1.6, 1.6])
textbox(s, 8.4, 4.35, 4.4, 2.2,
        'All three live well below their income prediction. Nigeria is −15 years, with a '
        "studentised residual of −4.46 and a Cook's D three times the threshold.\n\n"
        'Resource dependence, conflict and geography bite beyond income per head.',
        size=12, color=GREY)
notes(s, '40 秒。先说模型没问题：SPEC 联合检验 p=0.165，不拒绝；197 个案例里 22 个被标记（Cook 9、杠杆 13、残差 6），'
         '一个都没删——删了 R² 会更好看，但结论就不可辩护了。'
         '然后把这页的重点转到三个国家：尼日利亚比收入预测低 15 年，学生化残差 −4.46，Cook D 是阈值的三倍。'
         '这是整份报告最有信息量的发现：收入在平均意义上很强，但在个别地方系统性失灵。')

# ------------------------------------------------------------------ slide 11
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Three conclusions, four limits', 'What we can defend, and what we cannot')
textbox(s, 0.65, 1.65, 5.9, 0.4, 'Conclusions', size=18, bold=True, color=NAVY)
bullets(s, [
    'Regional gaps survive every test (χ² = 108.58; F = 42.64; Welch F = 46.51)',
    'High income: +9.97 years (95% CI 8.63–11.30)',
    f'Each doubling of income: about {doubling:.2f} years, R² = 0.742',
    'But three economies miss by 8–15 years',
], top=2.1, left=0.65, width=5.9, size=13, gap=0.62)
textbox(s, 6.95, 1.65, 5.8, 0.4, 'Limitations', size=18, bold=True, color=ACCENT)
bullets(s, [
    'One year — says nothing about change',
    'Complete cases exclude 20 economies without GDP, and the two longest-lived countries',
    'No control for education, health spending, institutions, geography',
    'Still linear in logs; Spearman > Pearson hints at curvature',
], top=2.1, left=6.95, width=5.8, size=13, gap=0.95)
textbox(s, 0.65, 6.35, 12.0, 0.6,
        'We state the limits ourselves: income is a strong marker of longevity, not a lever this design can measure.',
        size=15, italic=True, color=BLUE)
notes(s, '30 秒。结论三条、局限四条，都说在我们自己嘴里。'
         '局限里第二条最容易被追问：缺 GDP 的 20 个经济体，以及全球最长寿的摩纳哥和列支敦士登，都不在回归里——'
         '所以完整案例不是随机样本。主动说出来比被问出来强。')

# ------------------------------------------------------------------ slide 12
s = prs.slides.add_slide(BLANK)
slide_title(s, 'Who did what, and how to reproduce it', 'One command rebuilds inputs, one command runs the analysis')
table(s, ['Member', 'Responsibility'],
      [['A', 'Data acquisition, three input formats, long-field and vintage audit'],
       ['B', 'Cleaning, missing values and sentinel handling, sample flags'],
       ['C', 'Merging, row reconciliation, assertion framework'],
       ['D', 'Descriptive statistics, extreme values, all seven figures'],
       ['E', 'Inference and regression, report editing']],
      left=0.65, top=1.7, width=7.3, height=3.0, font=13, col_widths=[1.4, 5.9])
bullets(s, [
    'prepare_inputs.py — rebuilds every input offline from the frozen JSON',
    'validate_inputs.py — 45 independent Python checks',
    'run_all.sas — one run, 29 assertions, writes RUN_STATUS.txt',
    'check_sas_run.py — verifies the downloaded SAS output',
], top=4.9, left=0.65, width=12.0, size=14, gap=0.5)
notes(s, '20 秒收尾。分工要具体到"能验证的东西"，不要说"负责分析"。'
         '最后强调可复现：四个脚本，一条命令重建输入、一条命令跑完分析、一条命令验收结果。'
         '然后停住，等提问。')

prs.save(OUT)
print(f'wrote {OUT}  ({OUT.stat().st_size:,} bytes)')
print(f'slides: {len(prs.slides)}')
