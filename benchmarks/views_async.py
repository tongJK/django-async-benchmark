import asyncio

from benchmarks.services.cpu_tasks import compute_async
from benchmarks.services.db_queries import run_queries_async
from benchmarks.services.external import fetch_all_async
from benchmarks.services.timing import TimingContext, benchmark_timer


@benchmark_timer(scenario="io_bound", mode="async")
async def io_bound_async(request, ctx: TimingContext):
    """Call 5 external APIs concurrently."""
    return {"api_results": await fetch_all_async(ctx)}


@benchmark_timer(scenario="db_bound", mode="async")
async def db_bound_async(request, ctx: TimingContext):
    """Run 5 DB queries concurrently."""
    return {"query_results": await run_queries_async(ctx)}


@benchmark_timer(scenario="mixed", mode="async")
async def mixed_async(request, ctx: TimingContext):
    """3 API calls + DB queries, all concurrent."""
    api_results, db_results = await asyncio.gather(
        fetch_all_async(ctx),
        run_queries_async(ctx),
    )
    return {"api_results": api_results, "query_results": db_results}


@benchmark_timer(scenario="cpu_bound", mode="async")
async def cpu_bound_async(request, ctx: TimingContext):
    """CPU-heavy computation — proves async doesn't help here."""
    return {"compute_results": await compute_async(ctx)}
