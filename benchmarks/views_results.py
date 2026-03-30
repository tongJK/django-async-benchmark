from decimal import Decimal

from django.db.models import Avg, Count, Max, Min
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from benchmarks.models import BenchmarkResult


def _to_float(val) -> float:
    if val is None:
        return 0
    if isinstance(val, Decimal):
        return float(val)
    return val


def results_list(request):
    """List recent benchmark results."""
    limit = int(request.GET.get("limit", 50))
    scenario = request.GET.get("scenario")

    qs = BenchmarkResult.objects.order_by("-created_at")
    if scenario:
        qs = qs.filter(scenario=scenario)

    results = list(
        qs.values(
            "id", "scenario", "mode", "duration_ms",
            "db_time_ms", "external_io_time_ms", "cpu_time_ms",
            "db_query_count", "created_at",
        )[:limit]
    )
    return JsonResponse({"count": len(results), "results": results})


def results_summary(request):
    """Aggregated comparison: avg, min, max per scenario/mode."""
    summary = (
        BenchmarkResult.objects
        .values("scenario", "mode")
        .annotate(
            avg_duration=Avg("duration_ms"),
            min_duration=Min("duration_ms"),
            max_duration=Max("duration_ms"),
            avg_db_time=Avg("db_time_ms"),
            avg_io_time=Avg("external_io_time_ms"),
            avg_cpu_time=Avg("cpu_time_ms"),
            run_count=Count("id"),
        )
        .order_by("scenario", "mode")
    )

    grouped = {}
    for row in summary:
        scenario = row["scenario"]
        if scenario not in grouped:
            grouped[scenario] = {}
        grouped[scenario][row["mode"]] = {
            k: round(_to_float(v), 2) if isinstance(v, (float, Decimal)) else v
            for k, v in row.items()
            if k not in ("scenario", "mode")
        }

    # Calculate speedup ratios
    for scenario, modes in grouped.items():
        if "sync" in modes and "async" in modes:
            sync_avg = modes["sync"]["avg_duration"]
            async_avg = modes["async"]["avg_duration"]
            if async_avg > 0:
                modes["speedup"] = round(sync_avg / async_avg, 2)

    return JsonResponse({"summary": grouped})


@csrf_exempt
def results_clear(request):
    """Clear all benchmark results."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    count, _ = BenchmarkResult.objects.all().delete()
    return JsonResponse({"deleted": count})
