from benchmarks.services.cpu_tasks import compute_sync
from benchmarks.services.db_queries import run_queries_sync
from benchmarks.services.external import fetch_all_sync
from benchmarks.services.timing import TimingContext, benchmark_timer


@benchmark_timer(scenario="io_bound", mode="sync")
def io_bound_sync(request, ctx: TimingContext):
    """Call 5 external APIs sequentially."""
    return {"api_results": fetch_all_sync(ctx)}


@benchmark_timer(scenario="db_bound", mode="sync")
def db_bound_sync(request, ctx: TimingContext):
    """Run 5 DB queries sequentially."""
    return {"query_results": run_queries_sync(ctx)}


@benchmark_timer(scenario="mixed", mode="sync")
def mixed_sync(request, ctx: TimingContext):
    """3 API calls + DB queries, all sequential."""
    api_results = fetch_all_sync(ctx)
    db_results = run_queries_sync(ctx)
    return {"api_results": api_results, "query_results": db_results}


@benchmark_timer(scenario="cpu_bound", mode="sync")
def cpu_bound_sync(request, ctx: TimingContext):
    """CPU-heavy computation."""
    return {"compute_results": compute_sync(ctx)}
