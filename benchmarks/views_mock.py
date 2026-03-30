import asyncio
import time

from django.conf import settings
from django.http import JsonResponse


def mock_delay_sync(request):
    """Simulate an external API with configurable delay (sync)."""
    delay = float(request.GET.get("delay", settings.BENCHMARK_MOCK_DELAY))
    time.sleep(delay)
    return JsonResponse({"mock": True, "delay": delay})


async def mock_delay_async(request):
    """Simulate an external API with configurable delay (async)."""
    delay = float(request.GET.get("delay", settings.BENCHMARK_MOCK_DELAY))
    await asyncio.sleep(delay)
    return JsonResponse({"mock": True, "delay": delay})
