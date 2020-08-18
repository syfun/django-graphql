from functools import wraps

from djgql.exceptions import AuthenticationError


def login_required(func):
    @wraps(func)
    def wrap(parent, info, *args, **kwargs):
        request = info.context['request']
        if 'authenticated' not in request.auth.scopes:
            raise AuthenticationError()
        info.context['user'] = request.user

        return func(*args, **kwargs)

    return wrap
