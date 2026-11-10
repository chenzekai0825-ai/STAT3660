/* [M1] Check keys BEFORE any joins. A duplicate stops the pipeline. */
%unique_key(proj.economies,iso3,metadata);
%unique_key(proj.life_input,%str(iso3,year),life);
%unique_key(proj.gdp_input,%str(iso3,year),gdp);
data proj.key_issues;
  length source $12;
  set proj.economies(in=m keep=iso3)
      proj.life_input(in=l keep=iso3 year)
      proj.gdp_input(in=g keep=iso3 year);
  if m then source='metadata'; else if l then source='life'; else source='gdp';
  if missing(iso3) or lengthn(iso3) ne 3 or ((l or g) and year ne &study_year);
run;
%export_csv(proj.key_issues,key_issues);
%assert_rows(proj.key_issues,0,Nonmissing keys and correct year);
proc sort data=proj.life_input out=work.life_sorted; by iso3 year; run;
proc sort data=proj.gdp_input out=work.gdp_sorted; by iso3 year; run;

/* [M2] Full outer match-merge retains unmatched records for inspection.
   BY requires sorting; the asserted unique keys prevent many-to-many merges. */
data proj.indicator_merge;
  merge work.life_sorted(in=l keep=iso3 year period_start life_exp)
        work.gdp_sorted(in=g keep=iso3 year gdp_date gdp_ppp);
  by iso3 year;
  has_life_row=l; has_gdp_row=g;
  if missing(period_start) then period_start=gdp_date;
  date_disagreement=(l and g and period_start ne gdp_date);
run;
%check_step(Indicator merge);
%unique_key(proj.indicator_merge,%str(iso3,year),indicator_merge);
/* With a single study year, the indicator union is also unique on iso3. */
%unique_key(proj.indicator_merge,iso3,indicator_iso3);
proc sort data=proj.economies out=work.meta_sorted; by iso3; run;
data proj.merge_audit;
  length merge_status $32;
  merge work.meta_sorted(in=m) proj.indicator_merge(in=i);
  by iso3;
  has_metadata=m;
  if not i then do;
    year=&study_year; period_start=mdy(1,1,year);
    has_life_row=0; has_gdp_row=0; date_disagreement=0;
  end;
  if not m then merge_status='Indicators without metadata';
  else if not i then merge_status='Metadata only';
  else if has_life_row and has_gdp_row then merge_status='All three matched';
  else merge_status='One indicator row absent';
  format period_start yymmdd10.;
run;
%check_step(Metadata merge);
%export_csv(proj.merge_audit,merge_audit);
data proj.unmatched_rows;
  set proj.merge_audit;
  if merge_status ne 'All three matched';
run;
%export_csv(proj.unmatched_rows,unmatched_rows);
proc freq data=proj.merge_audit noprint;
  tables merge_status / out=proj.merge_status_counts;
run;
%export_csv(proj.merge_status_counts,merge_status_counts);
proc sql noprint;
  select sum(not has_metadata),sum(date_disagreement)
    into :missing_metadata trimmed,:date_disagreements trimmed from proj.merge_audit;
quit;
%assert_equal(Indicator rows lacking metadata,&missing_metadata,0);
%assert_equal(Dates agree across indicators,&date_disagreements,0);
%assert_rows(proj.merge_audit,&expected_metadata_rows,Full merge preserves metadata rows);

/* [M3] Keep every nonaggregate economy. Missing values are never replaced by 0.
   Out-of-domain values are flagged; analysis uses only valid positive GDP.
   REGION comes from the current metadata snapshot, not historical 2023 groups. */
data proj.analysis_all proj.excluded_aggregates;
  set proj.merge_audit;
  length exclusion_reason $100;
  if is_aggregate=1 then output proj.excluded_aggregates;
  else do;
    missing_life=missing(life_exp);
    missing_gdp=missing(gdp_ppp);
    invalid_life=(not missing_life and (life_exp<=0 or life_exp>120));
    invalid_gdp=(not missing_gdp and gdp_ppp<=0);
    complete_case=(not missing_life and not missing_gdp and not invalid_life and not invalid_gdp);
    exclusion_reason='';
    if missing_life then exclusion_reason=catx('; ',exclusion_reason,'Missing life expectancy');
    if missing_gdp then exclusion_reason=catx('; ',exclusion_reason,'Missing GDP');
    if invalid_life then exclusion_reason=catx('; ',exclusion_reason,'Life expectancy out of domain');
    if invalid_gdp then exclusion_reason=catx('; ',exclusion_reason,'GDP nonpositive');
    if complete_case then exclusion_reason='Included';
    if not missing_gdp and not invalid_gdp then log_gdp=log(gdp_ppp);
    if missing(region) then region='Unclassified';
    label year='Reference year' life_exp='Life expectancy at birth (years)'
      gdp_ppp='GDP per capita PPP (constant 2021 international dollars)'
      log_gdp='Natural log of GDP per capita PPP'
      complete_case='Included in regression (1=yes)'
      exclusion_reason='Regression inclusion or exclusion reason'
      period_start='Annual period marker (not collection date)';
    /* Keep numeric precision in exported data; round only in printed tables. */
    format period_start yymmdd10. life_exp best32. gdp_ppp best32. log_gdp best32.;
    output proj.analysis_all;
  end;
run;
%export_csv(proj.excluded_aggregates,excluded_aggregates);
%unique_key(proj.analysis_all,%str(iso3,year),analysis);
%assert_rows(proj.analysis_all,&expected_economies,Eligible economy count);
proc sql noprint;
  select sum(complete_case),sum(missing_life),sum(missing_gdp),sum(invalid_life or invalid_gdp)
    into :n_model trimmed,:n_life_missing trimmed,:n_gdp_missing trimmed,:n_invalid_domain trimmed
    from proj.analysis_all;
quit;
%assert_equal(Complete cases,&n_model,&expected_complete_cases);
%assert_equal(Missing life expectancy,&n_life_missing,&expected_life_missing);
%assert_equal(Missing GDP,&n_gdp_missing,&expected_gdp_missing);
%assert_equal(Out of domain observations,&n_invalid_domain,0);

/* [M4] Reconcile every stage, including exclusions and retained missing values. */
proc sql;
  create table proj.row_counts as
  select '01 Excel metadata' as stage length=40,count(*) as n from proj.economies
  union all select '02 CSV life expectancy',count(*) from proj.life_input
  union all select '03 DAT GDP',count(*) from proj.gdp_input
  union all select '04 Indicator full merge',count(*) from proj.indicator_merge
  union all select '05 Metadata full merge',count(*) from proj.merge_audit
  union all select '06 Excluded aggregates',count(*) from proj.excluded_aggregates
  union all select '07 Retained economies',count(*) from proj.analysis_all
  union all select '08 Complete-case regression',count(*) from proj.analysis_all where complete_case=1;
quit;
%export_csv(proj.row_counts,row_counts);
title 'Merge row reconciliation: World Bank 2023 snapshot';
proc print data=proj.row_counts noobs label; label stage='Pipeline stage' n='Rows'; run;
title 'Unmatched records are retained and classified';
proc print data=proj.merge_status_counts noobs label; run;
title;
