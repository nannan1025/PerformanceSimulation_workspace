# CVA6 Benchmark-Suite Delay Contribution Summary

## Input Summary

- Root directory: `trace_output/cva6_bottleneck`
- Benchmarks analyzed: `19`
- Timing CSV files: `722`
- Timing rows: `54,813,916`
- Aggregate max observed cycle sum: `74,564,452`
- Total attributed delay cycles: `56,381,495`

## Whole-Suite Category Summary

| Category | Source field | Cycles | Nonzero rows | Max row delay | % attributed | % aggregate max cycle sum |
| --- | --- | --- | --- | --- | --- | --- |
| Divider extra delay | divider_extra_cycles | 1,426,739 | 96,198 | 34 | 2.53% | 1.91% |
| I-cache extra delay | icache_extra_cycles | 143,296 | 35,824 | 4 | 0.25% | 0.19% |
| Frontend cache-block wait | frontend_wait_cycles | 212,086 | 34,031 | 31 | 0.38% | 0.28% |
| Frontend IF-capacity wait | frontend_wait_cycles | 3,705,868 | 2,469,203 | 34 | 6.57% | 4.97% |
| D-cache / memory extra delay | dcache_extra_cycles | 440,370 | 56,966 | 8 | 0.78% | 0.59% |
| Branch redirect delay | branch_redirect_cycles | 12,664,580 | 1,423,464 | 108 | 22.46% | 16.98% |
| RAW wait | raw_wait_cycles | 11,519,665 | 9,140,592 | 18 | 20.43% | 15.45% |
| Clobber model delay | clobber_wait_cycles | 13,294,953 | 7,398,682 | 14 | 23.58% | 17.83% |
| Commit wait | commit_wait_cycles | 2,374,909 | 2,374,909 | 1 | 4.21% | 3.19% |
| EX subpipe wait (ALU) | ex_subpipe_wait_cycles | 9,604,927 | 8,290,544 | 35 | 17.04% | 12.88% |
| EX subpipe wait (MUL) | ex_subpipe_wait_cycles | 290,639 | 66,142 | 35 | 0.52% | 0.39% |
| EX subpipe wait (DIV) | ex_subpipe_wait_cycles | 0 | 0 | 0 | 0.00% | 0.00% |
| EX subpipe wait (DIVU) | ex_subpipe_wait_cycles | 441,876 | 15,456 | 34 | 0.78% | 0.59% |
| EX subpipe wait (LOAD) | ex_subpipe_wait_cycles | 153,688 | 61,459 | 8 | 0.27% | 0.21% |
| EX subpipe wait (STORE) | ex_subpipe_wait_cycles | 107,899 | 107,899 | 1 | 0.19% | 0.14% |

## Per-Benchmark Summary

| Benchmark | Timing files | Rows | Max cycle | Attributed cycles | Dominant category | Divider | I-cache | Frontend cache-block | Frontend IF-capacity | D-cache | Branch redirect | RAW | Clobber | Commit | EX subpipe total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aha-mont64 | 25 | 1,918,426 | 2,639,879 | 626,484 | Branch redirect delay | 0 | 2,604 | 3,783 | 7,192 | 800 | 533,800 | 23,621 | 22,322 | 138 | 32,224 |
| crc32 | 57 | 4,184,058 | 6,106,366 | 8,544,895 | Clobber model delay | 0 | 2,468 | 3,531 | 1,391,882 | 1,544 | 4,977 | 2,264,643 | 3,656,739 | 174,218 | 1,044,893 |
| cubic | 49 | 3,743,102 | 5,243,297 | 3,801,583 | Branch redirect delay | 263,920 | 57,892 | 86,757 | 211,926 | 1,214 | 1,012,376 | 447,555 | 687,842 | 57,906 | 974,195 |
| edn | 45 | 3,367,939 | 3,858,685 | 1,831,877 | EX subpipe wait (ALU) | 0 | 2,916 | 4,240 | 87,723 | 2,888 | 75,804 | 397,032 | 246,476 | 342,496 | 672,302 |
| huffbench | 31 | 2,297,463 | 3,343,836 | 2,258,245 | Branch redirect delay | 0 | 3,136 | 4,591 | 38,304 | 4,466 | 787,534 | 473,357 | 512,464 | 170,074 | 264,319 |
| matmult-int | 58 | 4,334,701 | 4,899,568 | 3,172,852 | EX subpipe wait (ALU) | 6,353 | 2,584 | 3,681 | 12,608 | 8,798 | 166,261 | 375,336 | 378,201 | 385,495 | 1,833,535 |
| minver | 30 | 2,287,078 | 3,476,474 | 3,168,654 | Branch redirect delay | 499,500 | 3,988 | 5,715 | 280,795 | 18,704 | 743,775 | 237,838 | 361,147 | 49,568 | 967,624 |
| nbody | 29 | 2,248,434 | 3,128,559 | 1,797,765 | Branch redirect delay | 118,574 | 4,108 | 5,892 | 37,257 | 1,112 | 702,898 | 188,464 | 304,105 | 28,535 | 406,820 |
| nettle-aes | 68 | 5,333,799 | 5,474,397 | 905,949 | Commit wait | 13,728 | 3,728 | 5,425 | 28,840 | 5,012 | 64,556 | 55,625 | 155,425 | 414,898 | 158,712 |
| nettle-sha256 | 51 | 4,022,440 | 4,125,548 | 1,157,167 | EX subpipe wait (ALU) | 0 | 4,484 | 6,572 | 9,536 | 998 | 80,847 | 57,860 | 141,862 | 233,814 | 621,194 |
| nsichneu | 35 | 2,566,060 | 5,805,312 | 6,627,779 | Branch redirect delay | 0 | 15,404 | 23,799 | 7,382 | 818 | 3,259,352 | 1,969,880 | 1,174,232 | 127 | 176,785 |
| picojpeg | 48 | 3,642,847 | 4,675,013 | 4,362,934 | Clobber model delay | 0 | 7,328 | 10,648 | 420,407 | 1,802 | 325,166 | 1,099,409 | 1,678,742 | 142,044 | 677,388 |
| qrduino | 41 | 3,088,750 | 4,720,914 | 4,862,486 | Clobber model delay | 0 | 12,308 | 18,110 | 204,397 | 1,358 | 1,260,153 | 1,125,385 | 1,348,545 | 42,473 | 849,757 |
| sglib-combined | 32 | 2,394,797 | 3,960,278 | 3,576,132 | Branch redirect delay | 16,586 | 3,380 | 4,812 | 168,150 | 318,816 | 1,220,066 | 1,043,684 | 430,579 | 86,113 | 283,946 |
| slre | 33 | 2,470,357 | 3,445,118 | 1,920,582 | Branch redirect delay | 0 | 3,132 | 4,472 | 4,197 | 61,886 | 829,722 | 423,166 | 243,749 | 59,426 | 290,832 |
| st | 36 | 2,728,276 | 3,868,765 | 3,196,348 | Clobber model delay | 334,880 | 3,568 | 5,125 | 311,878 | 1,460 | 600,396 | 470,530 | 603,125 | 68,399 | 796,987 |
| statemate | 24 | 1,876,459 | 2,347,946 | 1,330,611 | Clobber model delay | 0 | 3,144 | 4,595 | 282,720 | 968 | 106,259 | 252,232 | 548,278 | 53,229 | 79,186 |
| ud | 18 | 1,384,912 | 2,129,817 | 2,194,389 | Branch redirect delay | 45,818 | 3,140 | 4,596 | 76,865 | 1,028 | 702,539 | 482,736 | 634,288 | 13,436 | 229,943 |
| wikisort | 12 | 924,018 | 1,314,680 | 1,044,763 | Branch redirect delay | 127,380 | 3,984 | 5,742 | 123,809 | 6,698 | 188,099 | 131,312 | 166,832 | 52,520 | 238,387 |

## Ranking Tables

### Top 5 Benchmarks By Total Attributed Delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | crc32 | 8,544,895 | 4,184,058 | 6,106,366 |
| 2 | nsichneu | 6,627,779 | 2,566,060 | 5,805,312 |
| 3 | qrduino | 4,862,486 | 3,088,750 | 4,720,914 |
| 4 | picojpeg | 4,362,934 | 3,642,847 | 4,675,013 |
| 5 | cubic | 3,801,583 | 3,743,102 | 5,243,297 |

### Top 5 Benchmarks By Divider extra delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | minver | 499,500 | 2,287,078 | 3,476,474 |
| 2 | st | 334,880 | 2,728,276 | 3,868,765 |
| 3 | cubic | 263,920 | 3,743,102 | 5,243,297 |
| 4 | wikisort | 127,380 | 924,018 | 1,314,680 |
| 5 | nbody | 118,574 | 2,248,434 | 3,128,559 |

### Top 5 Benchmarks By I-cache extra delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | cubic | 57,892 | 3,743,102 | 5,243,297 |
| 2 | nsichneu | 15,404 | 2,566,060 | 5,805,312 |
| 3 | qrduino | 12,308 | 3,088,750 | 4,720,914 |
| 4 | picojpeg | 7,328 | 3,642,847 | 4,675,013 |
| 5 | nettle-sha256 | 4,484 | 4,022,440 | 4,125,548 |

### Top 5 Benchmarks By Frontend cache-block wait

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | cubic | 86,757 | 3,743,102 | 5,243,297 |
| 2 | nsichneu | 23,799 | 2,566,060 | 5,805,312 |
| 3 | qrduino | 18,110 | 3,088,750 | 4,720,914 |
| 4 | picojpeg | 10,648 | 3,642,847 | 4,675,013 |
| 5 | nettle-sha256 | 6,572 | 4,022,440 | 4,125,548 |

### Top 5 Benchmarks By Frontend IF-capacity wait

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | crc32 | 1,391,882 | 4,184,058 | 6,106,366 |
| 2 | picojpeg | 420,407 | 3,642,847 | 4,675,013 |
| 3 | st | 311,878 | 2,728,276 | 3,868,765 |
| 4 | statemate | 282,720 | 1,876,459 | 2,347,946 |
| 5 | minver | 280,795 | 2,287,078 | 3,476,474 |

### Top 5 Benchmarks By D-cache / memory extra delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | sglib-combined | 318,816 | 2,394,797 | 3,960,278 |
| 2 | slre | 61,886 | 2,470,357 | 3,445,118 |
| 3 | minver | 18,704 | 2,287,078 | 3,476,474 |
| 4 | matmult-int | 8,798 | 4,334,701 | 4,899,568 |
| 5 | wikisort | 6,698 | 924,018 | 1,314,680 |

### Top 5 Benchmarks By Branch redirect delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | nsichneu | 3,259,352 | 2,566,060 | 5,805,312 |
| 2 | qrduino | 1,260,153 | 3,088,750 | 4,720,914 |
| 3 | sglib-combined | 1,220,066 | 2,394,797 | 3,960,278 |
| 4 | cubic | 1,012,376 | 3,743,102 | 5,243,297 |
| 5 | slre | 829,722 | 2,470,357 | 3,445,118 |

### Top 5 Benchmarks By RAW wait

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | crc32 | 2,264,643 | 4,184,058 | 6,106,366 |
| 2 | nsichneu | 1,969,880 | 2,566,060 | 5,805,312 |
| 3 | qrduino | 1,125,385 | 3,088,750 | 4,720,914 |
| 4 | picojpeg | 1,099,409 | 3,642,847 | 4,675,013 |
| 5 | sglib-combined | 1,043,684 | 2,394,797 | 3,960,278 |

### Top 5 Benchmarks By Clobber model delay

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | crc32 | 3,656,739 | 4,184,058 | 6,106,366 |
| 2 | picojpeg | 1,678,742 | 3,642,847 | 4,675,013 |
| 3 | qrduino | 1,348,545 | 3,088,750 | 4,720,914 |
| 4 | nsichneu | 1,174,232 | 2,566,060 | 5,805,312 |
| 5 | cubic | 687,842 | 3,743,102 | 5,243,297 |

### Top 5 Benchmarks By Commit wait

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | nettle-aes | 414,898 | 5,333,799 | 5,474,397 |
| 2 | matmult-int | 385,495 | 4,334,701 | 4,899,568 |
| 3 | edn | 342,496 | 3,367,939 | 3,858,685 |
| 4 | nettle-sha256 | 233,814 | 4,022,440 | 4,125,548 |
| 5 | crc32 | 174,218 | 4,184,058 | 6,106,366 |

### Top 5 Benchmarks By EX subpipe wait (ALU)

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | matmult-int | 1,825,050 | 4,334,701 | 4,899,568 |
| 2 | crc32 | 1,044,473 | 4,184,058 | 6,106,366 |
| 3 | cubic | 848,740 | 3,743,102 | 5,243,297 |
| 4 | qrduino | 845,438 | 3,088,750 | 4,720,914 |
| 5 | minver | 697,915 | 2,287,078 | 3,476,474 |

### Top 5 Benchmarks By EX subpipe wait (MUL)

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | st | 103,517 | 2,728,276 | 3,868,765 |
| 2 | cubic | 88,262 | 3,743,102 | 5,243,297 |
| 3 | nbody | 47,618 | 2,248,434 | 3,128,559 |
| 4 | wikisort | 35,198 | 924,018 | 1,314,680 |
| 5 | ud | 14,777 | 1,384,912 | 2,129,817 |

### Top 5 Benchmarks By EX subpipe wait (DIV)

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | aha-mont64 | 0 | 1,918,426 | 2,639,879 |
| 2 | crc32 | 0 | 4,184,058 | 6,106,366 |
| 3 | cubic | 0 | 3,743,102 | 5,243,297 |
| 4 | edn | 0 | 3,367,939 | 3,858,685 |
| 5 | huffbench | 0 | 2,297,463 | 3,343,836 |

### Top 5 Benchmarks By EX subpipe wait (DIVU)

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | minver | 251,415 | 2,287,078 | 3,476,474 |
| 2 | st | 87,828 | 2,728,276 | 3,868,765 |
| 3 | cubic | 36,649 | 3,743,102 | 5,243,297 |
| 4 | nbody | 33,584 | 2,248,434 | 3,128,559 |
| 5 | wikisort | 32,400 | 924,018 | 1,314,680 |

### Top 5 Benchmarks By EX subpipe wait (LOAD)

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | sglib-combined | 70,657 | 2,394,797 | 3,960,278 |
| 2 | ud | 21,344 | 1,384,912 | 2,129,817 |
| 3 | minver | 17,186 | 2,287,078 | 3,476,474 |
| 4 | nettle-aes | 10,946 | 5,333,799 | 5,474,397 |
| 5 | matmult-int | 8,485 | 4,334,701 | 4,899,568 |

### Top 5 Benchmarks By EX subpipe wait (STORE)

| Rank | Benchmark | Cycles | Rows | Max cycle |
| --- | --- | --- | --- | --- |
| 1 | picojpeg | 82,879 | 3,642,847 | 4,675,013 |
| 2 | slre | 8,236 | 2,470,357 | 3,445,118 |
| 3 | st | 7,796 | 2,728,276 | 3,868,765 |
| 4 | sglib-combined | 5,391 | 2,394,797 | 3,960,278 |
| 5 | wikisort | 2,485 | 924,018 | 1,314,680 |

## Frontend Wait Notes

| Benchmark | cacheBlockWait cycles | cacheBlockWait rows | ifCapacityWait cycles | ifCapacityWait rows | pcCorrectWait cycles | Note |
| --- | --- | --- | --- | --- | --- | --- |
| aha-mont64 | 3,783 | 617 | 7,192 | 7,181 | 533,800 | counted as branch redirect, not frontend |
| crc32 | 3,531 | 576 | 1,391,882 | 1,391,107 | 4,977 | counted as branch redirect, not frontend |
| cubic | 86,757 | 13,769 | 211,926 | 29,464 | 1,012,376 | counted as branch redirect, not frontend |
| edn | 4,240 | 693 | 87,723 | 83,810 | 75,804 | counted as branch redirect, not frontend |
| huffbench | 4,591 | 746 | 38,304 | 25,416 | 787,534 | counted as branch redirect, not frontend |
| matmult-int | 3,681 | 601 | 12,608 | 4,111 | 166,261 | counted as branch redirect, not frontend |
| minver | 5,715 | 924 | 280,795 | 15,539 | 743,775 | counted as branch redirect, not frontend |
| nbody | 5,892 | 956 | 37,257 | 6,166 | 702,898 | counted as branch redirect, not frontend |
| nettle-aes | 5,425 | 889 | 28,840 | 21,141 | 64,556 | counted as branch redirect, not frontend |
| nettle-sha256 | 6,572 | 1,081 | 9,536 | 8,563 | 80,847 | counted as branch redirect, not frontend |
| nsichneu | 23,799 | 3,695 | 7,382 | 4,919 | 3,259,352 | counted as branch redirect, not frontend |
| picojpeg | 10,648 | 1,739 | 420,407 | 416,384 | 325,166 | counted as branch redirect, not frontend |
| qrduino | 18,110 | 2,960 | 204,397 | 143,608 | 1,260,153 | counted as branch redirect, not frontend |
| sglib-combined | 4,812 | 784 | 168,150 | 43,418 | 1,220,066 | counted as branch redirect, not frontend |
| slre | 4,472 | 730 | 4,197 | 1,876 | 829,722 | counted as branch redirect, not frontend |
| st | 5,125 | 835 | 311,878 | 24,063 | 600,396 | counted as branch redirect, not frontend |
| statemate | 4,595 | 748 | 282,720 | 176,688 | 106,259 | counted as branch redirect, not frontend |
| ud | 4,596 | 752 | 76,865 | 56,137 | 702,539 | counted as branch redirect, not frontend |
| wikisort | 5,742 | 936 | 123,809 | 9,612 | 188,099 | counted as branch redirect, not frontend |

## EX Subpipe Notes

| Benchmark | EX subpipe total | ALU | MUL | DIV | DIVU | LOAD | STORE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| aha-mont64 | 32,224 | 30,517 | 1,267 | 0 | 0 | 440 | 0 |
| crc32 | 1,044,893 | 1,044,473 | 0 | 0 | 0 | 420 | 0 |
| cubic | 974,195 | 848,740 | 88,262 | 0 | 36,649 | 544 | 0 |
| edn | 672,302 | 669,211 | 0 | 0 | 0 | 3,091 | 0 |
| huffbench | 264,319 | 261,986 | 0 | 0 | 0 | 2,333 | 0 |
| matmult-int | 1,833,535 | 1,825,050 | 0 | 0 | 0 | 8,485 | 0 |
| minver | 967,624 | 697,915 | 0 | 0 | 251,415 | 17,186 | 1,108 |
| nbody | 406,820 | 325,009 | 47,618 | 0 | 33,584 | 609 | 0 |
| nettle-aes | 158,712 | 147,766 | 0 | 0 | 0 | 10,946 | 0 |
| nettle-sha256 | 621,194 | 618,739 | 0 | 0 | 0 | 2,455 | 0 |
| nsichneu | 176,785 | 176,320 | 0 | 0 | 0 | 465 | 0 |
| picojpeg | 677,388 | 590,759 | 0 | 0 | 0 | 3,750 | 82,879 |
| qrduino | 849,757 | 845,438 | 0 | 0 | 0 | 4,317 | 2 |
| sglib-combined | 283,946 | 207,898 | 0 | 0 | 0 | 70,657 | 5,391 |
| slre | 290,832 | 281,728 | 0 | 0 | 0 | 868 | 8,236 |
| st | 796,987 | 597,393 | 103,517 | 0 | 87,828 | 453 | 7,796 |
| statemate | 79,186 | 78,689 | 0 | 0 | 0 | 497 | 0 |
| ud | 229,943 | 193,820 | 14,777 | 0 | 0 | 21,344 | 2 |
| wikisort | 238,387 | 163,476 | 35,198 | 0 | 32,400 | 4,828 | 2,485 |

## Parse Warnings

No malformed numeric fields were observed.

## Interpretation Notes

- These totals are additive instrumentation-field sums, not critical-path analysis and not a de-overlapped CPI stack.
- A single instruction row can contribute to more than one category.
- Per-benchmark totals are independent benchmark summaries; the whole-suite summary adds those independent totals.
- `frontend_wait_type=pcCorrectWait` is not counted as frontend wait because branch redirect is counted through `branch_redirect_cycles`.
- Frontend cache-block and IF-capacity waits are intentionally reported as separate categories.
- EX subpipe wait is split by `ex_subpipe_kind`; rows with `ex_subpipe_kind=none` do not contribute.
- Commit wait uses `commit_wait_cycles` as one total category; this report does not split backpressure and capacity into separate contribution categories.

