# ⚡ Django Async Convention (Expert Level)

> Decision framework for sync vs async in Django 5.1+.
> Based on real benchmarks from the django-async-benchmark POC.
> Apply these rules when writing or reviewing Django views, services,
> and ORM code.

## The Decision Matrix

**Before writing any view or service, ask: "What does this endpoint do?"**

| Workload | Use Sync | Use Async | Why |
|---|---|---|---|
| Single DB query | ✅ | ❌ | No concurrency benefit, async adds overhead |
| Multiple independent DB queries | ❌ | ✅ | `asyncio.gather()` runs them concurrently |
| External API calls (1+) | ❌ | ✅ | I/O wait is where async shines (~5x faster for 5 calls) |
| DB + external APIs mixed | ❌ | ✅ | Overlap I/O wait with DB queries |
| CPU-heavy computation | ✅ | ❌ | Async doesn't parallelize CPU work, same thread |
| Simple CRUD (create/read/update/delete) | ✅ | ❌ | Overhead not worth it for single operations |
| File uploads/downloads | ❌ | ✅ | I/O-bound, benefits from non-blocking |
| WebSocket / streaming | ❌ | ✅ | Requires ASGI, async is mandatory |

**Rule of thumb**: If the view does **one thing sequentially**, keep it sync.
If it does **multiple independent I/O operations**, make it async.

## Async Views

### When to use `async def` views
```python
# ✅ Good — multiple independent I/O operations
async def dashboard(request):
    user_data, notifications, feed = await asyncio.gather(
        fetch_user_profile(request.user.id),
        fetch_notifications(request.user.id),
        fetch_activity_feed(request.user.id),
    )
    return JsonResponse({...})

# ❌ Bad — single DB query, async adds overhead for nothing
async def product_detail(request, pk):
    product = await Product.objects.aget(pk=pk)  # just use sync
    return JsonResponse({...})
```

### Async views require ASGI
- Async views only work properly under **ASGI** (uvicorn, daphne).
- Under WSGI (gunicorn), Django wraps async views in `async_to_sync`
  automatically — you lose all benefits and add overhead.
- **Always deploy with uvicorn** if you have async views:
  ```bash
  uvicorn project.asgi:application --workers 4
  ```

## Async ORM (Django 5.1+)

### Lazy vs Evaluation — know which needs `a` prefix

QuerySet methods fall into two categories:

**Lazy (build SQL, don't hit DB)** — NO async version needed:
```python
# These are the same in sync and async — they just build the query
qs = Product.objects.filter(is_active=True)   # no .afilter()!
qs = qs.exclude(stock=0)                      # no .aexclude()!
qs = qs.order_by("-price")                    # no .aorder_by()!
qs = qs.select_related("category")            # no .aselect_related()!
qs = qs.values("name", "price")               # no .avalues()!
qs = qs.annotate(count=Count("reviews"))      # no .aannotate()!
# Nothing has hit the DB yet.
```

**Evaluation (hit DB)** — these need the `a` prefix in async:
```python
# Single object
product = await Product.objects.aget(pk=1)              # .get()
product = await Product.objects.acreate(name="x")       # .create()
await product.asave()                                   # .save()
await product.adelete()                                 # .delete()

# Aggregation
count = await Product.objects.filter(active=True).acount()  # .count()
exists = await Product.objects.filter(pk=1).aexists()       # .exists()
stats = await qs.aaggregate(avg=Avg("price"))               # .aggregate()

# Bulk operations
await Product.objects.abulk_create([...])                # .bulk_create()
await Product.objects.abulk_update([...], ["price"])     # .bulk_update()
await qs.aupdate(is_active=False)                       # .update()
await qs.adelete()                                      # .delete()

# Iteration — use `async for` instead of `for`
async for product in Product.objects.filter(is_active=True):
    process(product)

# List conversion
products = [p async for p in Product.objects.all()[:10]]
```

### Concurrent queries with gather
```python
# ✅ The pattern: lazy chain + async evaluation inside gather
results = await asyncio.gather(
    Product.objects.filter(is_active=True).acount(),
    Category.objects.acount(),
    Product.objects.filter(stock__lt=10).aaggregate(avg=Avg("price")),
    Product.objects.filter(pk=1).aexists(),
)
```

### When async ORM helps vs doesn't
- **Helps**: Multiple independent queries that can run concurrently.
- **Doesn't help**: Single query — async ORM has slight overhead
  vs sync ORM for single operations.
- **Doesn't help**: Queries that depend on each other (sequential
  by nature).

## Bridge Patterns (sync ↔ async)

### sync_to_async — calling sync code from async views

**Use case**: Migrating to async views but service layer is still sync.

```python
from asgiref.sync import sync_to_async

# ⚠️ CRITICAL: Use thread_sensitive=False for thread-safe code
# Django DEFAULTS to thread_sensitive=True, which serializes
# all calls to the main thread — killing concurrency.

# ❌ Bad — thread_sensitive=True (default) serializes everything
wrapped = sync_to_async(my_sync_function)  # silently slow

# ✅ Good — thread_sensitive=False allows parallel execution
wrapped = sync_to_async(my_sync_function, thread_sensitive=False)

# ✅ Good — concurrent sync calls via thread pool
async def my_async_view(request):
    result_a, result_b = await asyncio.gather(
        sync_to_async(query_a, thread_sensitive=False)(),
        sync_to_async(query_b, thread_sensitive=False)(),
    )
```

**When to use `thread_sensitive=True`** (the default):
- Code that uses thread-local storage
- Code that calls C extensions that aren't thread-safe
- Django's admin, sessions, or auth internals (rare in views)

**When to use `thread_sensitive=False`**:
- Django ORM queries (thread-safe)
- Most Python standard library code
- Your own service functions (unless they use thread-locals)

### async_to_sync — calling async code from sync views

**Use case**: Want concurrent HTTP calls but view is still sync.

```python
from asgiref.sync import async_to_sync

# Sync view that benefits from async HTTP concurrency
def my_sync_view(request):
    # async_to_sync creates an event loop internally
    results = async_to_sync(fetch_multiple_apis)()
    return JsonResponse({"results": results})

async def fetch_multiple_apis():
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(
            client.get("https://api-a.example.com/data"),
            client.get("https://api-b.example.com/data"),
        )
```

This is the **quick win** for teams not ready to go full async —
you get concurrent I/O without changing your view signatures.

### Mixed bridge — the migration pattern

**Use case**: Async view + sync ORM (bridged) + async HTTP (native).

```python
async def mixed_view(request):
    # ORM through bridge, HTTP stays native async
    # Both run concurrently via gather()
    db_result, api_result = await asyncio.gather(
        sync_to_async(get_products, thread_sensitive=False)(),
        fetch_external_api(),  # native async
    )
    return JsonResponse({...})
```

## HTTP Clients

### Always use httpx (not requests) in async code
```python
# Sync context — both work, httpx preferred for consistency
import httpx
response = httpx.get("https://api.example.com/data", timeout=10.0)

# Async context — httpx only (requests is sync-only)
async with httpx.AsyncClient(timeout=10.0) as client:
    responses = await asyncio.gather(
        client.get("https://api-a.example.com/data"),
        client.get("https://api-b.example.com/data"),
    )
```

### Always handle errors on external calls
```python
# ❌ Bad — one timeout kills everything
results = await asyncio.gather(*[client.get(url) for url in urls])

# ✅ Good — individual error handling
async def safe_fetch(client: httpx.AsyncClient, url: str) -> dict:
    try:
        resp = await client.get(url, timeout=httpx.Timeout(10.0))
        return {"url": url, "status": resp.status_code}
    except httpx.TimeoutException:
        return {"url": url, "error": "timeout"}
    except httpx.HTTPError as e:
        return {"url": url, "error": str(e)}

results = await asyncio.gather(*[safe_fetch(client, url) for url in urls])
```

## Common Mistakes

### 1. Async view with sequential awaits
```python
# ❌ Bad — sequential, no benefit over sync
async def bad_view(request):
    users = await User.objects.filter(active=True).acount()
    orders = await Order.objects.filter(status="pending").acount()
    products = await Product.objects.acount()
    return JsonResponse({...})

# ✅ Good — concurrent
async def good_view(request):
    users, orders, products = await asyncio.gather(
        User.objects.filter(active=True).acount(),
        Order.objects.filter(status="pending").acount(),
        Product.objects.acount(),
    )
    return JsonResponse({...})
```

### 2. CPU-bound work in async view
```python
# ❌ Bad — blocks the event loop, starves other requests
async def bad_view(request):
    result = heavy_computation()  # blocks entire event loop
    return JsonResponse({"result": result})

# ✅ Good — offload to thread pool
async def good_view(request):
    result = await sync_to_async(
        heavy_computation, thread_sensitive=False
    )()
    return JsonResponse({"result": result})

# ✅ Better — use sync view, async doesn't help with CPU
def best_view(request):
    result = heavy_computation()
    return JsonResponse({"result": result})
```

### 3. Forgetting thread_sensitive=False
```python
# ❌ Silently slow — all calls serialized to main thread
tasks = [sync_to_async(query)() for query in queries]
await asyncio.gather(*tasks)  # runs one at a time!

# ✅ Actually concurrent
tasks = [
    sync_to_async(query, thread_sensitive=False)()
    for query in queries
]
await asyncio.gather(*tasks)  # runs in parallel
```

### 4. Mixing sync ORM calls in async views without bridge
```python
# ❌ Bad — SynchronousOnlyOperation error in Django 4.1+
async def bad_view(request):
    products = list(Product.objects.all())  # raises error

# ✅ Good — use async ORM
async def good_view(request):
    products = [p async for p in Product.objects.all()]

# ✅ Good — use sync_to_async bridge
async def also_good_view(request):
    products = await sync_to_async(
        lambda: list(Product.objects.all()),
        thread_sensitive=False,
    )()
```

## Server Configuration

### ASGI (async) — uvicorn
```bash
# Development
uvicorn project.asgi:application --reload --port 8000

# Production
uvicorn project.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

### WSGI (sync) — gunicorn
```bash
# Production
gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### When to use which
- **ASGI**: You have async views, WebSockets, or streaming responses.
- **WSGI**: All views are sync, no async code anywhere.
- **Don't mix**: If you deploy on WSGI, async views get wrapped in
  `async_to_sync` automatically — overhead with zero benefit.

## Database Driver

### Use psycopg3 (not psycopg2) for async
```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # psycopg3 is the default driver in Django 5.1+
        # It supports native async connections.
        # psycopg2 is sync-only — async ORM falls back to
        # sync_to_async wrapper, adding overhead.
    }
}
```

- `psycopg[binary]>=3.2` in your dependencies.
- SQLite does NOT support async connections at all.

## Benchmark Reference

Expected results from the django-async-benchmark POC:

| Scenario | Sync | Async | Speedup |
|---|---|---|---|
| I/O Bound (5 API calls) | ~5000ms | ~1000ms | **~5x** |
| DB Bound (5 queries) | ~45ms | ~55ms | **~0.8x (sync wins locally)** |
| Mixed (APIs + DB) | ~5050ms | ~1020ms | **~5x** |
| CPU Bound (hashing) | ~310ms | ~310ms | **1x (no gain)** |
| Bridge: sync_to_async (False) | — | ~25ms | Close to pure async |
| Bridge: sync_to_async (True) | — | ~45ms | Same as sync (serialized!) |
| Bridge: async_to_sync | ~1000ms | — | ~5x vs pure sync I/O |

## Checklist for Code Review

When reviewing Django code, check:

- [ ] Async views use `asyncio.gather()` for concurrent operations
      (not sequential awaits)
- [ ] `sync_to_async` uses `thread_sensitive=False` for ORM code
- [ ] External HTTP calls use `httpx` with timeout and error handling
- [ ] CPU-bound work is NOT in async views (or is offloaded to thread pool)
- [ ] ASGI server is used when async views exist
- [ ] psycopg3 is used (not psycopg2) for async ORM support
- [ ] No bare `list(QuerySet)` inside async views without bridge
