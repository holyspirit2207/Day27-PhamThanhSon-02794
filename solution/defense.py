"""
Your defense. Implement register(ctx) and a handler per event type.
See ../README.md for the full interface + toolkit reference, and
../RULES.md before you start.
"""
from api import Verdict


def register(ctx):
    ctx.on("data_batch", check_data_batch)
    ctx.on("contract_checkpoint", check_contract_checkpoint)
    ctx.on("lineage_run", check_lineage_run)
    ctx.on("feature_materialization", check_feature_materialization)
    ctx.on("embedding_batch", check_embedding_batch)


def check_data_batch(payload, ctx):
    result = ctx.tools.batch_profile(payload["batch_id"])
    if "error" in result:
        return Verdict(alert=False, confidence=0.0, reason=result["error"], pillar="checks")
    b = ctx.baseline
    alert = (
        result["row_count"] < b["row_count_min"]
        or result["row_count"] > b["row_count_max"]
        or result["null_rate"]["customer_id"] > b["null_rate_max"]
        or result["mean_amount"] < b["mean_amount_min"]
        or result["mean_amount"] > b["mean_amount_max"]
        or result["staleness_min"] > b["staleness_min_max"]
    )
    return Verdict(alert=alert, reason="batch profile outside baseline" if alert else "", pillar="checks")


def check_contract_checkpoint(payload, ctx):
    result = ctx.tools.contract_diff(payload["contract_id"], payload["checkpoint_batch_id"])
    if "error" in result:
        return Verdict(alert=False, confidence=0.0, reason=result["error"], pillar="contracts")
    alert = bool(result["violations"]) or result["freshness_delay_min"] > ctx.baseline["freshness_delay_max_min"]
    return Verdict(alert=alert, reason="contract violation or freshness SLA breach" if alert else "", pillar="contracts")


def check_lineage_run(payload, ctx):
    result = ctx.tools.lineage_graph_slice(payload["run_id"])
    if "error" in result:
        return Verdict(alert=False, confidence=0.0, reason=result["error"], pillar="lineage")
    # The stg_orders lineage contract has two sources and one declared output.
    # Sets make the comparison insensitive to harmless ordering differences.
    expected_upstream = {"raw.orders", "raw.customers"}
    alert = (
        result["duration_ms"] > ctx.baseline["lineage_duration_ms_max"]
        or set(result["actual_upstream"]) != expected_upstream
        or result["actual_downstream_count"] != len(payload.get("outputs", []))
    )
    return Verdict(alert=alert, reason="lineage topology or runtime anomaly" if alert else "", pillar="lineage")


def check_feature_materialization(payload, ctx):
    result = ctx.tools.feature_drift(payload["feature_view"], payload["batch_id"])
    if "error" in result:
        return Verdict(alert=False, confidence=0.0, reason=result["error"], pillar="ai_infra")
    alert = result["mean_shift_sigma"] > ctx.baseline["feature_mean_shift_sigma_max"]
    return Verdict(alert=alert, reason="training-serving feature skew" if alert else "", pillar="ai_infra")


def check_embedding_batch(payload, ctx):
    result = ctx.tools.embedding_drift(payload["corpus"], payload["chunk_batch_id"])
    if "error" in result:
        return Verdict(alert=False, confidence=0.0, reason=result["error"], pillar="ai_infra")
    alert = (
        result["centroid_shift"] > ctx.baseline["embedding_centroid_shift_max"]
        or result["avg_doc_age_days"] > ctx.baseline["corpus_avg_doc_age_days_max"]
    )
    return Verdict(alert=alert, reason="embedding drift or stale corpus" if alert else "", pillar="ai_infra")
