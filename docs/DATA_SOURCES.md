# Data Sources, Conversion Rules and Field Dictionary

## Why these indicators, and what was actually downloaded

Both indicators come from the World Bank **World Development Indicators** (WDI, source 2) for the
year 2023. A single fixed year is used so that no economy is compared on a different reference year:
mixing "latest available year" values across economies would compare observations collected up to a
decade apart. GDP is measured at purchasing power parity in constant 2021 international dollars,
which compares real output across economies; longevity is life expectancy at birth for the total
population, in years. The two indicators each cover 217 non-aggregate economies, and 197 of those
have both values, which supports the descriptive, regional and log-GDP analyses.

The raw files keep the API bytes exactly as returned; nothing is re-serialised. Download and
conversion are separated, and SAS never touches the network. The exact download time (Hong Kong
time), URLs, SHA-256 digests, byte counts and API response headers are recorded in
`data/raw/manifest.json`. The source revises its data, so only an archived snapshot can reproduce
these figures.

`FILE_SHA256.txt` covers every file in the repository except itself, with **one deliberate
exception: `data/input/economies.xlsx`**. openpyxl writes new zip timestamps on every rebuild, so
the byte hash would change while the cell contents do not. That file is therefore verified cell by
cell against `countries.json` by `tools/validate_inputs.py`, which is a stricter check than a byte
hash. The CSV and DAT files have a fixed row layout, reproduce byte for byte, and are included in
the hash manifest.

| Raw file | Official download URL |
|---|---|
| countries.json | https://api.worldbank.org/v2/country?format=json&per_page=400 |
| life_2023.json | https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?date=2023&format=json&per_page=400&source=2 |
| gdp_2023.json | https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?date=2023&format=json&per_page=400&source=2 |
| life_metadata.json | https://api.worldbank.org/v2/indicator/SP.DYN.LE00.IN?format=json&source=2 |
| gdp_metadata.json | https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.PP.KD?format=json&source=2 |

Indicator definitions: [life expectancy glossary](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/SP.DYN.LE00.IN),
[GDP glossary](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/NY.GDP.PCAP.PP.KD).
API structure: [Country API queries](https://datahelpdesk.worldbank.org/knowledgebase/articles/898590-country-api-queries).
Attribution: World Bank, World Development Indicators, 2023 observations; see the manifest for the
download snapshot. Terms of use: [World Bank Dataset Terms of Use](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets).
The source organisation's own notes are preserved in the two `*_metadata.json` files.

## Conversion

The three input formats are **transparent conversions of the same set of real public data**. They are
not three independent surveys, and the repository does not imply that the World Bank publishes these
DAT or Excel files itself.

1. `countries.json` → `economies.xlsx`: `tools/prepare_inputs.py` builds the workbook with openpyxl,
   taking the code, name, region and income group, and setting `is_aggregate` to 1 when
   `region.id == 'NA'` and 0 otherwise. Rows are sorted by code. One sheet named `Economies`, the
   six variable names on the first row, all 296 rows retained. Source text is kept as supplied,
   including trailing blanks. The income group is catalogue information only and is not used as a
   2023 historical classification.
2. `life_2023.json` → `life_expectancy.csv`: the same script takes the code, year and value. A JSON
   null becomes an empty field, and values are written with round-trip precision.
   `period_start_raw = 2023-01-01` is an **annual period marker** derived from the year; it is not a
   measurement or collection date.
3. `gdp_2023.json` → `gdp_ppp.dat`: the same script writes each record as a 44-byte ASCII fixed-width
   line with no header. Code in columns 1–3, blank in 4, year in 5–8, blank in 9, the period marker
   in 10–19, blank in 20, and the GDP value or `NA` right-aligned in 21–44. Values use 17
   significant digits so that no rounding is introduced; null becomes `NA`.
4. `sourceNote` from the two `*_metadata.json` files → `indicator_notes.csv`: the real definitions are
   preserved, with real newlines, literal `\n` and repeated whitespace normalised to single spaces so
   that each definition fits one CSV line. **Only the two columns the source provides are kept**
   (`indicator_id`, `description`); no "correct answer" column is pre-computed. The length, whether a
   200-byte buffer would truncate it, and how many bytes would be lost are all measured inside SAS at
   run time. The longest definition is 1,342 bytes, SAS receives it in a `$4096` field, and the same
   record is also read into a `$200` field to demonstrate the truncation. The original notes remain in
   the JSON files.
5. `lastupdated` from the API response headers plus `manifest.json` → `indicator_vintage.csv`: this is
   where the project's **real dates** come from. `last_updated` is the `lastupdated` value in the World
   Bank API response (2026-10-08) and `retrieved_date` is the day the snapshot was downloaded
   (2026-11-08). Both are read as SAS dates and their difference is reported. The annual period marker
   (2023-01-01) is only a period marker and does not pretend to be a collection date.
6. A few aggregates have a blank `countryiso3code` in the indicator API. Their code is resolved
   through the API's own `country.id` → catalogue `iso2Code` mapping; names are never used to guess a
   code. The five mappings per indicator are saved in `key_mapping_audit.csv`. Note that `iso3` here
   means a **three-character World Bank code**, which is not guaranteed to be an ISO sovereign
   country code.

## Field dictionary and keys

| Field | SAS type / length | Meaning and rule |
|---|---|---|
| iso3 | char 3 | World Bank economy or aggregate code; unique key of the catalogue |
| country_name | char 180 | Economy or aggregate name |
| region_id / region | char 3 / 100 | Region code and name at download time; NA marks an aggregate |
| income_group | char 60 | Income group at download time, catalogue use only |
| is_aggregate | numeric | 1 = aggregate, 0 = economy; the analysis uses only 0 |
| year | numeric | 2023; the unique key of both indicators is (iso3, year) |
| period_start_raw / gdp_date_raw | char 10 | ISO text of the annual period marker, not an observation date |
| period_start / gdp_date | SAS numeric date | Read with `YYMMDD10.` and displayed the same way; 2023-01-01 is 23011 internally |
| life_raw / gdp_raw | char 32 / 24 | Raw value field before parsing; blanks and `NA` are kept for audit |
| life_exp | numeric | Life expectancy at birth in years; SP.DYN.LE00.IN |
| gdp_ppp | numeric | GDP per capita, PPP, constant 2021 international dollars; NY.GDP.PCAP.PP.KD |
| log_gdp | numeric | Natural log of GDP when GDP > 0; missing or non-positive values are not logged |
| has_life_row / has_gdp_row / has_metadata | numeric | Whether the source **record** exists, which differs from the value being missing |
| merge_status | char 32 | All three matched, catalogue only, indicator only, or one indicator absent |
| missing_life / missing_gdp | numeric | Variable-level missing flags, 1/0 |
| invalid_life / invalid_gdp | numeric | Life expectancy outside (0, 120] or non-positive GDP; both are 0 in this snapshot |
| complete_case | numeric | 1 if the economy enters the regression, otherwise 0 |
| exclusion_reason | char 100 | Inclusion or exclusion reason; the final CSV keeps every economy |
| indicator_id / description | char 24 / 4096 | Indicator code and the normalised original long definition |
| indicator_id / indicator_name | char 24 / 80 | `indicator_vintage.csv`: indicator code and official name |
| last_updated / retrieved | SAS numeric date | Date the source series was last updated (API `lastupdated`) and the snapshot retrieval date |

SAS first performs a full join of the two indicators on (iso3, year), then a full join to the
catalogue on iso3. Because there is a single study year, the indicator merge is also unique on iso3,
and the code verifies this rather than assuming it. Every duplicate key is exported and stops the run;
duplicates are never hidden by dropping rows. The 30 catalogue-only records are all aggregates, and
after the audit they are excluded together with the other 49 aggregates. An indicator null stays
"a record exists but the value is missing" and is never counted as a failed join.

## Analysis conventions

- Descriptive statistics: each variable uses its own available observations and reports N, missing N,
  mean, sample standard deviation, minimum, maximum, quartiles and median. SAS uses `QNTLDEF=5`;
  Python is cross-checked with `averaged_inverted_cdf`.
- Regression: 197 complete cases out of 217 economies, each economy equally weighted. The slope is the
  association between one natural-log unit of GDP and life expectancy, so a doubling of GDP
  corresponds to `beta × ln(2)` years. It must not be extrapolated to an individual-level income
  effect or to a causal effect.
- Diagnostics: conventional OLS estimates, the ordinary ANOVA and CLB intervals; HC3 robust standard
  errors and tests; the SPEC joint specification test; residual, normal Q-Q, Cook's distance, leverage
  and externally studentized residual plots. Cook's D > 4/N, leverage > 2p/N (p = 2) and
  |externally studentized residual| > 2 are flags only and never remove a row.
- Inference: `35_inference.sas` answers a different question — whether the differences between groups
  exceed random variation. It runs a Kruskal-Wallis test across regions, a one-way ANOVA with Levene's
  variance test and a Welch correction, a two-sample t test of high-income economies against the rest,
  and Pearson and Spearman correlations. These are reported separately from the regression because
  they answer a different question; see section 4 of the report.
- Complete cases may differ systematically from the economies with missing GDP. Geographic dependence,
  uncontrolled confounders and the linear specification all limit inference carried out on this
  snapshot. Region groups come from the current catalogue. The Python reference diagnostics do not
  impersonate the SAS SPEC test; the official interpretation follows the actual SAS output.
