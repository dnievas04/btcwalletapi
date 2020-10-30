from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions


class TokenAdminAuthentication(BaseAuthentication):
    """
    Hardcoded Token authentication.
    Token must be provided using the PLATFORM_ADMIN_TOKEN setting
    """

    keyword = "Token"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _(
                "Invalid token header. Token string should not contain invalid characters."
            )
            raise exceptions.AuthenticationFailed(msg)
        if token == settings.PLATFORM_ADMIN_TOKEN:
            return (AnonymousUser, None)
        else:
            raise exceptions.AuthenticationFailed(_("Invalid token."))
        return None
