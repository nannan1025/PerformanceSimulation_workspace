#!/bin/bash
# $1: coreperfdsl $2 coreperfdsl model name(RC)
set -euo pipefail

. $(dirname "${0}")/../.env
# $1: ./llm_output/ROCKET_0429.corePerfDsl
INPUT_FILE="${1:?Error: please provide input CorePerfDSL file as the first argument}"
# RUN_NAME="${2:?Error: please provide runing times as the second argument}"

# FOLDER_A_ROOT="/home/yang/program/project/AIResearch/trace_error_analysis/agent"
# Create a new folder under folder a using the second argument
# RUN_DIR="$FOLDER_A_ROOT/$RUN_NAME"
# mkdir -p "$RUN_DIR"
# Filtered log file
# FILTERED_LOG_MD="$RUN_DIR/log.md"


# Create log folder

LOG_DIR="./trace_output/$2/logs"
mkdir -p "$LOG_DIR"

# Log file name with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/rocket_run_${TIMESTAMP}.log"
# OUTPUR_FILE="trace_output/$2/summary_${TIMESTAMP}.csv"

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
echo "[1/3] Generating simulator..."
./scripts/code_gen.sh "$INPUT_FILE"

# Run benchmark trace
echo "[2/3] Running single benchmark trace..."
./scripts/runbencha_trace_single_rocket_correction.sh $2 $2

# Run trace analyzer
echo "[3/3] Running trace analyzer..."
./scripts/trace_analyzer_single_rocket.sh $2 ROCKET


echo "========================================"
echo "Finished successfully"
echo "End time: $(date)"
echo "========================================"
