/* 30_analysis.sas -- Descriptive analysis, extremes, plots and OLS.
   Run through run_all.sas. Input: PROJ.ANALYSIS_ALL; &OUT and &STUDY_YEAR.
   Each economy receives equal weight. Association is not a causal effect.
   Current-download regions describe the metadata snapshot, not a historical
   classification. All missing outcomes remain in the final analysis data.
*/

/* A. Sample accounting: descriptive summaries use variable-wise available
   observations; OLS uses the predeclared complete-case flag only. */
data work.model_sample;
    set proj.analysis_all;
    where complete_case=1;
run;
proc sql;
    create table work.analysis_sample_flow as
    select count(*) as all_economies label='All eligible economies',
           sum(missing(life_exp)) as life_missing label='Missing life expectancy',
           sum(missing(gdp_ppp)) as gdp_missing label='Missing GDP per capita',
           sum(not missing(gdp_ppp) and gdp_ppp<=0) as gdp_nonpositive
               label='Nonpositive observed GDP',
           sum(complete_case=1) as model_n label='OLS complete cases',
           sum(complete_case=0) as excluded_n label='Excluded from OLS'
    from proj.analysis_all;
    create table work.analysis_exclusions as
    select exclusion_reason, count(*) as economies label='Number of economies'
    from proj.analysis_all
    group by exclusion_reason;
quit;
%export_csv(work.analysis_sample_flow,analysis_sample_flow);
%export_csv(work.analysis_exclusions,analysis_exclusions);
title "Analysis sample accounting: &study_year World Bank economies";
proc print data=work.analysis_sample_flow noobs label; run;
title 'Reasons for inclusion or exclusion from the regression';
proc print data=work.analysis_exclusions noobs label; run;

/* B. Analysis 1: unweighted descriptive statistics overall and by region.
   SAS QNTLDEF=5 is specified for reproducible quartiles. N and NMISS are
   reported separately for each variable, not silently restricted to OLS. */
proc means data=proj.analysis_all noprint qntldef=5;
    class region / missing;
    types () region;
    var life_exp gdp_ppp;
    output out=work.descriptive_wide
        n=life_n gdp_n nmiss=life_nmiss gdp_nmiss
        mean=life_mean gdp_mean std=life_sd gdp_sd
        min=life_min gdp_min q1=life_q1 gdp_q1
        median=life_median gdp_median q3=life_q3 gdp_q3
        max=life_max gdp_max;
run;
data work.descriptive_statistics;
    length scope $12 group_name $100 variable $16 unit $40;
    set work.descriptive_wide;
    array nn[2] life_n gdp_n;
    array nm[2] life_nmiss gdp_nmiss;
    array av[2] life_mean gdp_mean;
    array sd[2] life_sd gdp_sd;
    array mn[2] life_min gdp_min;
    array p1[2] life_q1 gdp_q1;
    array md[2] life_median gdp_median;
    array p3[2] life_q3 gdp_q3;
    array mx[2] life_max gdp_max;
    if _type_=0 then do;
        scope='Overall'; group_name='All eligible economies';
    end;
    else do;
        scope='Region'; group_name=coalescec(region,'Unknown region');
    end;
    do variable_index=1 to 2;
        if variable_index=1 then do;
            variable='life_exp'; unit='Years';
        end;
        else do;
            variable='gdp_ppp'; unit='PPP constant 2021 international dollars';
        end;
        n=nn[variable_index]; n_missing=nm[variable_index];
        mean=av[variable_index]; stddev=sd[variable_index];
        minimum=mn[variable_index]; q1=p1[variable_index];
        median=md[variable_index]; q3=p3[variable_index];
        maximum=mx[variable_index];
        output;
    end;
    label scope='Summary level' group_name='Economy group'
          variable='Measure' unit='Measurement unit' n='Observed N'
          n_missing='Missing N' mean='Mean' stddev='Standard deviation'
          minimum='Minimum' q1='25th percentile' median='Median'
          q3='75th percentile' maximum='Maximum';
    keep scope group_name variable unit n n_missing mean stddev
         minimum q1 median q3 maximum;
run;
%export_csv(work.descriptive_statistics,descriptive_statistics);
title "Descriptive statistics: &study_year (each economy equally weighted)";
footnote 'Each measure uses its own nonmissing observations; monetary values are PPP constant 2021 international dollars.';
proc print data=work.descriptive_statistics noobs label;
    var scope group_name variable unit n n_missing mean stddev minimum q1 median q3 maximum;
    format mean stddev minimum q1 median q3 maximum comma14.2;
run;
footnote;

/* C. Exactly four lowest and four highest observed life-expectancy records.
   Ties are resolved by ascending ISO3, a reproducibility rule, not evidence of
   a substantive difference. Separate audits disclose all boundary ties.
   Rankings use all observed life expectancy, regardless of missing GDP. */
data work.life_nonmissing;
    set proj.analysis_all;
    where not missing(life_exp);
run;
proc sort data=work.life_nonmissing out=work.life_ascending;
    by life_exp iso3;
run;
proc sort data=work.life_nonmissing out=work.life_descending;
    by descending life_exp iso3;
run;
data work.extreme_low;
    length extreme $7;
    set work.life_ascending(obs=4);
    extreme='Lowest'; rank=_n_;
run;
data work.extreme_high;
    length extreme $7;
    set work.life_descending(obs=4);
    extreme='Highest'; rank=_n_;
run;
data work.extreme_eight;
    set work.extreme_low work.extreme_high;
    label extreme='End of distribution' rank='Position (ISO3 breaks ties)'
          iso3='Economy code' country_name='Economy' year='Year'
          life_exp='Life expectancy at birth (years)'
          gdp_ppp='GDP per capita (PPP, constant 2021 intl $)';
    keep extreme rank iso3 country_name region year life_exp gdp_ppp;
run;
proc sql;
    create table work.extreme_cutoffs as
    select extreme, life_exp as cutoff
    from work.extreme_eight where rank=4;
    create table work.extreme_cutoff_ties as
    select c.extreme, c.cutoff, a.iso3, a.country_name,
           (not missing(e.iso3)) as selected_in_four
    from work.extreme_cutoffs c
    inner join work.life_nonmissing a on a.life_exp=c.cutoff
    left join work.extreme_eight e on e.extreme=c.extreme and e.iso3=a.iso3
    order by c.extreme, a.iso3;
    create table work.extreme_cutoff_audit as
    select extreme, cutoff label='Fourth-position value (years)',
           count(*) as all_tied label='All economies tied at boundary',
           sum(selected_in_four) as selected_tied label='Boundary ties included',
           count(*)-sum(selected_in_four) as omitted_tied label='Boundary ties omitted'
    from work.extreme_cutoff_ties
    group by extreme, cutoff;
quit;
%export_csv(work.extreme_eight,life_expectancy_extremes);
%export_csv(work.extreme_cutoff_audit,extreme_cutoff_audit);
%export_csv(work.extreme_cutoff_ties,extreme_cutoff_ties);
title "Four lowest and four highest life expectancies: &study_year";
footnote 'Missing life expectancy is excluded. Ties use ascending ISO3; see boundary-tie audit.';
proc print data=work.extreme_eight noobs label;
    var extreme rank iso3 country_name year life_exp gdp_ppp;
    format life_exp 8.3 gdp_ppp comma14.2;
run;
title 'Audit of ties at the fourth selected observation';
proc print data=work.extreme_cutoff_audit noobs label; run;
footnote;

/* D. Two different question-driven visualizations. PNGs are written through
   the ODS LISTING GPATH configured in the main program. */
ods graphics / reset=index imagename='01_income_life_scatter' imagefmt=png width=9in height=6in;
title "Income and life expectancy: &study_year complete cases";
footnote 'Each point is one economy. The line is an unweighted OLS association, not a causal effect.';
proc sgplot data=work.model_sample;
    reg x=log_gdp y=life_exp / nomarkers lineattrs=(color=darkred thickness=2)
        legendlabel='OLS fitted association';
    scatter x=log_gdp y=life_exp / markerattrs=(symbol=circlefilled size=6)
        transparency=0.2 legendlabel='Economies';
    xaxis label='Natural log of GDP per capita (PPP, constant 2021 international $)' grid;
    yaxis label='Life expectancy at birth (years)' grid;
run;
ods graphics / reset=index imagename='02_life_expectancy_by_region' imagefmt=png width=10in height=6in;
title "Life expectancy distribution by region: &study_year";
footnote 'All nonmissing life expectancies. Boxes show Q1, median and Q3; points beyond 1.5 IQR are marked.';
proc sgplot data=work.life_nonmissing;
    hbox life_exp / category=region missing;
    xaxis label='Life expectancy at birth (years)' grid;
    yaxis label='World Bank region (download snapshot)';
run;
footnote;

/* E. Analysis 2: life expectancy = intercept + beta * ln(GDP per capita).
   HCCMETHOD=3 provides HC3 heteroskedasticity-consistent standard errors.
   CLB with HCC requests both conventional and robust confidence limits;
   the ordinary ANOVA table remains conventional.
   The named TEST produces an additional HC3 covariance-based test.
   SPEC tests a joint null about specification, homoskedasticity and error
   independence from regressors. Rejection alone cannot identify the cause.
   No automatic outlier removal and no population weighting are performed. */
proc sql noprint;
    select count(*), std(log_gdp) into :model_n trimmed, :model_log_sd trimmed
    from work.model_sample;
quit;
data _null_;
    if &model_n < 5 or missing(&model_log_sd) or &model_log_sd<=0 then do;
        put 'ERROR: Too few complete cases or no predictor variation for OLS.';
        abort cancel;
    end;
run;
title "OLS association: life expectancy versus log GDP, &study_year (N=&model_n)";
footnote1 'Both conventional and HC3 inference are requested; the separate covariance-based TEST is robust.';
footnote2 'SPEC is a joint specification test. Country-level associations do not establish individual or causal effects.';
ods output NObs=work.reg_nobs
           ANOVA=work.reg_anova
           FitStatistics=work.reg_fit
           ParameterEstimates=work.reg_parameters
           SpecTest=work.reg_spec_test
           TestANOVA=work.reg_slope_test_ordinary
           ACovTestANOVA=work.reg_slope_test_hc3;
proc reg data=work.model_sample plots=none;
    id iso3 country_name;
    model life_exp=log_gdp / clb hcc hccmethod=3 spec;
    income_association: test log_gdp=0;
    output out=work.reg_diagnostics_raw
        p=predicted_life r=residual rstudent=rstudent h=leverage cookd=cooks_d;
run;
quit;
ods output close;
footnote;
%export_csv(work.reg_nobs,regression_sample_size);
%export_csv(work.reg_anova,regression_anova);
%export_csv(work.reg_fit,regression_fit);
%export_csv(work.reg_parameters,regression_parameters);
%export_csv(work.reg_spec_test,regression_specification_test);
%export_csv(work.reg_slope_test_ordinary,regression_slope_test_ordinary);
%export_csv(work.reg_slope_test_hc3,regression_slope_test_hc3);

/* F. Diagnostics identify records for investigation; they are not exclusion
   rules. p=2 counts the intercept and the one income slope. */
data work.reg_diagnostics;
    set work.reg_diagnostics_raw;
    observation_index=_n_;
    model_n=&model_n;
    cooks_threshold=4/model_n;
    leverage_threshold=2*2/model_n;
    flag_cook=(not missing(cooks_d) and cooks_d>cooks_threshold);
    flag_leverage=(not missing(leverage) and leverage>leverage_threshold);
    flag_residual=(not missing(rstudent) and abs(rstudent)>2);
    flag_any=max(flag_cook,flag_leverage,flag_residual);
    label predicted_life='Fitted life expectancy (years)'
          residual='Observed minus fitted life expectancy (years)'
          rstudent='Externally studentized residual'
          leverage='Leverage (unitless)' cooks_d="Cook's D (unitless)"
          flag_cook="Cook's D > 4/N" flag_leverage='Leverage > 2p/N (p=2)'
          flag_residual='Absolute externally studentized residual > 2';
    keep iso3 country_name region year life_exp gdp_ppp log_gdp
         observation_index predicted_life residual rstudent leverage cooks_d
         model_n cooks_threshold leverage_threshold flag_cook flag_leverage
         flag_residual flag_any;
run;
data work.influence_flags;
    set work.reg_diagnostics;
    where flag_any=1;
run;
proc sort data=work.influence_flags;
    by descending cooks_d iso3;
run;
%export_csv(work.reg_diagnostics,regression_diagnostics);
%export_csv(work.influence_flags,regression_influence_flags);
title "Influence and residual flags: &study_year OLS model";
footnote 'Flags prompt examination only. All complete cases remain in the fitted model.';
proc print data=work.influence_flags noobs label;
    var iso3 country_name residual rstudent leverage cooks_d flag_cook flag_leverage flag_residual;
    format residual rstudent leverage cooks_d 10.4;
run;
footnote;
ods graphics / reset=index imagename='03_residuals_vs_fitted' imagefmt=png width=9in height=6in;
title "OLS diagnostic: residuals versus fitted life expectancy (&study_year)";
proc sgplot data=work.reg_diagnostics;
    scatter x=predicted_life y=residual;
    refline 0 / axis=y lineattrs=(pattern=shortdash color=gray);
    xaxis label='Fitted life expectancy (years)' grid;
    yaxis label='Residual: observed minus fitted (years)' grid;
run;
ods graphics / reset=index imagename='04_residual_normal_qq' imagefmt=png width=8in height=6in;
title "OLS diagnostic: normal Q-Q plot of residuals (&study_year)";
proc univariate data=work.reg_diagnostics noprint;
    var residual;
    qqplot residual / normal(mu=est sigma=est);
run;
ods graphics / reset=index imagename='05_cooks_distance' imagefmt=png width=9in height=6in;
title "OLS diagnostic: Cook's distance (&study_year)";
proc sgplot data=work.reg_diagnostics;
    needle x=observation_index y=cooks_d;
    refline %sysevalf(4/&model_n) / axis=y lineattrs=(pattern=shortdash color=red)
        label='4/N screening threshold';
    xaxis label='Economy observation index (see diagnostics CSV)';
    yaxis label="Cook's D (unitless)" grid;
run;
ods graphics / reset=index imagename='06_leverage_studentized_residual' imagefmt=png width=9in height=6in;
title "OLS diagnostic: leverage and studentized residuals (&study_year)";
proc sgplot data=work.reg_diagnostics;
    scatter x=leverage y=rstudent;
    refline -2 2 / axis=y lineattrs=(pattern=shortdash color=gray);
    refline %sysevalf(4/&model_n) / axis=x lineattrs=(pattern=shortdash color=red)
        label='2p/N screening threshold';
    xaxis label='Leverage (unitless)' grid;
    yaxis label='Externally studentized residual (unitless)' grid;
run;
title;
footnote;
