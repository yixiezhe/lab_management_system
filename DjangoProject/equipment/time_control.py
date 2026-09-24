from datetime import datetime

from django.core.cache import cache
from django.utils import timezone


_TEST_NOW_CACHE_KEY = "equipment:test_now_iso"


def _ensure_local_aware(dt_value):
    if timezone.is_naive(dt_value):
        return timezone.make_aware(dt_value, timezone.get_current_timezone())
    return timezone.localtime(dt_value)


def get_test_now():
    iso_value = cache.get(_TEST_NOW_CACHE_KEY)
    if not iso_value:
        return None
    try:
        parsed = datetime.fromisoformat(iso_value)
    except (TypeError, ValueError):
        cache.delete(_TEST_NOW_CACHE_KEY)
        return None
    return _ensure_local_aware(parsed)


def set_test_now(dt_value):
    aware_local = _ensure_local_aware(dt_value)
    cache.set(_TEST_NOW_CACHE_KEY, aware_local.isoformat(), timeout=None)
    return aware_local


def clear_test_now():
    cache.delete(_TEST_NOW_CACHE_KEY)


def get_controlled_now(anchor=None):
    if anchor is not None:
        return timezone.localtime(anchor)
    mocked = get_test_now()
    if mocked is not None:
        return mocked
    return timezone.localtime()


def get_controlled_today(anchor=None):
    return get_controlled_now(anchor=anchor).date()
