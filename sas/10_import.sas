/* [I1] Excel metadata: one row per World Bank economy/aggregate code. */
proc import datafile="&input_dir/economies.xlsx"
  out=proj.meta_import dbms=xlsx replace;
  sheet='Economies'; getnames=yes;
run;
%check_step(Excel import);
proc contents data=proj.meta_import out=proj.meta_types noprint; run;
%export_csv(proj.meta_types,metadata_import_types);
/* Confirm the inferred workbook type before SET could cause type conversion. */
proc sql noprint;
  select count(*) into :meta_schema_ok trimmed from proj.meta_types
  where (upcase(name) in ('ISO3','COUNTRY_NAME','REGION_ID','REGION','INCOME_GROUP') and type=2)
     or (upcase(name)='IS_AGGREGATE' and type=1);
quit;
%assert_equal(Excel field types,&meta_schema_ok,6);
data proj.economies;
  length iso3 $3 country_name $180 region_id $3 region $100 income_group $60;
  set proj.meta_import;
  iso3=upcase(strip(iso3));
  label iso3='World Bank economy code' country_name='Economy'
        region='Region (download snapshot)' income_group='Income group (download snapshot)';
run;

/* [I2] CSV: explicit lengths prevent guessing from early rows. Blank numeric
   values remain missing. TRUNCOVER stops a short record consuming the next line. */
data proj.life_input;
  length iso3 $3 period_start_raw $10 life_raw $32;
  infile "&input_dir/life_expectancy.csv" dsd dlm=',' firstobs=2
         lrecl=32767 truncover encoding='utf-8';
  input iso3 :$3. year :4. period_start_raw :$10. life_raw :$32.;
  period_start=input(period_start_raw,?? yymmdd10.);
  life_exp=input(life_raw,?? best32.);
  invalid_date=(missing(period_start) or year(period_start) ne year
                or put(period_start,yymmdd10.) ne period_start_raw);
  invalid_value=(not missing(life_raw) and missing(life_exp));
  format period_start yymmdd10. life_exp 8.3;
run;

/* [I3] Fixed width ASCII DAT (44 bytes per record, no header):
   1-3 code; 5-8 year; 10-19 annual period start; 21-44 GDP token.
   NA is the explicit missing sentinel. Pointer input does not guess delimiters. */
data proj.gdp_input;
  length iso3 $3 gdp_date_raw $10 gdp_raw $24;
  infile "&input_dir/gdp_ppp.dat" lrecl=32767 truncover length=record_bytes;
  input @1 iso3 $3. @5 year 4. @10 gdp_date_raw $10. @21 gdp_raw $24.;
  gdp_date=input(gdp_date_raw,?? yymmdd10.);
  if upcase(strip(gdp_raw)) in ('NA','') then gdp_ppp=.;
  else gdp_ppp=input(gdp_raw,?? best32.);
  invalid_date=(missing(gdp_date) or year(gdp_date) ne year
                or put(gdp_date,yymmdd10.) ne gdp_date_raw);
  invalid_value=(upcase(strip(gdp_raw)) not in ('NA','') and missing(gdp_ppp));
  invalid_width=(record_bytes ne 44);
  format gdp_date yymmdd10. gdp_ppp best32.;
run;

/* [I4] Real source descriptions: read with $4096, then compare byte length and
   end-of-string against independently prepared reference fields. short_copy
   intentionally demonstrates loss with $200; it is never used for analysis. */
data proj.notes_import;
  length indicator_id $24 description $4096 expected_suffix $40 short_copy $200;
  infile "&input_dir/indicator_notes.csv" dsd dlm=',' firstobs=2
         lrecl=32767 truncover encoding='utf-8';
  input indicator_id :$24. description :$4096. expected_bytes :8. expected_suffix :$40.;
  actual_bytes=lengthn(description);
  short_copy=description;
  short_bytes=lengthn(short_copy);
  bytes_lost_if_200=actual_bytes-short_bytes;
  length_ok=(actual_bytes=expected_bytes);
  suffix_ok=(substrn(description,max(1,actual_bytes-39))=expected_suffix);
run;
%export_csv(proj.notes_import,long_field_audit);
data proj.parse_issues;
  length input_name $12;
  set proj.life_input(in=l) proj.gdp_input(in=g);
  if l then input_name='CSV'; else input_name='DAT';
  if invalid_date or invalid_value or invalid_width=1;
run;
%export_csv(proj.parse_issues,parse_issues);
proc sql noprint;
  select sum(not length_ok or not suffix_ok), max(actual_bytes)
    into :bad_notes trimmed, :longest_note trimmed from proj.notes_import;
  select sum(invalid_date),sum(invalid_value) into :bad_life_dates trimmed,:bad_life_values trimmed from proj.life_input;
  select sum(invalid_date),sum(invalid_value),sum(invalid_width)
    into :bad_gdp_dates trimmed,:bad_gdp_values trimmed,:bad_widths trimmed from proj.gdp_input;
quit;
%assert_equal(Long field integrity,&bad_notes,0);
%assert_equal(Longest source description bytes,&longest_note,&expected_max_note_bytes);
%assert_equal(CSV date parsing,&bad_life_dates,0);
%assert_equal(CSV numeric parsing,&bad_life_values,0);
%assert_equal(DAT date parsing,&bad_gdp_dates,0);
%assert_equal(DAT numeric parsing,&bad_gdp_values,0);
%assert_equal(DAT fixed record widths,&bad_widths,0);
%assert_rows(proj.economies,&expected_metadata_rows,Excel row count);
%assert_rows(proj.life_input,&expected_life_rows,CSV row count);
%assert_rows(proj.gdp_input,&expected_gdp_rows,DAT row count);

proc contents data=proj.life_input out=proj.life_types noprint; run;
proc contents data=proj.gdp_input out=proj.gdp_types noprint; run;
data proj.input_types; set proj.meta_types proj.life_types proj.gdp_types; run;
%export_csv(proj.input_types,input_types);
data proj.date_audit;
  set proj.life_input(keep=iso3 year period_start_raw period_start invalid_date);
  parsed_year=year(period_start);
  numeric_sas_date=period_start;
  label period_start='Annual period marker (not collection day)' numeric_sas_date='Days since 01JAN1960';
run;
%export_csv(proj.date_audit,date_audit);
title 'Import audit: dates and numeric types, 2023 annual data';
proc print data=proj.date_audit(obs=8) noobs label; run;
title 'Real source notes: full-width read versus intentionally short 200-byte copy';
proc print data=proj.notes_import noobs label;
  var indicator_id expected_bytes actual_bytes short_bytes bytes_lost_if_200 length_ok suffix_ok;
run;
title;
