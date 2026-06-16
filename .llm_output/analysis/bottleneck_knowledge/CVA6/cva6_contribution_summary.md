# CVA6 Trace Bottleneck Contribution Summary

## Input

- Trace directory: `.llm_output/analysis/bottleneck_knowledge/CVA6/test`
- Timing CSV files: `18`
- Timing rows: `1,384,912`
- Max observed pipeline cycle: `2,129,817`
- Total attributed delay cycles: `2,194,389`

## Category Summary

| Category | Source field | Cycles | Nonzero rows | Max row delay | % attributed | % max cycle |
| --- | --- | --- | --- | --- | --- | --- |
| Divider extra delay | divider_extra_cycles | 45,818 | 31,038 | 3 | 2.09% | 2.15% |
| I-cache extra delay | icache_extra_cycles | 3,140 | 785 | 4 | 0.14% | 0.15% |
| Frontend cache-block wait | frontend_wait_cycles | 4,596 | 752 | 10 | 0.21% | 0.22% |
| Frontend IF-capacity wait | frontend_wait_cycles | 76,865 | 56,137 | 6 | 3.50% | 3.61% |
| D-cache / memory extra delay | dcache_extra_cycles | 1,028 | 171 | 8 | 0.05% | 0.05% |
| Branch redirect delay | branch_redirect_cycles | 702,539 | 62,328 | 25 | 32.02% | 32.99% |
| RAW wait | raw_wait_cycles | 482,736 | 340,333 | 10 | 22.00% | 22.67% |
| Clobber model delay | clobber_wait_cycles | 634,288 | 338,562 | 10 | 28.90% | 29.78% |
| Commit wait | commit_wait_cycles | 13,436 | 13,436 | 1 | 0.61% | 0.63% |
| EX subpipe wait (ALU) | ex_subpipe_wait_cycles | 193,820 | 170,178 | 3 | 8.83% | 9.10% |
| EX subpipe wait (MUL) | ex_subpipe_wait_cycles | 14,777 | 5,911 | 4 | 0.67% | 0.69% |
| EX subpipe wait (DIV) | ex_subpipe_wait_cycles | 0 | 0 | 0 | 0.00% | 0.00% |
| EX subpipe wait (DIVU) | ex_subpipe_wait_cycles | 0 | 0 | 0 | 0.00% | 0.00% |
| EX subpipe wait (LOAD) | ex_subpipe_wait_cycles | 21,344 | 20,809 | 7 | 0.97% | 1.00% |
| EX subpipe wait (STORE) | ex_subpipe_wait_cycles | 2 | 2 | 1 | 0.00% | 0.00% |

## Frontend Wait Type Breakdown

| frontend_wait_type | Rows | Cycles | % attributed |
| --- | --- | --- | --- |
| pcCorrectWait | 62,328 | 702,539 | 32.02% |
| ifCapacityWait | 56,137 | 76,865 | 3.50% |
| cacheBlockWait | 752 | 4,596 | 0.21% |
| none | 1,265,695 | 0 | 0.00% |

## EX Subpipe Kind Breakdown

| ex_subpipe_kind | Rows | Cycles | % attributed |
| --- | --- | --- | --- |
| ALU | 170,178 | 193,820 | 8.83% |
| LOAD | 20,809 | 21,344 | 0.97% |
| MUL | 5,911 | 14,777 | 0.67% |
| STORE | 2 | 2 | 0.00% |
| none | 1,188,012 | 0 | 0.00% |

## Top Contributors by Type ID and PC (top 10)

| Category | Top type_id:cycles | Top pc:cycles |
| --- | --- | --- |
| Divider extra delay | 47:45,818 | 2147485688:5,912, 2147485812:4,434, 2147486708:4,434, 2147486736:4,434, 2147484612:2,956, 2147484652:2,956, 2147484688:2,956, 2147484720:2,956, 2147485972:2,956, 2147486768:2,956 |
| I-cache extra delay | 6:772, 60:524, 65:392, 1:188, 34:168, 40:132, 22:96, 23:80, 18:76, 12:76 | 2147484160:8, 2147484192:8, 2147531328:8, 65536:4, 65540:4, 65544:4, 65548:4, 65552:4, 65556:4, 2147483648:4 |
| Frontend cache-block wait | 6:1,109, 65:721, 60:681, 34:276, 1:208, 40:181, 22:133, 9:128, 12:116, 35:115 | 2147529044:18, 2147545052:13, 2147520120:12, 2147484164:12, 2147484196:12, 2147531332:12, 65556:10, 2147489968:7, 2147562096:7, 2147494464:7 |
| Frontend IF-capacity wait | 60:29,586, 23:13,293, 22:5,911, 47:5,908, 42:5,908, 65:4,439, 12:4,431, 6:2,955, 34:2,952, 1:1,476 | 2147485540:4,431, 2147486760:4,431, 2147486788:4,431, 2147484736:2,954, 2147486428:2,954, 2147486460:2,954, 2147485576:2,954, 2147486696:2,954, 2147486708:2,954, 2147486820:2,954 |
| D-cache / memory extra delay | 60:846, 59:86, 55:78, 57:12, 56:6 | 2147493776:60, 2147547264:32, 2147488196:30, 2147488204:30, 2147485596:18, 2147545012:18, 2147545052:18, 2147545080:18, 2147529076:12, 2147494860:12 |
| Branch redirect delay | 60:309,307, 6:110,035, 12:72,401, 65:65,007, 47:62,050, 22:53,240, 18:20,726, 1:8,966, 40:103, 59:99 | 2147485812:62,050, 2147484920:41,390, 2147485680:39,893, 2147484828:39,891, 2147485012:38,422, 2147484752:38,412, 2147485552:32,527, 2147484772:28,097, 2147485904:26,610, 2147485644:25,130 |
| RAW wait | 23:167,028, 42:109,365, 22:73,916, 12:41,380, 60:35,473, 47:28,085, 65:26,646, 35:247, 34:210, 62:147 | 2147485748:13,306, 2147484744:11,833, 2147485612:11,826, 2147484760:11,824, 2147484764:11,824, 2147485616:11,822, 2147485896:8,873, 2147484908:8,873, 2147484780:8,868, 2147484940:8,867 |
| Clobber model delay | 22:189,196, 12:144,819, 42:131,528, 23:102,019, 60:35,467, 47:22,174, 6:4,508, 18:4,458, 25:26, 9:22 | 2147485748:17,740, 2147484908:13,307, 2147484856:13,300, 2147485728:13,299, 2147484744:11,835, 2147485896:11,829, 2147485612:11,826, 2147484760:11,824, 2147484940:11,823, 2147485740:8,868 |
| Commit wait | 34:2,960, 12:2,955, 6:1,538, 41:1,511, 23:1,481, 22:1,480, 18:1,478, 65:13, 40:7, 0:3 | 2147485236:2,955, 2147486296:1,478, 2147486340:1,478, 2147486392:1,477, 2147485556:1,477, 2147485552:1,477, 2147486756:1,477, 2147487004:1,477, 2147547260:15, 2147549732:6 |
| EX subpipe wait (ALU) | 34:53,237, 23:28,076, 6:20,810, 1:19,218, 39:17,733, 12:14,782, 22:13,303, 35:11,824, 18:10,342, 40:4,456 | 2147484748:5,912, 2147484768:5,912, 2147485620:5,911, 2147485696:5,911, 2147485752:4,434, 2147485836:4,434, 2147485816:4,434, 2147484868:4,433, 2147484916:4,433, 2147485040:4,433 |
| EX subpipe wait (MUL) | 42:14,777 | 2147486712:5,912, 2147486740:5,910, 2147486936:1,478, 2147486880:1,477 |
| EX subpipe wait (DIV) | none | none |
| EX subpipe wait (DIVU) | none | none |
| EX subpipe wait (LOAD) | 60:21,314, 55:19, 59:11 | 2147485720:4,433, 2147485868:2,955, 2147484684:1,483, 2147486492:1,483, 2147484644:1,482, 2147486404:1,482, 2147484732:1,478, 2147484736:1,477, 2147486020:1,477, 2147486484:1,477 |
| EX subpipe wait (STORE) | 65:2 | 2147487624:1, 2147487628:1 |

## Formulas

| Category | Formula |
| --- | --- |
| Divider extra delay | sum(divider_extra_cycles) |
| I-cache extra delay | sum(icache_extra_cycles) |
| Frontend cache-block wait | sum(frontend_wait_cycles where frontend_wait_type == "cacheBlockWait") |
| Frontend IF-capacity wait | sum(frontend_wait_cycles where frontend_wait_type == "ifCapacityWait") |
| D-cache / memory extra delay | sum(dcache_extra_cycles) |
| Branch redirect delay | sum(branch_redirect_cycles) |
| RAW wait | sum(raw_wait_cycles) |
| Clobber model delay | sum(clobber_wait_cycles) |
| Commit wait | sum(commit_wait_cycles) |
| EX subpipe wait (ALU) | sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "ALU") |
| EX subpipe wait (MUL) | sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "MUL") |
| EX subpipe wait (DIV) | sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "DIV") |
| EX subpipe wait (DIVU) | sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "DIVU") |
| EX subpipe wait (LOAD) | sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "LOAD") |
| EX subpipe wait (STORE) | sum(ex_subpipe_wait_cycles where ex_subpipe_kind == "STORE") |

## Parse Warnings

No malformed numeric fields were observed.

## Interpretation Notes

- These totals are additive sums of instrumentation fields, not critical-path analysis and not a de-overlapped CPI stack.
- A single instruction row can contribute to more than one category, so category totals can overlap conceptually.
- `frontend_wait_type=pcCorrectWait` is excluded from frontend wait categories because branch redirect is counted through `branch_redirect_cycles`.
- Frontend cache-block and IF-capacity waits are intentionally reported as separate categories.
- EX subpipe wait is split by `ex_subpipe_kind`; rows with `ex_subpipe_kind=none` do not contribute.
- Commit wait uses `commit_wait_cycles` as one total category; this report does not split backpressure and capacity into separate contribution categories.

