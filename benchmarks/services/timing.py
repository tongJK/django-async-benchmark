import functools
import logging
import time
from dataclasses import dataclass, field

from django.http import JsonResponse

from benchmarks.models import BenchmarkResult

logger = logging.getLogger(__name__)


@dataclass
class TimingContext:
    """Accumulates timing data across a request."""

    db_time_ms: float = 0
    external_io_time_ms: float = 0
    cpu_time_ms: float = 0
    db_query_count: int = 0

    def record_db(self, duration_ms: float, query_count: int = 1) -> None:
        self.db_time_ms += duration_ms
        self.db_query_count += query_count

    def record_io(self, duration_ms: float) -> None:
        self.external_io_time_ms += duration_ms

    def record_cpu(self, duration_ms: float) -> None:
        self.cpu_time_ms += duration_ms


class Timer:
    """Context manager that measures elapsed time in milliseconds."""

    def __init__(self) -> None:
        self.elapsed_ms: float = 0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


def benchmark_timer(scenario: str, mode: str):
    """Decorator that wraps a view, records total duration, and saves BenchmarkResult."""

    def decorator(view_func):
        @functools.wraps(view_func)
        async def async_wrapper(request, *args, **kwargs):
            ctx = TimingContext()
            start = time.perf_counter()
            response = await view_func(request, ctx, *args, **kwargs)
            total_ms = (time.perf_counter() - start) * 1000

            result = await BenchmarkResult.objects.acreate(
                scenario=scenario,
                mode=mode,
                duration_ms=total_ms,
                db_time_ms=ctx.db_time_ms,
                external_io_time_ms=ctx.external_io_time_ms,
                cpu_time_ms=ctx.cpu_time_ms,
                db_query_count=ctx.db_query_count,
            )
            logger.info("Benchmark %s/%s: %.1fms", scenario, mode, total_ms)

            if isinstance(response, JsonResponse):
                return response

            return JsonResponse({
                "scenario": scenario,
                "mode": mode,
                "duration_ms": round(total_ms, 2),
                "db_time_ms": round(ctx.db_time_ms, 2),
                "external_io_time_ms": round(ctx.external_io_time_ms, 2),
                "cpu_time_ms": round(ctx.cpu_time_ms, 2),
                "db_query_count": ctx.db_query_count,
                "benchmark_id": result.pk,
                "data": response,
            })

        @functools.wraps(view_func)
        def sync_wrapper(request, *args, **kwargs):
            ctx = TimingContext()
            start = time.perf_counter()
            response = view_func(request, ctx, *args, **kwargs)
            total_ms = (time.perf_counter() - start) * 1000

            result = BenchmarkResult.objects.create(
                scenario=scenario,
                mode=mode,
                duration_ms=total_ms,
                db_time_ms=ctx.db_time_ms,
                external_io_time_ms=ctx.external_io_time_ms,
                cpu_time_ms=ctx.cpu_time_ms,
                db_query_count=ctx.db_query_count,
            )
            logger.info("Benchmark %s/%s: %.1fms", scenario, mode, total_ms)

            if isinstance(response, JsonResponse):
                return response

            return JsonResponse({
                "scenario": scenario,
                "mode": mode,
                "duration_ms": round(total_ms, 2),
                "db_time_ms": round(ctx.db_time_ms, 2),
                "external_io_time_ms": round(ctx.external_io_time_ms, 2),
                "cpu_time_ms": round(ctx.cpu_time_ms, 2),
                "db_query_count": ctx.db_query_count,
                "benchmark_id": result.pk,
                "data": response,
            })

        if mode == "async":
            return async_wrapper
        return sync_wrapper

    return decorator
