Rocket Instruction Cache Model
==============================

1. Cache Structure
------------------
<Cache organization>: 8-way set-associative
<Number of ways>: 8
<Number of sets>: 64
<Cache line size>: 64 bytes
<Total cache capacity>: Derived: 32 KiB

Description:
The instruction cache is an 8-way set-associative VIPT cache.
It has 64 sets and 8 ways.
Each cache line contains 64 bytes. RocketConfig does not enable ITIM or
instruction-cache prefetching.

If the total capacity is derived:
<Derivation>: 8 ways x 64 sets x 64 bytes = 32,768 bytes = 32 KiB.


2. Address Mapping
------------------
<Lookup address>: Virtual fetch PC for SRAM access; translated physical address for tag comparison
<Cache-line offset bits>: Address bits [5:0]
<Set-index bits>: Virtual address bits [11:6], equivalent to physical address bits [11:6] within a 4 KiB page
<Tag bits>: Physical address bits [paddrBits-1:12]; the negotiated paddrBits value is Unknown statically
<Cacheable address range>: PMA/TileLink-manager dependent; exact ranges are Unknown without elaboration

Description:
The instruction cache uses the frontend next-PC value as the stage-0 virtual
lookup address. Tag and data SRAMs are read in parallel. Bits 5 to 0 select the
byte offset within a 64-byte cache line, and bits 11 to 6 select one of 64
sets. The translated physical address above bit 11 forms the tag. Addresses
that differ only in bits 5 to 0 belong to the same cache line.


3. Cache Hit and Miss Behavior
------------------------------
<Valid bit required for hit>: Yes
<Tag match required for hit>: Yes, against the translated physical tag
<Ways checked on lookup>: All 8 ways in the selected set
<Uncacheable access behavior>: Speculative non-cacheable refills are killed; non-speculative misses use the normal Get/refill path with allocation hints disabled

Description:
A cache access is considered a hit when one selected-set way has its valid bit
set and its decoded physical tag matches; all eight ways are checked in
parallel. An access is a miss when a non-killed stage-2 request has no hit.
During an outstanding refill, another miss is replayed rather than issuing a
second refill. Cacheability comes from the frontend TLB/PMA result. A
non-cacheable speculative fetch cannot start a refill, while a non-speculative
fetch can issue the normal line Get with read-allocation and write-allocation
hints deasserted.


4. Cache Timing
---------------
<Hit latency>: 2 cycles
<Miss total latency>: Unknown; variable downstream latency plus an 8-beat refill and a replayed hit
<Additional miss penalty>: Unknown
<Latency type>: variable overall; cache-hit pipeline latency is fixed

Description:
A cache hit takes two cycles from an accepted stage-0 request to the stage-2
response. A miss is detected in stage 2, issues a TileLink line Get when no
other refill is outstanding, receives eight 64-bit data beats, and then
requires the frontend fetch to replay and hit the newly valid line. The
TileLink request wait, first-response latency, beat spacing, and replay timing
are not fixed by this ICache RTL, so neither miss total latency nor the
additional miss penalty can be reduced to one static cycle count.


5. Cache Miss and Refill Behavior
---------------------------------
<Cache line inserted on miss>: Yes
<Cache line becomes valid at>: The accepted final refill data beat, if the cache was not invalidated
<Explicit refill state modeled>: Yes; refill_valid, refill counter, request-fire, per-beat, and refill-done state are modeled
<Refill latency>: Variable; 8 accepted TileLink data beats plus request and downstream response delays

Description:
When an instruction-cache miss occurs, the cache issues one 64-byte TileLink
Get. Data SRAM entries are written on each accepted refill beat. The selected
way is invalid while refill is incomplete; its tag is written and valid bit is
set on the final beat unless an invalidation is pending. While refill is in
progress, hits to unaffected valid lines can proceed between refill data-beat
cycles, but another miss cannot launch a second demand refill and the frontend
must replay it.


6. Cache Replacement Behavior
------------------------------
<Use invalid way before replacement>: No explicit invalid-way-first selection
<Replacement policy>: Pseudo-random selection using a 16-bit LFSR
<Replacement state>: LFSR state advances when the refill request fires

Description:
When a new cache line must be inserted, the refill request selects one of the
eight ways from the LFSR output. The selected configuration has no ITIM ways to
exclude. If some ways are invalid, the implementation does not explicitly
prioritize them; the pseudo-randomly selected way is used.


7. Cache Blocking Behavior
--------------------------
<Blocking cache>: Partially blocking with one outstanding demand miss
<Following fetches blocked by a miss>: Refill data beats block new stage-0 acceptance; unrelated hits may proceed between beats, but following misses cannot start another refill
<Block starts when>: Miss serialization starts when refill_valid is set; request backpressure occurs on each accepted refill data beat
<Block ends when>: Miss serialization ends on the final refill beat; per-beat request backpressure ends after that beat
<Maximum outstanding cache misses>: 1 demand miss

Description:
When an instruction-cache miss request fires, refill_valid prevents any later
miss from launching another burst until refill completion. The request-ready
signal is not held low for the entire refill: it is lowered on each refill
data-beat cycle, while requests can be accepted between beats. Consequently,
following fetches that hit unaffected valid lines may complete during the
outstanding miss, whereas a fetch that misses or targets the invalidated
replacement line is replayed. The final refill beat releases the one-miss
serialization state.


8. Pipeline Interaction
-----------------------
<Cache access starts at>: Frontend/ICache stage 0 when the fetch request fires
<Cache result becomes available at>: ICache stage 2 and then the frontend fetch queue
<Access frequency>: One access per accepted 4-byte fetch packet, not one access per individual instruction
<Pipeline stage affected by cache latency>: Instruction-fetch frontend and its fetch-queue supply to decode

Description:
The instruction cache is accessed during frontend stage 0, with tag and data
SRAM reads initiated in parallel. Physical address translation and tag
comparison occur in stage 1, and the configured two-cycle response is produced
in stage 2. Each request fetches 4 bytes, corresponding to a packet that can
contain two 16-bit compressed instruction slots. Cache misses suppress a valid
stage-2 response, cause frontend replay, and can starve the fetch queue feeding
the instruction buffer and decode pipeline.


9. Interaction with Control-Flow Changes
----------------------------------------
<Cache access after branch redirect>: Starts in the same frontend cycle that the redirect request selects the corrected PC, subject to ICache request readiness
<Branch redirect and cache access can overlap>: Yes, corrected-PC selection and the new stage-0 cache request are combinationally coupled
<Redirected cache miss behavior>: The wrong-path stage-1 request is killed; a miss on the corrected path is detected in stage 2 and then follows the normal single-refill/replay path

Description:
When a branch, jump, exception, or replay redirects instruction fetch, the core
asserts a frontend request carrying the corrected PC. The frontend selects and
aligns that PC for the ICache stage-0 address in the same cycle and kills the
older stage-1 lookup. If the redirected instruction fetch misses, the cache
detects that miss in stage 2 and starts the normal TileLink refill when the
single refill slot is available. The downstream refill latency remains
variable; the RTL does not define a fixed combined branch-recovery-plus-cache-
miss cycle count.


10. Unknown or Insufficient Information
---------------------------------------
List all timing-relevant instruction-cache properties that could not be
determined from the provided input:

- The negotiated physical-address width and therefore the numeric physical-tag width.
- The exact cacheable and uncacheable address ranges after diplomacy/PMA elaboration.
- TileLink arbitration delay, first refill-response latency, and spacing or backpressure between the eight refill data beats.
- A fixed miss total latency and fixed additional miss penalty; both depend on the downstream memory hierarchy at runtime.
- The complete core-side branch-resolution latency before a redirect request reaches the frontend; only the frontend behavior after receiving the redirect is statically established here.
