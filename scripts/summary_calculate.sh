#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 input.csv [output.csv]" >&2
    exit 1
fi

input=$1
output=${2:-$input}
tmp=$(mktemp)

awk -F, -v OFS=, '
NR == 1 {
    for (i = 1; i <= NF; i++) {
        if ($i == "cpi_etiss") cpi_etiss = i
        else if ($i == "cpi_cpi1") cpi_cpi1 = i
        else if ($i == "ccerr_etiss") ccerr_etiss = i
        else if ($i == "ccerr_cpi1") ccerr_cpi1 = i
    }
    if (!cpi_etiss || !cpi_cpi1 || !ccerr_etiss || !ccerr_cpi1) {
        print "Missing required columns" > "/dev/stderr"
        exit 1
    }
    print
    next
}
{
    print
    sum[cpi_etiss] += ($cpi_etiss < 0 ? -$cpi_etiss : $cpi_etiss)
    sum[cpi_cpi1] += ($cpi_cpi1 < 0 ? -$cpi_cpi1 : $cpi_cpi1)
    sum[ccerr_etiss] += ($ccerr_etiss < 0 ? -$ccerr_etiss : $ccerr_etiss)
    sum[ccerr_cpi1] += ($ccerr_cpi1 < 0 ? -$ccerr_cpi1 : $ccerr_cpi1)
    rows++
}
END {
    if (rows == 0) exit
    for (i = 1; i <= NF; i++) out[i] = ""
    out[cpi_etiss] = sum[cpi_etiss] / rows
    out[cpi_cpi1] = sum[cpi_cpi1] / rows
    out[ccerr_etiss] = sum[ccerr_etiss] / rows
    out[ccerr_cpi1] = sum[ccerr_cpi1] / rows

    # Print to terminal
    print "avg cpi_etiss ="out[cpi_etiss] > "/dev/stderr"


    for (i = 1; i <= NF; i++) printf "%s%s", out[i], (i == NF ? ORS : OFS)
}
' "$input" > "$tmp"

mv "$tmp" "$output"
