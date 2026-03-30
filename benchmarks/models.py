from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    product_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["price", "is_active"]),
            models.Index(
                fields=["created_at"],
                condition=models.Q(is_active=True),
                name="idx_active_created_at",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class BenchmarkResult(models.Model):
    class Scenario(models.TextChoices):
        IO_BOUND = "io_bound", "I/O Bound"
        DB_BOUND = "db_bound", "DB Bound"
        MIXED = "mixed", "Mixed"
        CPU_BOUND = "cpu_bound", "CPU Bound"
        BRIDGE_SYNC_TO_ASYNC = "bridge_sync_to_async", "Bridge: sync_to_async"
        BRIDGE_ASYNC_TO_SYNC = "bridge_async_to_sync", "Bridge: async_to_sync"
        BRIDGE_MIXED = "bridge_mixed", "Bridge: Mixed"
        BRIDGE_THREAD_SENSITIVE = "bridge_thread_sensitive", "Bridge: thread_sensitive"

    class Mode(models.TextChoices):
        SYNC = "sync", "Sync"
        ASYNC = "async", "Async"

    scenario = models.CharField(max_length=30, choices=Scenario.choices)
    mode = models.CharField(max_length=10, choices=Mode.choices)
    duration_ms = models.FloatField(help_text="Total request time in ms")
    db_time_ms = models.FloatField(default=0, help_text="Time spent on DB queries")
    external_io_time_ms = models.FloatField(default=0, help_text="Time on external API calls")
    cpu_time_ms = models.FloatField(default=0, help_text="Time on computation")
    db_query_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["scenario", "mode"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.scenario}/{self.mode}: {self.duration_ms:.1f}ms"
