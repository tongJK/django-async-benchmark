import asyncio
import logging

import httpx
from django.conf import settings

from benchmarks.services.timing import Timer, TimingContext

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(10.0)


def _get_urls() -> list[str]:
    """Return target URLs based on BENCHMARK_IO_MODE setting."""
    if settings.BENCHMARK_IO_MODE == "mock":
        base = f"http://localhost:8000/api/v1/mock/delay/?delay={settings.BENCHMARK_MOCK_DELAY}"
        return [base] * settings.BENCHMARK_MOCK_URL_COUNT
    return settings.BENCHMARK_EXTERNAL_URLS


def _safe_result(url: str, status: int = 0, error: str = "") -> dict:
    return {"url": url, "status": status, "error": error} if error else {"url": url, "status": status}


def fetch_all_sync(ctx: TimingContext) -> list[dict]:
    """Fetch all URLs sequentially (blocking)."""
    urls = _get_urls()
    results = []
    with Timer() as t:
        for url in urls:
            try:
                resp = httpx.get(url, timeout=TIMEOUT)
                results.append(_safe_result(url, resp.status_code))
            except httpx.TimeoutException:
                logger.warning("Timeout fetching %s", url)
                results.append(_safe_result(url, error="timeout"))
            except httpx.HTTPError as e:
                logger.warning("HTTP error fetching %s: %s", url, e)
                results.append(_safe_result(url, error=str(e)))
    ctx.record_io(t.elapsed_ms)
    return results


async def fetch_all_async(ctx: TimingContext) -> list[dict]:
    """Fetch all URLs concurrently."""
    urls = _get_urls()

    async def _fetch_one(client: httpx.AsyncClient, url: str) -> dict:
        try:
            resp = await client.get(url, timeout=TIMEOUT)
            return _safe_result(url, resp.status_code)
        except httpx.TimeoutException:
            logger.warning("Timeout fetching %s", url)
            return _safe_result(url, error="timeout")
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching %s: %s", url, e)
            return _safe_result(url, error=str(e))

    with Timer() as t:
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(*[_fetch_one(client, url) for url in urls])
    ctx.record_io(t.elapsed_ms)
    return list(results)
