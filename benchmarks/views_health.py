from django.db import connection
from django.http import JsonResponse


def health(request):
    """Health check — verifies DB connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "unhealthy", "db": db_ok}, status=status)
