"""
Provides various authentication policies.
"""
import base64
import binascii
import typing

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext_lazy as _

from djgql.exceptions import AuthenticationError


class AuthCredentials:
    def __init__(self, scopes: typing.Sequence[str] = None):
        self.scopes = [] if scopes is None else list(scopes)


class UnauthenticatedUser(AnonymousUser):
    def __init__(self, error: AuthenticationError = None):
        self.error = error


def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, str):
        auth = auth.encode()
    return auth


class BaseAuthMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        raise NotImplementedError(".authenticate() must be overridden.")

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        pass

    def __call__(self, request):
        try:
            auth, user = self.authenticate(request)
        except AuthenticationError as exc:
            auth = AuthCredentials()
            user = UnauthenticatedUser(exc)
        finally:
            request.auth, request.user = auth, user
        return self.get_response(request)


class BasicAuthMiddleware(BaseAuthMiddleware):
    """
    HTTP Basic authentication against username/password.
    """

    www_authenticate_realm = 'api'

    def authenticate(self, request):
        """
        Returns a `User` if a correct username and password have been supplied
        using HTTP Basic authentication.  Otherwise returns `None`.
        """
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'basic':
            return None, None

        if len(auth) == 1:
            msg = _('Invalid basic header. No credentials provided.')
            raise AuthenticationError(msg)
        elif len(auth) > 2:
            msg = _('Invalid basic header. Credentials string should not contain spaces.')
            raise AuthenticationError(msg)
        try:
            auth_parts = base64.b64decode(auth[1]).decode().partition(':')
        except (TypeError, UnicodeDecodeError, binascii.Error):
            msg = _('Invalid basic header. Credentials not correctly base64 encoded.')
            raise AuthenticationError(msg)

        userid, password = auth_parts[0], auth_parts[2]
        return self.authenticate_credentials(userid, password, request)

    def authenticate_credentials(self, userid, password, request=None):
        """
        Authenticate the userid and password against username and password
        with optional request for context.
        """
        credentials = {get_user_model().USERNAME_FIELD: userid, 'password': password}
        user = authenticate(request=request, **credentials)

        if user is None:
            raise AuthenticationError(_('Invalid username/password.'))

        if not user.is_active:
            raise AuthenticationError(_('User inactive or deleted.'))

        return AuthCredentials(['authenticated']), user

    def authenticate_header(self, request):
        return 'Basic realm="%s"' % self.www_authenticate_realm
