/* STAT 3660SEF | 2026 Autumn | World Bank 2023 cross-section
   Edit ONLY project_root below. Upload the entire folder to SAS Studio first.
   Requires Base SAS 9.4, SAS/STAT, ODS Graphics and DBMS=XLSX support.
   Save this program as UTF-8; run the WHOLE program in a fresh SAS session. */
%let project_root=/home/YOUR_USER/stat3660sef-group-project;

%let study_year=2023;
%let input_dir=&project_root/data/input;
%let out=&project_root/results/sas;
options validvarname=v7 mprint mlogic symbolgen nofmterr;
%macro preflight;
  %if not %sysfunc(fileexist(&input_dir/economies.xlsx)) %then %do;
    %put ERROR: Set project_root to the uploaded SAS server folder containing data/input/economies.xlsx.;
    %abort cancel;
  %end;
%mend;
%preflight;
/* Create directories on the SAS server, without shell commands. */
data _null_;
  length p $1024;
  p=dcreate('results',"&project_root");
  p=dcreate('sas',"&project_root/results");
  p=dcreate('datasets',"&out");
run;
libname proj "&out/datasets";
filename status "&out/RUN_STATUS.txt";
data _null_;
  if fexist('status') then rc=fdelete('status');
run;
proc printto log="&out/run_all.log" new; run;
ods _all_ close;
ods listing gpath="&out";
ods html5(id=project) path="&out" file='analysis.html'
  style=htmlblue options(bitmap_mode='inline');
ods graphics on / reset=all outputfmt=png width=9in height=5.5in;
%include "&project_root/sas/00_helpers.sas";
%include "&project_root/sas/snapshot_expectations.sas";
%include "&project_root/sas/10_import.sas";
%check_step(Import);
%include "&project_root/sas/20_merge.sas";
%check_step(Merge);
%include "&project_root/sas/30_analysis.sas";
%check_step(Analysis);

%export_csv(proj.analysis_all,final_analysis);
%export_csv(proj.assertions,assertions);
title 'Pipeline validation checks';
proc print data=proj.assertions noobs label; run;
title;
%check_step(Final exports);
ods html5(id=project) close;
ods listing close;
data _null_;
  file status;
  put 'COMPLETED: SAS pipeline reached the end and all explicit assertions passed.';
  put 'Review run_all.log for WARNING and all model diagnostics before reporting results.';
  put "Study year=&study_year";
  put "SAS version=&sysvlong4";
  completed_at=datetime();
  put 'Completed at ' completed_at datetime20.;
run;
%put NOTE: PROJECT_COMPLETED. Review &out/run_all.log and RUN_STATUS.txt.;
proc printto; run;
ods html5;
