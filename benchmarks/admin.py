from django.contrib import admin

from benchmarks.models import BenchmarkResult, Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "product_count")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active")
    list_filter = ("is_active", "category")


@admin.register(BenchmarkResult)
class BenchmarkResultAdmin(admin.ModelAdmin):
    list_display = ("scenario", "mode", "duration_ms", "db_time_ms", "external_io_time_ms", "cpu_time_ms", "created_at")
    list_filter = ("scenario", "mode")
