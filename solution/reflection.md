# Reflection

**Which fault types were hardest to catch, and why?**

The hardest cases were subtle feature skew and lineage topology faults. A
feature shift can sit close to ordinary training-serving variation, so lowering
the threshold indiscriminately would create expensive false alarms. Lineage was
also easy to under-detect if I checked runtime alone: missing upstream edges and
orphaned outputs can complete at an entirely normal speed. I therefore compare
the observed graph with the pipeline's declared topology as well as checking
runtime. Contract schema/type violations were the clearest signals because the
diff tool reports them explicitly.

**What would you change about your cost/coverage tradeoff, if you had another pass?**

I chose one targeted tool call per event. This gives complete signal coverage
while remaining below the supplied budgets, and avoids redundant calls. With
another pass and more representative clean history, I would add robust rolling
calibration in `ctx.state` per feature view and corpus (median/MAD or quantile bands) for
borderline drift. I would only tighten a static threshold when independent
signals agree; otherwise the score's false-positive penalty makes the current
conservative baseline preferable. I would also cache stable contract and
lineage expectations by identifier if the stream introduced several schemas or
jobs.
