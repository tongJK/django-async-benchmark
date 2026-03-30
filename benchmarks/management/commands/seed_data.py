import random

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from benchmarks.models import Category, Product

CATEGORIES = [
    "Electronics", "Books", "Clothing", "Home & Garden", "Sports",
    "Toys", "Food & Beverage", "Health", "Automotive", "Music",
    "Office Supplies", "Pet Supplies", "Beauty", "Tools", "Software",
]


class Command(BaseCommand):
    help = "Seed Product and Category data for benchmarking"

    def add_arguments(self, parser):
        parser.add_argument(
            "--products", type=int, default=10_000,
            help="Number of products to create (default: 10000)",
        )

    def handle(self, *args, **options):
        product_count = options["products"]

        # Create categories
        categories = Category.objects.bulk_create(
            [Category(name=name, slug=slugify(name)) for name in CATEGORIES],
            ignore_conflicts=True,
        )
        categories = list(Category.objects.all())
        self.stdout.write(f"Categories: {len(categories)}")

        # Create products in batches
        batch_size = 2000
        created = 0
        for i in range(0, product_count, batch_size):
            batch = [
                Product(
                    name=f"Product {i + j + 1}",
                    category=random.choice(categories),
                    price=round(random.uniform(1, 999), 2),
                    stock=random.randint(0, 500),
                    is_active=random.random() > 0.1,  # 90% active
                    description=f"Description for product {i + j + 1}",
                )
                for j in range(min(batch_size, product_count - i))
            ]
            Product.objects.bulk_create(batch)
            created += len(batch)
            self.stdout.write(f"  Created {created}/{product_count} products")

        # Update denormalized counts
        for cat in categories:
            cat.product_count = cat.products.count()
        Category.objects.bulk_update(categories, ["product_count"])

        self.stdout.write(self.style.SUCCESS(
            f"Done: {len(categories)} categories, {created} products"
        ))
