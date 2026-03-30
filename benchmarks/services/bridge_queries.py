"""Bridge patterns: sync_to_async and async_to_sync wrappers.

These demonstrate the real-world migration patterns Django developers face:
1. sync_to_async — wrap sync ORM code to call from async views
2. async_to_sync — wrap async HTTP client to call from sync views
3. Mixed — async view using sync_to_async for ORM + native async for HTTP
"""

import asyncio

from asgiref.sync import async_to_sync, sync_to_async

from benchmarks.services.db_queries import run_queries_sync
from benchmarks.services.external import fetch_all_async, fetch_all_sync
from benchmarks.services.timing import Timer, TimingContext


# Pattern 1: sync_to_async
# Use case: You have existing sync ORM code but want async views.
# sync_to_async wraps the sync function to run in a thread pool,
# so it doesn't block the event loop.

async def run_queries_via_sync_to_async(ctx: TimingContext) -> dict:
    """Wrap sync ORM queries with sync_to_async(thread_sensitive=False).

    thread_sensitive=False → runs in a NEW thread from the default
    executor (thread pool). Multiple calls can run in parallel.
    """
    wrapped = sync_to_async(run_queries_sync, thread_sensitive=False)

    with Timer() as t:
        results = await wrapped(ctx)
    return results


async def run_queries_via_sync_to_async_sensitive(ctx: TimingContext) -> dict:
    """Wrap sync ORM queries with sync_to_async(thread_sensitive=True).

    thread_sensitive=True (the default!) → runs in the MAIN thread.
    This means multiple calls are serialized — no parallelism.

    This is the footgun: Django defaults to thread_sensitive=True,
    which is safe for thread-unsafe code (like old C extensions)
    but kills concurrency. Most ORM code is thread-safe, so you
    should use thread_sensitive=False for it.

    Compare with:
    - /api/v1/bridge/sync-to-async/          (thread_sensitive=False — parallel)
    - /api/v1/bridge/sync-to-async-sensitive/ (thread_sensitive=True — serialized)
    """
    wrapped = sync_to_async(run_queries_sync, thread_sensitive=True)

    with Timer() as t:
        results = await wrapped(ctx)
    return results


# Pattern 2: async_to_sync
# Use case: You want to use httpx.AsyncClient (or any async lib)
# but your view is still sync. async_to_sync creates a new event loop
# and blocks until the coroutine completes.

def fetch_all_via_async_to_sync(ctx: TimingContext) -> list[dict]:
    """Wrap async HTTP calls with async_to_sync for use in sync views."""
    wrapped = async_to_sync(fetch_all_async)
    with Timer() as t:
        results = wrapped(ctx)
    # Note: This still runs concurrently internally (gather inside
    # fetch_all_async), but the sync view blocks until it's done.
    # Benefit over pure sync: the HTTP calls themselves are concurrent.
    return results


# Pattern 3: Mixed bridge (most common migration pattern)
# Use case: Async view that needs to call sync ORM code AND async HTTP.
# ORM goes through sync_to_async, HTTP stays native async,
# both run concurrently via gather().

async def run_mixed_bridge(ctx: TimingContext) -> dict:
    """Async view calling sync ORM (via bridge) + async HTTP concurrently."""
    wrapped_queries = sync_to_async(run_queries_sync, thread_sensitive=False)

    with Timer() as t:
        db_results, api_results = await asyncio.gather(
            wrapped_queries(ctx),
            fetch_all_async(ctx),
        )

    return {"query_results": db_results, "api_results": api_results}


# Pattern 4: thread_sensitive comparison
# This is the most important footgun to demonstrate.
# Django's sync_to_async defaults to thread_sensitive=True,
# which serializes all calls to the main thread.
# For ORM code (which is thread-safe), you want False.
