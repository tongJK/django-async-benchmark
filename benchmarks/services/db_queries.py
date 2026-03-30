import asyncio

from django.db.models import Avg, Count, Max, Min, Q, Sum

from benchmarks.models import Category, Product
from benchmarks.services.timing import Timer, TimingContext


def run_queries_sync(ctx: TimingContext) -> dict:
    """Run 5 independent DB queries sequentially."""
    results = {}

    with Timer() as t:
        # Query 1: Active products count
        results["active_count"] = Product.objects.filter(is_active=True).count()

    ctx.record_db(t.elapsed_ms)

    with Timer() as t:
        # Query 2: Price aggregation
        agg = Product.objects.filter(is_active=True).aggregate(
            avg_price=Avg("price"),
            max_price=Max("price"),
            min_price=Min("price"),
        )
        results["price_stats"] = {k: float(v) if v else 0 for k, v in agg.items()}

    ctx.record_db(t.elapsed_ms)

    with Timer() as t:
        # Query 3: Top 10 expensive products
        results["top_expensive"] = list(
            Product.objects.filter(is_active=True)
            .order_by("-price")
            .values("name", "price")[:10]
        )

    ctx.record_db(t.elapsed_ms)

    with Timer() as t:
        # Query 4: Category product counts
        results["category_stats"] = list(
            Category.objects.annotate(count=Count("products"))
            .values("name", "count")
            .order_by("-count")[:10]
        )

    ctx.record_db(t.elapsed_ms)

    with Timer() as t:
        # Query 5: Low stock active products
        results["low_stock"] = list(
            Product.objects.filter(is_active=True, stock__lt=10)
            .values("name", "stock", "category__name")[:10]
        )

    ctx.record_db(t.elapsed_ms)

    return results


async def run_queries_async(ctx: TimingContext) -> dict:
    """Run 5 independent DB queries concurrently using async ORM."""

    async def q_active_count() -> int:
        return await Product.objects.filter(is_active=True).acount()

    async def q_price_stats() -> dict:
        agg = await (
            Product.objects.filter(is_active=True)
            .aaggregate(
                avg_price=Avg("price"),
                max_price=Max("price"),
                min_price=Min("price"),
            )
        )
        return {k: float(v) if v else 0 for k, v in agg.items()}

    async def q_top_expensive() -> list:
        return [
            p async for p in
            Product.objects.filter(is_active=True)
            .order_by("-price")
            .values("name", "price")[:10]
        ]

    async def q_category_stats() -> list:
        return [
            c async for c in
            Category.objects.annotate(count=Count("products"))
            .values("name", "count")
            .order_by("-count")[:10]
        ]

    async def q_low_stock() -> list:
        return [
            p async for p in
            Product.objects.filter(is_active=True, stock__lt=10)
            .values("name", "stock", "category__name")[:10]
        ]

    with Timer() as t:
        (
            active_count,
            price_stats,
            top_expensive,
            category_stats,
            low_stock,
        ) = await asyncio.gather(
            q_active_count(),
            q_price_stats(),
            q_top_expensive(),
            q_category_stats(),
            q_low_stock(),
        )

    ctx.record_db(t.elapsed_ms, query_count=5)

    return {
        "active_count": active_count,
        "price_stats": price_stats,
        "top_expensive": top_expensive,
        "category_stats": category_stats,
        "low_stock": low_stock,
    }
