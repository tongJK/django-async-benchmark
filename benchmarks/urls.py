from django.urls import path

from benchmarks.views_async import (
    cpu_bound_async,
    db_bound_async,
    io_bound_async,
    mixed_async,
)
from benchmarks.views_bridge import (
    bridge_async_to_sync_view,
    bridge_mixed_view,
    bridge_sync_to_async_view,
    bridge_thread_sensitive_view,
)
from benchmarks.views_health import health
from benchmarks.views_mock import mock_delay_async, mock_delay_sync
from benchmarks.views_results import results_clear, results_list, results_summary
from benchmarks.views_sync import (
    cpu_bound_sync,
    db_bound_sync,
    io_bound_sync,
    mixed_sync,
)

app_name = "benchmarks"

urlpatterns = [
    # Health
    path("health/", health, name="health"),
    # Mock server (local delay simulation)
    path("mock/delay/", mock_delay_async, name="mock-delay"),
    path("mock/delay/sync/", mock_delay_sync, name="mock-delay-sync"),
    # Sync endpoints
    path("sync/io-bound/", io_bound_sync, name="sync-io-bound"),
    path("sync/db-bound/", db_bound_sync, name="sync-db-bound"),
    path("sync/mixed/", mixed_sync, name="sync-mixed"),
    path("sync/cpu-bound/", cpu_bound_sync, name="sync-cpu-bound"),
    # Async endpoints
    path("async/io-bound/", io_bound_async, name="async-io-bound"),
    path("async/db-bound/", db_bound_async, name="async-db-bound"),
    path("async/mixed/", mixed_async, name="async-mixed"),
    path("async/cpu-bound/", cpu_bound_async, name="async-cpu-bound"),
    # Bridge endpoints (sync_to_async / async_to_sync patterns)
    path("bridge/sync-to-async/", bridge_sync_to_async_view, name="bridge-sync-to-async"),
    path("bridge/async-to-sync/", bridge_async_to_sync_view, name="bridge-async-to-sync"),
    path("bridge/mixed/", bridge_mixed_view, name="bridge-mixed"),
    path("bridge/sync-to-async-sensitive/", bridge_thread_sensitive_view, name="bridge-thread-sensitive"),
    # Results
    path("results/", results_list, name="results-list"),
    path("results/summary/", results_summary, name="results-summary"),
    path("results/clear/", results_clear, name="results-clear"),
]
