/*==============================================================================
  00_environment_check.sas  --  run this ALONE before run_all.sas

  Purpose: answer one question before you invest time in the project —
  does THIS SAS session support everything the project uses?

  How to use
    1. Open a new, empty program tab in SAS Studio.
    2. Paste this whole file and press Run.
    3. Read the log top to bottom. Every test prints a clear title, and at the
       end you get a summary of which capabilities are missing.
    4. Tick the boxes in the table at the bottom of the log.

  This file creates nothing outside its own test folder and does not touch the
  project. It stops at nothing: a failed test prints an error but the rest still
  runs, so you get the full picture in one pass.
  =============================================================================*/

options nodate nonumber linesize=160;

%put NOTE: ==========================================================;
%put NOTE: SAS version      : &sysvlong4;
%put NOTE: session encoding : %sysfunc(getoption(encoding));
%put NOTE: locale           : %sysfunc(getoption(locale));
%put NOTE: ==========================================================;

/* ---------------------------------------------------------------------------
   TEST 1  SAS/STAT: PROC REG  (needed by 30_analysis.sas)
   PASS  -> a parameter table with an intercept and a slope
   FAIL  -> "ERROR: Procedure REG not found" => SAS/STAT is not licensed
   ---------------------------------------------------------------------------*/
title 'TEST 1  PROC REG  (SAS/STAT needed for the OLS model)';
proc reg data=sashelp.class;
    model weight=height;
run;
quit;
title;

/* ---------------------------------------------------------------------------
   TEST 2  SAS/STAT: PROC GLM with HOVTEST=LEVENE and WELCH
           (needed by 35_inference.sas)
   PASS  -> a "Levene's Test" table and a "Welch's ANOVA" table
   FAIL  -> ERROR in the MEANS statement => drop that one line, use only
            the Kruskal-Wallis result and say so in the report
   ---------------------------------------------------------------------------*/
title 'TEST 2  PROC GLM: Levene + Welch  (needed for the region ANOVA)';
proc glm data=sashelp.class;
    class sex;
    model weight=sex;
    means sex / hovtest=levene welch;
run;
quit;
title;

/* ---------------------------------------------------------------------------
   TEST 3  SAS/STAT: PROC NPAR1WAY (Kruskal-Wallis)
   PASS  -> "Kruskal-Wallis Test" table
   FAIL  -> replace the region test with PROC GLM only
   ---------------------------------------------------------------------------*/
title 'TEST 3  PROC NPAR1WAY  (Kruskal-Wallis for the region test)';
proc npar1way data=sashelp.class;
    class sex;
    var weight;
run;
title;

/* ---------------------------------------------------------------------------
   TEST 4  PROC TTEST (two-sample, needed for the income comparison)
   ---------------------------------------------------------------------------*/
title 'TEST 4  PROC TTEST  (two-sample comparison)';
proc ttest data=sashelp.class;
    class sex;
    var weight;
run;
title;

/* ---------------------------------------------------------------------------
   TEST 5  ODS GRAPHICS + VBAR with LIMITSTAT=CLM
           This is the exact construct that draws the confidence-limit bars in
           35_inference.sas, so if the graph appears here it will appear there.

   PASS  -> a bar chart with whiskers appears in Results, and the folder
            /home/<you>/stat3660_test contains a .png file
   FAIL  -> graph appears in Results but no .png file => ODS LISTING GPATH does
            not write images in this session; tell the team before running the
            project (the HTML output still works, only the saved PNG is missing)
   ---------------------------------------------------------------------------*/
%let testout=/home/&sysuserid/stat3660_test;
options dlcreatedir;
libname testlib "&testout";

data _null_;
    file "&testout/write_test.txt";
    put 'If you can read this file, the session can write to this folder.';
run;

ods graphics on / reset=all outputfmt=png width=6in height=4in;
ods listing gpath="&testout";
ods graphics / reset=index imagename='env_check_vbar_clm';

title 'TEST 5  VBAR with 95% confidence limits (ODS Graphics + CLM)';
proc sgplot data=sashelp.class;
    vbar sex / response=weight stat=mean limitstat=clm alpha=0.05 datalabel;
    xaxis label='Group';
    yaxis label='Mean weight' grid;
run;
title;
ods listing close;

%put NOTE: look in &testout for a .png file (TEST 5 evidence);

/* ---------------------------------------------------------------------------
   TEST 6  PROC IMPORT DBMS=XLSX  (needed by 10_import.sas)
           Skipped automatically if the project is not uploaded yet.
   PASS  -> NOTE: TEST 6 PASSED, 296 rows imported
   FAIL  -> "ERROR: DBMS type XLSX not valid" => the Excel engine is missing
   ---------------------------------------------------------------------------*/
%let project_root=/home/&sysuserid/STAT3660;

%if %sysfunc(fileexist("&project_root/data/input/economies.xlsx")) %then %do;
    proc import datafile="&project_root/data/input/economies.xlsx"
                out=work.xlsx_test dbms=xlsx replace;
        sheet='Economies';
        getnames=yes;
    run;
    %let dsid=%sysfunc(open(work.xlsx_test));
    %if &dsid > 0 %then %do;
        %let n_xlsx=%sysfunc(attrn(&dsid,nobs));
        %let rc=%sysfunc(close(&dsid));
        %put NOTE: TEST 6 rows imported from economies.xlsx = &n_xlsx;
        %if &n_xlsx = 296 %then %put NOTE: TEST 6 PASSED (expected 296);
        %else %put WARNING: TEST 6 unexpected row count, expected 296;
    %end;
    %else %put WARNING: TEST 6 the import did not create WORK.XLSX_TEST.;
%end;
%else %do;
    %put NOTE: TEST 6 skipped - economies.xlsx is not at &project_root;
    %put NOTE: upload the project first, then run this test again.;
%end;

/* ---------------------------------------------------------------------------
   Summary printed as a table so it is easy to read in Results
   ---------------------------------------------------------------------------*/
data work.check_summary;
    length test $40 meaning $80;
    infile datalines dlm='|' truncover;
    input test $ meaning $;
    datalines;
TEST 1 PROC REG|OLS model in 30_analysis.sas
TEST 2 GLM Levene + Welch|region ANOVA in 35_inference.sas
TEST 3 NPAR1WAY|Kruskal-Wallis in 35_inference.sas
TEST 4 TTEST|income comparison in 35_inference.sas
TEST 5 SGPLOT + CLM + PNG|all charts, and the saved image files
TEST 6 IMPORT XLSX|Excel input in 10_import.sas
;
run;
title 'Capability checklist: compare with the log above, then tick each PASS';
proc print data=work.check_summary noobs;
run;
title;
%put NOTE: ==========================================================;
%put NOTE: environment check finished. If every test above produced output,;
%put NOTE: you can run run_all.sas in this same session.;
%put NOTE: ==========================================================;
