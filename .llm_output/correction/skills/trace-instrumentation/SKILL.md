---
name: trace-instrumentation
description: Add and validate repeatable temporary timing-trace instrumentation to a CorePerfDSL-generated performance backend. Use when a user provides a CorePerfDSL path and wants stage cycles, generated microaction/resource/connector variables, dependency fields, external-model fields, CSV validation, and an insertion history.
---

# Trace Instrumentation

Use this skill only for generated performance backends in a CorePerfDSL workspace.
The first response must ask for the current CorePerfDSL path if it is not already
provided. Do not infer the target core from a filename alone.

## Safety rules

- Never edit a `.corePerfDsl` file.
- Never run the CorePerfDSL generator automatically.
- Resolve the target backend from the `CorePerfModel` declaration in the input DSL.
- Modify only that backend's generated files. Do not touch another core, the
  original ROCKET backend when the target is RC, or unrelated user changes.
- Before editing, inspect `git diff` for every target file. If an existing change
  cannot be explained as instrumentation, stop and report it.
- Use `apply_patch` for source edits. Do not use reset, checkout, or destructive
  cleanup commands.
- If the DSL and generated backend cannot be shown to match, stop before editing.
- Never call a stateful external-model method a second time for tracing.

## Default commands

Unless the user supplies overrides, use:

```bash
cmake --build etiss-perf-sim/etiss/build_dir \
  --target SWEVAL_BACKENDS_LIB SoftwareEval install -j2
```

Then run:

```bash
./scripts/run.sh em:ud.riscv <CORE> \
  -ta=.llm_output/correction/test \
  -tp=.llm_output/correction/test
```

Use `run2.sh` or another command only when the user specifies it or the
workspace clearly requires it. Ask for a command when no safe default applies.

## Required workflow

1. Ask for and normalize the CorePerfDSL path. Compute its SHA256.
2. Parse `CorePerfModel`, stages, instruction groups, microactions, resources,
   connectors, external-model names, and formulas.
3. Locate the matching generated `variants/<Core>` backend and inspect its
   `PerformanceModel`, `Channel`, and `SchedulingFunction` files.
4. Run the bundled inspection/fingerprint scripts before editing.
5. Load `.llm_output/correction/trace_instrumentation_history.json`, if present.
6. Compare DSL metadata with generated symbols and the previous fingerprint.
   Report consistency as `confirmed consistent`, `possibly inconsistent`, or
   `cannot prove consistency`. Stop on a confirmed mismatch.
7. Inventory the current timing header, `getPipelineStream`, `getPrintHeader`,
   channel pointers, existing trace helpers, and current `recordSchedVar` calls.
8. Derive the current schema as the union of the fixed fields and discovered
   stage-prefixed scheduling variables. Preserve historical order. Append new
   fields to the appropriate stage section. Missing per-instruction values are
   printed as the literal `null`.
9. Add or update instrumentation with `apply_patch`. Follow the insertion rules
   below and keep changes limited to the resolved backend.
10. Re-run the static inventory and fingerprint. Verify idempotency: a second
    run must not add duplicate columns or duplicate recording calls.
11. Build the backend, run the benchmark, and validate timing CSV files with
    `scripts/validate_timing_csv.py`.
12. Write the run record to the history JSON and generate a Markdown report only
    after the source edits and validation have been attempted. Record failures
    explicitly; never label a failed run successful.

## Field schema

Keep these fixed names when the corresponding channel/model supports them:

```text
pc,instr,rd,rs1,rs2,imm,rs1_data,rs2_data,
IF,ID,EX,MEM,WB,
used_rs1,used_rs2,used_rd,rd_ready_cycle,
icache_miss,dcache_miss,icache_delay_cycles,dcache_delay_cycles,
sim_misprediction
```

Discover scheduling fields from the actual formula and generated code. Name each
field `<STAGE>_<variable_name>`, for example:

```text
IF_n_PC_Gen
IF_n_uA_PcCorrect
IF_n_ICache
ID_n_uA_OF_A
EX_n_ALU
MEM_n_DCache
WB_n_Reg
```

Use the stage where the variable is consumed, not merely where it is declared.
If one value is consumed by multiple stages, record a stage-specific field for
each use. Do not rename an existing field because a newer DSL uses a different
local name; record the old field as historical and report a rename candidate.

## `recordSchedVar` insertion rules

For every variable participating in a stage formula, record the already computed
value immediately after its definition or assignment:

```cpp
uint64_t n_PC_Gen = ...;
perfModel->recordSchedVar("IF_n_PC_Gen", n_PC_Gen);
```

For `max(...)` formulas, record every candidate and the relevant `prev.<stage>`
value, not only the final stage cycle. For example, a formula containing
`max(n_PC_Gen, n_ICache, prev.ID)` needs `IF_n_PC_Gen`, `IF_n_ICache`, and
`IF_prev_ID`.

For external calls, capture the result once and reuse the local in both timing
and trace code:

```cpp
uint64_t cacheDelay = perfModel->iCacheModel.getDelay();
uint64_t n_ICache = n_Enter + cacheDelay;
perfModel->recordSchedVar("IF_n_ICache", n_ICache);
```

The same rule applies to `getXa`, `getXb`, `getPc_mp`, `getPc_pt`, `getIc_out`,
`getMulReady`, `getDivReady`, and other potentially stateful methods. A safe
read-only getter such as `getMiss()` may be read only when the model documents it
as non-mutating and it is read after the existing stateful operation.

If a value cannot be captured without a second stateful call, emit `null` and
record the limitation in `unsupported_fields`. Do not guess a zero.

## Idempotency and history

Use `.llm_output/correction/trace_instrumentation_history.json` as runtime state.
Each run must record:

- run id, timestamp, core, DSL path and SHA256;
- target backend files and backend fingerprint;
- previous/current schema hash;
- retained, added, removed, and rename-candidate fields;
- field, file, function, anchor, and source for every insertion point;
- external call capture decisions and unsupported fields;
- build, benchmark, and CSV validation commands and statuses;
- generated report path.

On a repeat run, recognize existing header fields and existing recording calls.
Do not append duplicates. A removed field remains in history; do not silently
remove it from the current schema when a rename is plausible.

## Backend edits

If trace infrastructure already exists, extend it in place. If the backend only
has `IF,ID,EX,MEM,WB`, add the minimum generated-backend support needed for:

- fixed ordered schema;
- sparse scheduling-variable storage;
- `null` output;
- channel identity pointers;
- diagnostic state and reset-after-row;
- header and row generation.

Do not copy a different core's timing attribution algorithm. Reuse only generic
trace storage/output patterns and values actually computed by this core.

## Validation and report

Run `scripts/validate_timing_csv.py` against the benchmark output. It must use
Python's `csv` module and check header uniqueness, row length, required fields,
schema order, and representative timing files. The report must include the DSL
and backend consistency result, all modified files, schema diff, insertion points,
external-call safety, build/run results, CSV counts, unsupported fields, and
whether any CorePerfDSL or non-target file was modified.

Read these references when needed:

- [trace_field_policy.md](references/trace_field_policy.md)
- [backend_layout.md](references/backend_layout.md)
