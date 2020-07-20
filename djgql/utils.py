from django.core.cache import cache


def get_user_from_cache(username):
    return cache.get(f'user:username:{username}')


def set_user_to_cache(user):
    key = f'user:username:{user.get_username()}'
    cache.set(key, user, timeout=3600)
