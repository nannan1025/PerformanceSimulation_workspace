#!/usr/bin/env bash
#usage:
#./scripts/runbencha_trace.sh core_name compare_core
set -e
. $(dirname "${0}")/../.env
core_name="$1"
compare_core="$2"
arg_upper="${core_name^^}"
benches=(
aha-mont64
crc32
cubic
edn
huffbench
matmult-int
### md5sum
minver
nbody
nettle-aes
nettle-sha256
nsichneu
picojpeg
### primecount
qrduino
sglib-combined
slre
st
statemate
### tarfind
ud
wikisort
)
RTL_RUN_SCRIPT="./scripts/support/rtl_run_helper.py"
BOOTROM_VAR="PSW_TARGETSW_CVA6_BOOTROM"
# BOOTROM_VALUE="$(printenv "$BOOTROM_VAR")"
TARGET_DIR="PSW_TARGETSW_"$arg_upper"_EMBENCH"
TARGET_DIR_VALUE="$(printenv "$TARGET_DIR")"
# 创建 trace_output 目录（如果不存在）
# mkdir -p trace_output


# 1) support rocket

for b in "${benches[@]}"; do
    
    outdir="./trace_output/ROCKET/rocket_${b}"

    mkdir -p "$outdir/asm"
    mkdir -p "$outdir/perf"
    rm -rf "$outdir/asm"/*
    rm -rf "$outdir/perf"/*
    echo "Running $b ..."
    ./scripts/run2.sh "em:${b}.riscv" $core_name -ta="$outdir/asm" -tp="$outdir/perf"
    mkdir -p "$outdir/timing"
    rm -rf "$outdir/timing"/*
    mv "$outdir/perf"/ROCKET_timing*.csv "$outdir/timing"/ 2>/dev/null || true
    echo "Done: $b"
    echo
    for file_i in "$outdir/asm"/*.txt; do
        [ -e "$file_i" ] || continue
        mv "$file_i" "${file_i%.txt}.csv"
    done
done


# 2) support cv32e40p

# for b in "${benches[@]}"; do
    
#     outdir="./trace_output/CV32E40P_CORE/${b}"

#     mkdir -p "$outdir/asm"
#     mkdir -p "$outdir/perf"

#     echo "Running $b ..."
#     ./scripts/run2.sh "em:${b}" CV32E40P_CORE -ta="$outdir/asm" -tp="$outdir/perf"
#     mkdir -p "$outdir/timing"
#     mv "$outdir/perf"/CV32E40P_CORE_timing*.csv "$outdir/timing"/ 2>/dev/null || true
#     echo "Done: $b"
#     echo
#     for file_i in "$outdir/asm"/*.txt; do
#         [ -e "$file_i" ] || continue
#         mv "$file_i" "${file_i%.txt}.csv"
#     done
# done


# 3) support cv32e40p and cva6

# for b in "${benches[@]}"; do
    
#     outdir="./trace_output/"$1"/${b}"
#     mkdir -p "$outdir/asm"
#     mkdir -p "$outdir/perf"
#     rm -rf "$outdir/asm"/*
#     rm -rf "$outdir/perf"/*
#     # mkdir -p "$outdir/rtl"
#     echo "Running $b ..."
#     ./scripts/run2.sh "em:${b}" $1 -ta="$outdir/asm" -tp="$outdir/perf"
#     mkdir -p "$outdir/timing"
#     rm -rf "$outdir/timing"/*
#     mv "$outdir/perf"/"$arg_upper"_timing*.csv "$outdir/timing"/ 2>/dev/null || true
#     echo "Done: $b Performance Simulator and rtl simulation"
#     echo
#     for file_i in "$outdir/asm"/*.txt; do
#         [ -e "$file_i" ] || continue
#         mv "$file_i" "${file_i%.txt}.csv"
#     done
#     # echo "rtl converter"
#     # python /home/yang/program/project/Performance_Estimator_workspace_2/PerformanceEstimator_workspace/tools/TraceAnalyzer/rtl_trace_converter/run.py "$outdir/rtl" -a $compare_core -o "$outdir/rtl"
#     # mkdir -p "$outdir/rtl/timing" "$outdir/rtl/raw"
#     # mv "$outdir/rtl"/instr_*.csv "$outdir/rtl/timing" 2>/dev/null || true
#     # mv "$outdir/rtl"/pipeline_*.csv "$outdir/rtl/raw" 2>/dev/null || true
# done
echo "All benchmarks finished."
