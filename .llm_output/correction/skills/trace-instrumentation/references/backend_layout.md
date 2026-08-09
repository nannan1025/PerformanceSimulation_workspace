# Backend Layout and Consistency Checks

## Generated backend

The target is normally:

```text
etiss-perf-sim/etiss_plugins/SoftwareEvalLib/libs/backends/variants/<CORE>/
```

Inspect these files when present:

```text
include/<CORE>_PerformanceModel.h
src/<CORE>_PerformanceModel.cpp
include/<CORE>_Channel.h
src/<CORE>_Channel.cpp
src/<CORE>_SchedulingFunction.cpp
```

Do not assume ROCKET and RC are interchangeable. Resolve `<CORE>` from the DSL
`CorePerfModel` declaration and verify the generated symbols before editing.

## Consistency fingerprint

The fingerprint should include:

- DSL SHA256;
- core model name;
- sorted stage names;
- sorted instruction/group names;
- sorted microaction/resource/connector names;
- sorted generated scheduling function names;
- sorted generated `n_*` variables and model-member references.

The fingerprint is a structural warning mechanism, not proof of generation
provenance. If it differs from history, report the difference and stop when the
current formulas cannot be mapped safely.

## Common trace anchors

Look for:

```text
getPipelineStream
getPrintHeader
recordSchedVar
trace_sched_vars
setInstructionInfo
getDelay(
getXa(
getXb(
getPc_mp(
getPc_pt(
getMulReady(
getDivReady(
```

The generated scheduling file is the source of truth for local formula values.
The performance model owns the stable schema and row reset. The channel/monitor
owns instruction identity values.
