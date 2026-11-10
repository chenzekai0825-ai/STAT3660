/* Shared audit and export utilities. Failing assertions stop the submitted job. */
data proj.assertions;
  length check_name $120 actual expected 8 passed 8;
  stop;
run;

%macro export_csv(ds,name);
  proc export data=&ds outfile="&out/&name..csv" dbms=csv replace;
  run;
%mend;

%macro fail(message);
  %put ERROR: PROJECT_FAILED: &message;
  %export_csv(proj.assertions,assertions);
  data _null_;
    file status;
    put "FAILED: &message";
  run;
  ods html5(id=project) close;
  proc printto; run;
  %abort cancel;
%mend;

%macro check_step(stage);
  %if &syserr > 4 or &syscc > 4 %then %do;
    %fail(&stage reported a SAS error. Inspect run_all.log.);
  %end;
%mend;

%macro assert_equal(name,actual,expected);
  data work._assert;
    length check_name $120 actual expected 8 passed 8;
    check_name="&name"; actual=&actual; expected=&expected;
    passed=(not missing(actual) and actual=expected);
  run;
  proc append base=proj.assertions data=work._assert force; run;
  %if %sysevalf(&actual ne &expected,boolean) %then %do;
    %fail(Check &name failed: actual=&actual expected=&expected);
  %end;
%mend;

%macro assert_rows(ds,expected,name);
  %local n;
  proc sql noprint; select count(*) into :n trimmed from &ds; quit;
  %assert_equal(&name,&n,&expected);
%mend;

%macro unique_key(ds,keys,tag);
  /* SQL GROUP BY preserves all duplicate-key evidence; no silent NODUPKEY loss. */
  proc sql;
    create table proj.duplicates_&tag as
    select &keys, count(*) as key_count from &ds
    group by &keys having count(*) > 1;
  quit;
  %export_csv(proj.duplicates_&tag,duplicates_&tag);
  %assert_rows(proj.duplicates_&tag,0,Unique key &tag);
%mend;
