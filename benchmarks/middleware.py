import time


class TimingMiddleware:
    """Adds X-Request-Duration-Ms header to every response.

    Works with both sync and async views. Useful for quick testing
    without checking the results API:

        curl -i http://localhost:8000/api/v1/async/io-bound/
        # → X-Request-Duration-Ms: 1023.45
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"
        return response
