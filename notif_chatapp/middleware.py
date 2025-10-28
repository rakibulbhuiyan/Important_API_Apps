from urllib.parse import parse_qs
import logging
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

@database_sync_to_async
def _user_from_token(token: str):
    try:
        auth = JWTAuthentication()
        validated = auth.get_validated_token(token)
        user = auth.get_user(validated)
        print(f"[JWT Middleware] ✅ Token validated for user_id={user.id}")
        return user
    except Exception as e:
        print(f"[JWT Middleware] ❌ JWT validation failed: {e}")
        logger.warning("JWT validation failed: %s", e)
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        token = None
        
        try:
            # 1️⃣ Try to get token from Authorization header
            headers = dict(scope.get("headers") or [])
            auth_header = headers.get(b"authorization", b"").decode(errors="ignore")
            
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                print(f"[JWT Middleware] 📝 Token from header: {token[:20]}...")

            # 2️⃣ If not in header, try query string
            if not token:
                query_string = (scope.get("query_string") or b"").decode(errors="ignore")
                print(f"[JWT Middleware] 🔍 Query string: {query_string}")
                
                qs = parse_qs(query_string)
                token = (qs.get("token") or [None])[0]
                
                if token:
                    print(f"[JWT Middleware] 📝 Token from query: {token[:20]}...")
                else:
                    print("[JWT Middleware] ⚠️ No token found in query string")

            # 3️⃣ Validate token
            if token:
                user = await _user_from_token(token)
                scope["user"] = user
                
                print(f"[JWT Middleware] 🔐 Final result: user_id={getattr(user, 'id', None)}, "
                      f"is_authenticated={getattr(user, 'is_authenticated', False)}, "
                      f"is_anonymous={getattr(user, 'is_anonymous', True)}")
            else:
                print("[JWT Middleware] ❌ No token provided")
                
        except Exception as e:
            print(f"[JWT Middleware] 💥 Exception: {e}")
            logger.exception("JWTAuthMiddleware error: %s", e)
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)