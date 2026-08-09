#!/bin/bash

set -e

# ========= 所有要跑的 benchmark =========
benches=(
# aha-mont64
# crc32
cubic
# edn
# huffbench
# matmult-int
# ### md5sum
# minver
# nbody
# nettle-aes
# nettle-sha256
# nsichneu
# picojpeg
# ### primecount
# qrduino
# sglib-combined
# slre
# st
# statemate
# ### tarfind
# ud
# wikisort
)

# ========= 固定参数：只把“变量名”换成 $b =========

ARCH=$2  # 或 "CV32E40P"
COUNT_MODE=1
RUN_DIR="/home/yang/program/project/Performance_Estimator_workspace_2/PerformanceEstimator_workspace/tools/TraceAnalyzer/trace_analyzer/run.py"
for b in "${benches[@]}"; do
    echo "=============================="
    echo "Running benchmark: $b"
    echo "=============================="
    # COMP_TRACE="./trace_output/"$1"/${b}/rtl/timing"
    # COMP_TRACE="./trace_output/CVA62_final/${b}/rtl/timing"
    COMP_TRACE="/home/yang/program/project/Core/chipyard/sims/verilator/output/chipyard.harness.TestHarness.RocketConfig/${b}"
    # ISS_TRACE="./trace_output/"$1"/${b}/asm"
    ISS_TRACE="./trace_output/"$1"/rocket_${b}/asm"
    # PIPELINE_TRACE="./trace_output/"$1"/${b}/rtl/timing"
    # PIPELINE_TRACE="./trace_output/CVA62_final/${b}/rtl/timing"
    PIPELINE_TRACE="/home/yang/program/project/Core/chipyard/sims/verilator/output/chipyard.harness.TestHarness.RocketConfig/${b}"

    TIMING_TRACE="./trace_output/"$1"/rocket_${b}/timing"
    OUTPUT_DIR="./trace_output/"$1"/rocket_${b}/"
    COM=(python3 "$RUN_DIR" "$ISS_TRACE" "-comp=$COMP_TRACE" "-o=$OUTPUT_DIR")
    # 用数组构造命令，避免 eval 和引号问题
    CMD=(python3 "$RUN_DIR" "$ISS_TRACE")

    if [[ -n "$TIMING_TRACE" ]]; then
        CMD+=(-time "$TIMING_TRACE")
    fi

    if [[ -n "$PIPELINE_TRACE" ]]; then
        CMD+=(-pipe "$PIPELINE_TRACE")
    fi

    if [[ -n "$ARCH" ]]; then
        CMD+=(-arch "$ARCH")
    fi

    if [[ "$COUNT_MODE" == "1" ]]; then
        CMD+=(-cnt)
    fi

    if [[ -n "$OUTPUT_DIR" ]]; then
        CMD+=(-o "$OUTPUT_DIR")
    fi

    echo "Running:"
    printf ' %q' "${CMD[@]}"
    echo
    mkdir -p "$OUTPUT_DIR"

    # 真正执行
    "${CMD[@]}"
    # "${COM[@]}"

    echo "Done: $b"
    echo
done

echo "All benchmarks finished."
