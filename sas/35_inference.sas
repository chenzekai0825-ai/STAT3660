/* 35_inference.sas -- Statistical inference: do groups really differ?
   Run through run_all.sas. Input: PROJ.ANALYSIS_ALL; &OUT and &STUDY_YEAR.

   Section 30 answers "what is the association?" with descriptive statistics and
   an OLS fit. This section answers the separate question "are the differences
   between groups larger than sampling noise?" and therefore covers the third
   analysis type the checklist asks for: statistical inference, next to summary
   statistics and regression.

   Deliberately NO hard-coded p-value assertions here: a p-value is a result to be
   read, not a constant to freeze. The only assertion in this file is the row
   count of the exported group summary (seven World Bank regions). */

/* H1. Is life expectancy distributed differently across the regions?
   Kruskal-Wallis is the default for a class variable with more than two levels.
   It assumes no particular distribution, which matters because several regions
   hold few economies. A small p-value only says the distributions are not all
   identical: it does not say which regions differ. */
title "H1: life expectancy differs across regions? Kruskal-Wallis, &study_year";
footnote 'Rank-based test. Rejection means the seven distributions are not all identical, not which one differs.';
proc npar1way data=proj.analysis_all;
    class region;
    var life_exp;
run;
footnote;

/* H2. One-way ANOVA on the same grouping, with the assumptions made explicit.
   Levene's test is reported because the F test assumes equal variances; Welch's
   ANOVA is the fallback when that assumption fails. */
title "H2: one-way ANOVA of life expectancy by region, &study_year";
footnote1 'Levene tests the equal-variance assumption; Welch ANOVA does not require it.';
footnote2 'ANOVA and Kruskal-Wallis answer the same question with different assumptions; report both.';
proc glm data=proj.analysis_all;
    class region;
    model life_exp=region;
    means region / hovtest=levene welch;
run;
quit;
footnote;

/* H3. Two-group comparison: high-income economies against the rest.
   The t test answers a narrower, more reportable question than the seven-way
   omnibus tests above, and its confidence interval is what the report quotes. */
data work.income_two;
    set proj.analysis_all;
    where not missing(life_exp) and not missing(income_group);
    length income_two $20;
    if income_group='High income' then income_two='High income';
    else income_two='Not high income';
run;
title "H3: mean life expectancy, high income vs the rest, &study_year";
footnote 'Two-sample t test with the Satterthwaite (unequal variance) row preferred when Levene is significant.';
proc ttest data=work.income_two;
    class income_two;
    var life_exp;
run;
footnote;

/* H4. How strong is the income association on both scales? Pearson for the
   linear fit, Spearman for the rank association, which is insensitive to the
   curvature visible at low income. */
title "H4: correlation between income and life expectancy, &study_year";
footnote 'Spearman uses ranks and does not assume linearity in levels; compare it with Pearson on ln(GDP).';
proc corr data=proj.analysis_all pearson spearman;
    var life_exp log_gdp;
run;
footnote;

/* H5. Group summary table, exported for the report and for the chart below. */
proc means data=proj.analysis_all noprint qntldef=5;
    class region / missing;
    types region;
    var life_exp;
    output out=work.region_summary n=n_economies mean=mean_life
        std=sd_life stderr=se_life min=min_life median=median_life max=max_life
        lclm=lclm_mean uclm=uclm_mean;
run;
data proj.region_summary;
    length region $100;
    set work.region_summary;
    where _type_=1;
    region=coalescec(region,'Unknown region');
    label region='World Bank region (download snapshot)'
          n_economies='Observed N' mean_life='Mean life expectancy (years)'
          sd_life='Sample standard deviation' se_life='Standard error of the mean'
          min_life='Minimum' median_life='Median' max_life='Maximum'
          lclm_mean='95% lower confidence limit of the mean'
          uclm_mean='95% upper confidence limit of the mean';
    format mean_life sd_life se_life min_life median_life max_life
           lclm_mean uclm_mean 8.2;
run;
%assert_rows(proj.region_summary,7,Region summary rows);
%export_csv(proj.region_summary,region_summary);

title "Mean life expectancy with 95% confidence limits by region, &study_year";
proc print data=proj.region_summary noobs label;
    var region n_economies mean_life lclm_mean uclm_mean;
run;
title;

/* H6. Third chart type: a bar chart with confidence limits. The box plot in
   section 30 shows the distribution; this shows the precision of each mean,
   which is what H2 and H3 test. The chart is drawn from the raw economy-level
   data, not from the summary table: LIMITSTAT=CLM needs the observations to
   compute a standard error, one row per region would give a degenerate interval. */
ods graphics / reset=index imagename='07_life_by_region_mean_clm'
    imagefmt=png width=9in height=6in;
title "Mean life expectancy by region with 95% confidence limits (&study_year)";
footnote 'Whiskers are 95% confidence limits of the mean, not ±1.5 IQR; small regions have wide whiskers.';
proc sgplot data=proj.analysis_all;
    vbar region / response=life_exp stat=mean limitstat=clm alpha=0.05 datalabel;
    xaxis label='World Bank region (download snapshot)' fitpolicy=rotate;
    yaxis label='Mean life expectancy at birth (years)' grid;
run;
footnote;
title;
