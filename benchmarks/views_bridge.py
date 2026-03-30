from benchmarks.services.bridge_queries import (
    fetch_all_via_async_to_sync,
    run_mixed_bridge,
    run_queries_via_sync_to_async,
    run_queries_via_sync_to_async_sensitive,
)
from benchmarks.services.timing import TimingContext, benchmark_timer


@benchmark_timer(scenario="bridge_sync_to_async", mode="async")
async def bridge_sync_to_async_view(request, ctx: TimingContext):
    """Async view calling sync ORM via sync_to_async.

    Real-world scenario: You're migrating to async views but your
    service layer is still sync. sync_to_async runs the sync code
    in a thread pool so it doesn't block the event loop.

    Compare with:
    - /api/v1/sync/db-bound/   (pure sync — baseline)
    - /api/v1/async/db-bound/  (pure async ORM — best case)
    This shows the cost of the bridge overhead.
    """
    return {"query_results": await run_queries_via_sync_to_async(ctx)}


@benchmark_timer(scenario="bridge_async_to_sync", mode="sync")
def bridge_async_to_sync_view(request, ctx: TimingContext):
    """Sync view calling async HTTP client via async_to_sync.

    Real-world scenario: Your views are still sync but you want to
    use an async HTTP library (httpx.AsyncClient) for concurrent
    external calls. async_to_sync creates an event loop internally.

    Compare with:
    - /api/v1/sync/io-bound/   (pure sync httpx — sequential)
    - /api/v1/async/io-bound/  (pure async — best case)
    This shows you get concurrency even from a sync view.
    """
    return {"api_results": fetch_all_via_async_to_sync(ctx)}


@benchmark_timer(scenario="bridge_mixed", mode="async")
async def bridge_mixed_view(request, ctx: TimingContext):
    """Async view: sync ORM via sync_to_async + async HTTP, all concurrent.

    Real-world scenario: You're partially migrated. Your ORM code is
    still sync, but you want to overlap DB queries with external API
    calls. sync_to_async + gather() makes this possible.

    Compare with:
    - /api/v1/sync/mixed/   (pure sync — everything sequential)
    - /api/v1/async/mixed/  (pure async — best case)
    This shows the practical middle-ground during migration.
    """
    return await run_mixed_bridge(ctx)


@benchmark_timer(scenario="bridge_thread_sensitive", mode="async")
async def bridge_thread_sensitive_view(request, ctx: TimingContext):
    """Async view calling sync ORM via sync_to_async(thread_sensitive=True).

    ⚠️ This is the FOOTGUN demo.

    thread_sensitive=True (Django's default!) forces all wrapped calls
    to run on the MAIN thread, one at a time. This kills concurrency.

    thread_sensitive=False lets each call run in its own thread from
    the pool, enabling true parallelism.

    Compare with:
    - /api/v1/bridge/sync-to-async/           (False — parallel, faster)
    - /api/v1/bridge/sync-to-async-sensitive/  (True — serialized, slower)
    The difference shows why you should use thread_sensitive=False
    for thread-safe code like Django ORM.
    """
    return {"query_results": await run_queries_via_sync_to_async_sensitive(ctx)}
