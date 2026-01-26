#!/usr/bin/env bash
#USAGE:
#scripts/trace_analyzer_summary.sh corename
# 输出文件名
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
OUT_FILE="trace_output/"$1"/summary_${timestamp}.csv"

# 写表头（benchmark 名 + 8 个数字）
# 这 8 个数字分别是：
# instructions, cycles_obs, cycles_etiss,
# cpi_obs, cpi_etiss, cpi_cpi1,
# ccerr_etiss, ccerr_cpi1
echo "benchmark,instructions,cycles_obs,cycles_etiss,cpi_obs,cpi_etiss,cpi_cpi1,ccerr_etiss,ccerr_cpi1" > "$OUT_FILE"

# 遍历 report 目录下的所有子目录
for dir in trace_output/"$1"/*; do
    [ -d "$dir" ] || continue

    bench=$(basename "$dir")
    report_file="$dir/performance_report.txt"

    # 没有报告就跳过
    [ -f "$report_file" ] || continue

    # 用 awk 从 performance_report.txt 中抓 8 个数字
    values=$(awk '
function clean(s){
  sub(/.*:/, "", s)       # 去掉冒号前
  sub(/\[.*$/, "", s)     # 去掉 [Error: ...] 以及后面
  gsub(/[[:space:]]+/, "", s)  # 去掉所有空白
  sub(/\]+$/, "", s)      # 去掉末尾一个或多个 ]
  return s
}

 /Number of considered instructions/ { instructions = clean($0) }

 /Total number of clock cycles/ {
   getline; cycles_obs   = clean($0)
   getline; cycles_etiss = clean($0)
 }

 /CPI Values/ {
   getline; cpi_obs   = clean($0)
   getline; cpi_etiss = clean($0)
   getline; cpi_cpi1  = clean($0)
 }

 /CC-Error \(averrage CC-deviation per instruction\)/ {
   getline; ccerr_etiss = clean($0)
   getline; ccerr_cpi1  = clean($0)
 }

 END {
   print instructions "," cycles_obs "," cycles_etiss "," \
         cpi_obs "," cpi_etiss "," cpi_cpi1 "," \
         ccerr_etiss "," ccerr_cpi1
 }'  "$report_file")

    # 写入一行：benchmark名 + 8 个数
    echo "$bench,$values" >> "$OUT_FILE"
done

echo "Done. Results saved to $OUT_FILE"
