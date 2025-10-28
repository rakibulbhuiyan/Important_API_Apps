from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    JWT middleware for Channels 3
    Accepts token in query string (?token=<jwt>) or Authorization header
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Default anonymous
        scope['user'] = AnonymousUser()

        # Check query string
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]

        # Check Authorization header
        if not token:
            headers = dict((k.decode().lower(), v.decode()) for k, v in scope.get('headers', []))
            auth = headers.get('authorization')
            if auth and auth.lower().startswith('bearer '):
                token = auth.split(None, 1)[1].strip()

        if token:
            scope['user'] = await get_user_from_token(token)
        return await self.app(scope, receive, send)

from django.utils import timezone
from django.core.cache import cache


# ---------------- Presence based on ANY API activity ----------------
class PresenceActivityMiddleware:
    """
    any authenticated HTTP API get request  update their pesence
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # 120s good default (API hit no hit ২ minutes offline)
        self.ACTIVITY_TTL = 120

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            now_iso = timezone.now().isoformat()
            cache.set(f"user:{user.id}:online", 1, timeout=self.ACTIVITY_TTL)
            cache.set(f"user:{user.id}:last_seen", now_iso, timeout=None)
        return response
    
    