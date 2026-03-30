import hashlib

from benchmarks.services.timing import Timer, TimingContext


def _heavy_computation(iterations: int = 100_000) -> str:
    """CPU-intensive work: repeated hashing."""
    data = b"benchmark"
    for _ in range(iterations):
        data = hashlib.sha256(data).digest()
    return data.hex()


def compute_sync(ctx: TimingContext) -> dict:
    """Run CPU-bound work. Async won't help here."""
    results = {}
    with Timer() as t:
        results["hash_1"] = _heavy_computation()
        results["hash_2"] = _heavy_computation()
        results["hash_3"] = _heavy_computation()
    ctx.record_cpu(t.elapsed_ms)
    results["iterations_per_task"] = 100_000
    results["total_tasks"] = 3
    return results


async def compute_async(ctx: TimingContext) -> dict:
    """Same CPU-bound work in async — proves async doesn't help with CPU."""
    results = {}
    with Timer() as t:
        # These are CPU-bound, so gather() won't parallelize them.
        # They still run on the same thread, one after another.
        results["hash_1"] = _heavy_computation()
        results["hash_2"] = _heavy_computation()
        results["hash_3"] = _heavy_computation()
    ctx.record_cpu(t.elapsed_ms)
    results["iterations_per_task"] = 100_000
    results["total_tasks"] = 3
    return results
