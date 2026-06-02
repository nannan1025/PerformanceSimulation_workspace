# CV32E40P Benchmark-Suite Delay Contribution Summary

## Input Summary

- Root directory: `trace_output/cv32e40p_bottleneck`
- Benchmarks analyzed: `19`
- Timing CSV files: `336`
- Timing rows: `60,410,082`
- Aggregate max observed cycle sum: `74,455,596`
- Total attributed delay cycles: `15,525,997`

## Whole-Suite Category Summary

| Category | Source field | Cycles | Nonzero rows | Max row delay | % attributed | % aggregate max cycle sum |
| --- | --- | --- | --- | --- | --- | --- |
| RAW wait | raw_wait_cycles | 2,421,627 | 1,371,046 | 31 | 15.60% | 3.25% |
| Branch/control-flow redirect | branch_redirect_cycles | 9,855,062 | 5,274,191 | 32 | 63.47% | 13.24% |
| Divider delay | divider_delay_cycles | 3,184,996 | 146,746 | 31 | 20.51% | 4.28% |
| Multiplier delay | multiplier_delay_cycles | 64,312 | 16,078 | 4 | 0.41% | 0.09% |
| Memory-port structural wait | memory_port_wait_cycles | 0 | 0 | 0 | 0.00% | 0.00% |

## Per-Benchmark Summary

| Benchmark | Timing files | Rows | Max cycle | Attributed cycles | Dominant category | RAW | Divider | Branch | Multiplier | Memory-port |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aha-mont64 | 25 | 4,534,817 | 5,314,729 | 781,635 | Branch/control-flow redirect | 1,793 | 0 | 715,530 | 64,312 | 0 |
| crc32 | 23 | 4,183,376 | 5,055,408 | 872,063 | Branch/control-flow redirect | 98 | 0 | 871,965 | 0 | 0 |
| cubic | 38 | 6,854,333 | 8,228,174 | 1,400,752 | Branch/control-flow redirect | 53,079 | 467,040 | 880,633 | 0 | 0 |
| edn | 19 | 3,447,366 | 4,132,665 | 685,531 | Branch/control-flow redirect | 3,519 | 0 | 682,012 | 0 | 0 |
| huffbench | 13 | 2,302,258 | 2,964,878 | 663,689 | Branch/control-flow redirect | 43,366 | 0 | 620,323 | 0 | 0 |
| matmult-int | 20 | 3,602,152 | 4,377,331 | 775,611 | Branch/control-flow redirect | 502 | 16,800 | 758,309 | 0 | 0 |
| minver | 14 | 2,509,246 | 3,617,747 | 1,110,197 | Divider delay | 5,096 | 639,360 | 465,741 | 0 | 0 |
| nbody | 18 | 3,177,393 | 3,803,671 | 626,312 | Branch/control-flow redirect | 902 | 145,728 | 479,682 | 0 | 0 |
| nettle-aes | 24 | 4,406,553 | 4,628,796 | 360,334 | RAW wait | 121,781 | 121,680 | 116,873 | 0 | 0 |
| nettle-sha256 | 22 | 3,965,640 | 3,994,834 | 29,225 | Branch/control-flow redirect | 2,475 | 0 | 26,750 | 0 | 0 |
| nsichneu | 13 | 2,241,955 | 3,619,366 | 1,562,090 | Branch/control-flow redirect | 768,256 | 0 | 793,834 | 0 | 0 |
| picojpeg | 20 | 3,595,305 | 4,225,636 | 632,652 | Branch/control-flow redirect | 8,095 | 0 | 624,557 | 0 | 0 |
| qrduino | 16 | 2,822,182 | 3,489,493 | 683,993 | Branch/control-flow redirect | 108,953 | 0 | 575,040 | 0 | 0 |
| sglib-combined | 13 | 2,344,372 | 3,312,142 | 1,190,991 | Branch/control-flow redirect | 268,473 | 243,600 | 678,918 | 0 | 0 |
| slre | 13 | 2,376,079 | 2,953,480 | 582,270 | Branch/control-flow redirect | 71,926 | 0 | 510,344 | 0 | 0 |
| st | 22 | 3,969,153 | 4,946,586 | 977,464 | Branch/control-flow redirect | 9,550 | 438,360 | 529,554 | 0 | 0 |
| statemate | 12 | 2,098,097 | 2,323,288 | 252,718 | Branch/control-flow redirect | 37,429 | 0 | 215,289 | 0 | 0 |
| ud | 5 | 923,462 | 2,036,105 | 1,962,544 | Divider delay | 910,567 | 938,530 | 113,447 | 0 | 0 |
| wikisort | 6 | 1,056,343 | 1,431,267 | 375,926 | Branch/control-flow redirect | 5,767 | 173,898 | 196,261 | 0 | 0 |

## Ranking Tables

### Top 5 Benchmarks By Total Attributed Delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | ud | 1,962,544 | 923,462 | 2,036,105 |
| 2 | nsichneu | 1,562,090 | 2,241,955 | 3,619,366 |
| 3 | cubic | 1,400,752 | 6,854,333 | 8,228,174 |
| 4 | sglib-combined | 1,190,991 | 2,344,372 | 3,312,142 |
| 5 | minver | 1,110,197 | 2,509,246 | 3,617,747 |

### Top 5 Benchmarks By RAW wait

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | ud | 910,567 | 923,462 | 2,036,105 |
| 2 | nsichneu | 768,256 | 2,241,955 | 3,619,366 |
| 3 | sglib-combined | 268,473 | 2,344,372 | 3,312,142 |
| 4 | nettle-aes | 121,781 | 4,406,553 | 4,628,796 |
| 5 | qrduino | 108,953 | 2,822,182 | 3,489,493 |

### Top 5 Benchmarks By Branch/control-flow redirect

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | cubic | 880,633 | 6,854,333 | 8,228,174 |
| 2 | crc32 | 871,965 | 4,183,376 | 5,055,408 |
| 3 | nsichneu | 793,834 | 2,241,955 | 3,619,366 |
| 4 | matmult-int | 758,309 | 3,602,152 | 4,377,331 |
| 5 | aha-mont64 | 715,530 | 4,534,817 | 5,314,729 |

### Top 5 Benchmarks By Divider delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | ud | 938,530 | 923,462 | 2,036,105 |
| 2 | minver | 639,360 | 2,509,246 | 3,617,747 |
| 3 | cubic | 467,040 | 6,854,333 | 8,228,174 |
| 4 | st | 438,360 | 3,969,153 | 4,946,586 |
| 5 | sglib-combined | 243,600 | 2,344,372 | 3,312,142 |

### Top 5 Benchmarks By Multiplier delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | aha-mont64 | 64,312 | 4,534,817 | 5,314,729 |
| 2 | crc32 | 0 | 4,183,376 | 5,055,408 |
| 3 | cubic | 0 | 6,854,333 | 8,228,174 |
| 4 | edn | 0 | 3,447,366 | 4,132,665 |
| 5 | huffbench | 0 | 2,302,258 | 2,964,878 |

### Top 5 Benchmarks By Memory-port structural wait

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | aha-mont64 | 0 | 4,534,817 | 5,314,729 |
| 2 | crc32 | 0 | 4,183,376 | 5,055,408 |
| 3 | cubic | 0 | 6,854,333 | 8,228,174 |
| 4 | edn | 0 | 3,447,366 | 4,132,665 |
| 5 | huffbench | 0 | 2,302,258 | 2,964,878 |

## Memory-Port Notes

| Benchmark | Memory-port cycles | DPort_R rows | DPort_W rows | Note |
| --- | --- | --- | --- | --- |
| aha-mont64 | 0 | 9,716 | 3,762 | memory rows, zero wait |
| crc32 | 0 | 348,959 | 175,021 | memory rows, zero wait |
| cubic | 0 | 595,065 | 548,756 | memory rows, zero wait |
| edn | 0 | 889,417 | 94,588 | memory rows, zero wait |
| huffbench | 0 | 353,488 | 182,422 | memory rows, zero wait |
| matmult-int | 0 | 793,214 | 406,782 | memory rows, zero wait |
| minver | 0 | 200,250 | 202,944 | memory rows, zero wait |
| nbody | 0 | 139,274 | 119,333 | memory rows, zero wait |
| nettle-aes | 0 | 788,470 | 47,194 | memory rows, zero wait |
| nettle-sha256 | 0 | 379,439 | 151,394 | memory rows, zero wait |
| nsichneu | 0 | 1,226,893 | 4,465 | memory rows, zero wait |
| picojpeg | 0 | 500,299 | 460,128 | memory rows, zero wait |
| qrduino | 0 | 486,488 | 68,560 | memory rows, zero wait |
| sglib-combined | 0 | 550,834 | 264,947 | memory rows, zero wait |
| slre | 0 | 465,775 | 288,867 | memory rows, zero wait |
| st | 0 | 219,325 | 189,060 | memory rows, zero wait |
| statemate | 0 | 334,850 | 548,749 | memory rows, zero wait |
| ud | 0 | 283,175 | 123,481 | memory rows, zero wait |
| wikisort | 0 | 112,916 | 103,416 | memory rows, zero wait |

## Parse Warnings

No malformed numeric fields were observed.

## Interpretation Notes

- These totals are additive instrumentation-field sums, not a de-overlapped CPI stack.
- A single instruction row can contribute to more than one category.
- Per-benchmark totals are independent benchmark summaries; the whole-suite summary adds those independent totals.
- Memory-port cycles are DPort/WB-stage structural wait only, not cache or external memory latency.

