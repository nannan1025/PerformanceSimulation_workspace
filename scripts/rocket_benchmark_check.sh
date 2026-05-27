#!/bin/bash

set -euo pipefail

. $(dirname "${0}")/../.env
# $1: ./llm_output/ROCKET_0429.corePerfDsl
INPUT_FILE="${1:?Error: please provide input CorePerfDSL file as the first argument}"
# RUN_NAME="${2:?Error: please provide runing times as the second argument}"

FOLDER_A_ROOT="/home/yang/program/project/AIResearch/trace_error_analysis/agent"
# Create a new folder under folder a using the second argument
# RUN_DIR="$FOLDER_A_ROOT/$RUN_NAME"
# mkdir -p "$RUN_DIR"
# Filtered log file
# FILTERED_LOG_MD="$RUN_DIR/log.md"


# Create log folder
LOG_DIR="./trace_output/ROCKET/logs"
mkdir -p "$LOG_DIR"

# Log file name with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/rocket_run_${TIMESTAMP}.log"
OUTPUR_FILE="trace_output/ROCKET/summary_${TIMESTAMP}.csv"
# write_filtered_log_md() {
#     local tmp_file
#     tmp_file="$(mktemp)"

#     if [ -f "$LOG_FILE" ]; then
#         perl -pe 's/\e\[[0-9;]*[A-Za-z]//g' "$LOG_FILE" |
#             grep -i -E 'error|failed|exception|missing|mismatch' |
#             grep -v -E 'Could NOT find|Up-to-date|errorInjection|ErrorDefinition|Estimated with CPI-1|Estimated with ETISS|CC-Error' |
#             sed -E 's|^.*error: |error: |' |
#             sort |
#             uniq > "$tmp_file" || true
#     fi

#     if [ -s "$tmp_file" ]; then
#         mv "$tmp_file" "$FILTERED_LOG_MD"
#     else
#         echo "success" > "$FILTERED_LOG_MD"
#         rm -f "$tmp_file"
#     fi
# }

# Always generate log.md when the script exits,
# no matter whether the flow succeeds or fails.
# trap write_filtered_log_md EXIT

# Save all terminal output to log file and still print to terminal
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================"
echo "Start ROCKET simulation flow"
echo "Input file: $INPUT_FILE"
# echo "Run name: $RUN_NAME"
# echo "Run folder: $RUN_DIR"
echo "Full log file: $LOG_FILE"
# echo "Filtered log.md: $FILTERED_LOG_MD"
echo "Start time: $(date)"
echo "========================================"

# Generate simulator
echo "[1/4] Generating simulator..."
./scripts/code_gen.sh "$INPUT_FILE"

# Run benchmark trace
echo "[2/4] Running benchmark trace..."
./scripts/runbencha_trace.sh ROCKET ROCKET

# Run trace analyzer
echo "[3/4] Running trace analyzer..."
./scripts/trace_analyzer_rocket.sh ROCKET ROCKET

# Generate summary
echo "[4/4] Generating trace analyzer summary..."
./scripts/trace_analyzer_summary.sh ROCKET "$OUTPUR_FILE"
cp "$OUTPUR_FILE" "$FOLDER_A_ROOT"

echo "========================================"
echo "Finished successfully"
echo "End time: $(date)"
echo "========================================"
