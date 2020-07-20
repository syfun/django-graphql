import jwt
from django.contrib.auth import get_user_model
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _

from djgql.auth import BaseAuthentication, get_authorization_header
from djgql.exceptions import AuthenticationError
from djgql.settings import api_settings as django_settings

from .settings import api_settings

jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
jwt_get_username_from_payload = api_settings.JWT_PAYLOAD_GET_USERNAME_HANDLER

get_user_from_cache = django_settings.USER_CACHE_GETTER
set_user_to_cache = django_settings.USER_CACHE_SETTER

JWT_USER_CACHE = api_settings.JWT_USER_CACHE


class BaseJSONWebTokenAuthentication(BaseAuthentication):
    """
    Token based authentication using the JSON Web Token standard.
    """

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            return None

        try:
            payload = jwt_decode_handler(jwt_value)
        except jwt.ExpiredSignature:
            msg = _('Signature has expired.')
            raise AuthenticationError(msg)
        except jwt.DecodeError:
            msg = _('Error decoding signature.')
            raise AuthenticationError(msg)
        except jwt.InvalidTokenError:
            raise AuthenticationError()

        user = self.authenticate_credentials(payload)

        return user, jwt_value

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        User = get_user_model()
        username = jwt_get_username_from_payload(payload)

        if not username:
            msg = _('Invalid payload.')
            raise AuthenticationError(msg)

        user = None
        if JWT_USER_CACHE:
            user = get_user_from_cache(username)
        if not user:
            try:
                user = User.objects.get_by_natural_key(username)
            except User.DoesNotExist:
                msg = _('Invalid signature.')
                raise AuthenticationError(msg)
            else:
                if JWT_USER_CACHE:
                    set_user_to_cache(user)

        if not user.is_active:
            msg = _('User account is disabled.')
            raise AuthenticationError(msg)

        return user


class JSONWebTokenAuthentication(BaseJSONWebTokenAuthentication):
    """
    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string specified in the setting
    `JWT_AUTH_HEADER_PREFIX`. For example:

        Authorization: JWT eyJhbGciOiAiSFMyNTYiLCAidHlwIj
    """

    www_authenticate_realm = 'api'

    def get_jwt_value(self, request):
        auth = get_authorization_header(request).split()
        auth_header_prefix = api_settings.JWT_AUTH_HEADER_PREFIX.lower()

        if not auth:
            if api_settings.JWT_AUTH_COOKIE:
                return request.COOKIES.get(api_settings.JWT_AUTH_COOKIE)
            return None

        if smart_text(auth[0].lower()) != auth_header_prefix:
            return None

        if len(auth) == 1:
            msg = _('Invalid Authorization header. No credentials provided.')
            raise AuthenticationError(msg)
        elif len(auth) > 2:
            msg = _(
                'Invalid Authorization header. Credentials string ' 'should not contain spaces.'
            )
            raise AuthenticationError(msg)

        return auth[1]

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return '{0} realm="{1}"'.format(
            api_settings.JWT_AUTH_HEADER_PREFIX, self.www_authenticate_realm
        )
