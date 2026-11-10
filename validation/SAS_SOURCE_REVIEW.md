# SAS 源码检查（不等同于执行）

已逐段复核主入口、宏参数、输入格式、变量长度、排序和BY键、完整连接、样本标记、极端值并列规则及ODS导出名称。复核中修复了完成状态日期的PUT语法，并将最终分析数据的寿命格式改为BEST32.，避免导出CSV时只保留三位小数。错误解析明细在断言停止前导出。路径检查在建立日志之前运行，便于发现未修改示例路径的问题。

SAS官方参考：

- [REG MODEL选项及HCC/CLB](https://support.sas.com/documentation/cdl/en/statug/63962/HTML/default/statug_reg_sect013.htm)
- [REG TEST与稳健协方差](https://support.sas.com/documentation/cdl/en/statug/67523/HTML/default/statug_reg_syntax20.htm)
- [REG ODS表名](https://support.sas.com/documentation/cdl/en/statug/63033/HTML/default/statug_reg_sect051.htm)
- [SPEC联合设定检验解释](https://support.sas.com/kb/22/637.html)

没有SAS编译、运行或日志证据；组件授权、XLSX解析、ODS输出和整个流程仍必须在实际SAS Studio环境验证。`tools/check_sas_run.py` 在没有SAS输出时实际返回失败，未将Python结果识别为SAS完成。环境检查记录见 `environment_check.json`。
