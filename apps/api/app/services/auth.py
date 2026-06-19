from contextvars import ContextVar
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import Depends, Header, HTTPException, status
from psycopg.rows import dict_row

try:
    import jwt
    from jwt import PyJWKClient
except ImportError:  # pragma: no cover - exercised only in incomplete local Python envs.
    jwt = None
    PyJWKClient = None

from app.core.config import get_settings
from app.services.db import get_conn


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    external_id: str
    role: str = "user"
    email: str | None = None
    provider: str = "local"


_request_auth_context: ContextVar[AuthContext | None] = ContextVar("request_auth_context", default=None)


def normalize_user_id(value: str) -> str:
    clean = value.strip()
    try:
        return str(UUID(clean))
    except ValueError:
        return str(uuid5(NAMESPACE_URL, f"gospel-library-ia:user:{clean}"))


def _split_csv(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _plain_header(value: str | None) -> str | None:
    return value if isinstance(value, str) else None


def _admin_role(user_id: str, role: str | None, email: str | None) -> str:
    settings = get_settings()
    admin_user_ids = _split_csv(settings.admin_user_ids)
    admin_emails = _split_csv(settings.clerk_admin_emails)
    if role and role.lower() == "admin":
        return "admin"
    if user_id.lower() in admin_user_ids:
        return "admin"
    if email and email.lower() in admin_emails:
        return "admin"
    return "user"


def _decode_clerk_token(token: str) -> AuthContext:
    settings = get_settings()
    if jwt is None or PyJWKClient is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PyJWT is required for Clerk JWT verification",
        )
    if not settings.clerk_jwks_url or not settings.clerk_jwt_issuer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk JWT verification is not configured",
        )
    try:
        signing_key = PyJWKClient(settings.clerk_jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_jwt_issuer,
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token") from exc

    external_id = str(claims.get("sub") or "")
    if not external_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth subject")
    email = claims.get("email") or claims.get("primary_email_address")
    email_addresses = claims.get("email_addresses")
    if not email and isinstance(email_addresses, list) and email_addresses:
        first_email = email_addresses[0]
        if isinstance(first_email, dict):
            email = first_email.get("email_address")
    role = claims.get("role") or (claims.get("public_metadata") or {}).get("role")
    user_id = normalize_user_id(external_id)
    context = AuthContext(
        user_id=user_id,
        external_id=external_id,
        role=_admin_role(user_id, str(role) if role else None, str(email) if email else None),
        email=str(email) if email else None,
        provider="clerk",
    )
    _request_auth_context.set(context)
    return context


def current_auth_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
) -> AuthContext:
    authorization = _plain_header(authorization)
    x_user_id = _plain_header(x_user_id)
    x_user_role = _plain_header(x_user_role)
    x_user_email = _plain_header(x_user_email)
    settings = get_settings()
    if authorization and authorization.lower().startswith("bearer "):
        return _decode_clerk_token(authorization.split(" ", 1)[1].strip())

    if settings.env == "production" and not settings.allow_dev_auth_headers:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_id = normalize_user_id(x_user_id)
    context = AuthContext(
        user_id=user_id,
        external_id=x_user_id,
        role=_admin_role(user_id, x_user_role, x_user_email),
        email=x_user_email,
        provider="local",
    )
    _request_auth_context.set(context)
    return context


def current_study_auth_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
) -> AuthContext:
    try:
        return current_auth_context(
            authorization=authorization,
            x_user_id=x_user_id,
            x_user_role=x_user_role,
            x_user_email=x_user_email,
        )
    except HTTPException as exc:
        settings = get_settings()
        demo_user_id = normalize_user_id(settings.study_demo_user_id)
        request_user_id = normalize_user_id(x_user_id) if x_user_id else None
        if (
            exc.status_code == status.HTTP_401_UNAUTHORIZED
            and settings.allow_study_demo_user
            and request_user_id == demo_user_id
        ):
            context = AuthContext(
                user_id=demo_user_id,
                external_id=x_user_id or settings.study_demo_user_id,
                role="user",
                email=x_user_email,
                provider="study-demo",
            )
            _request_auth_context.set(context)
            return context
        raise


def get_request_auth_context() -> AuthContext | None:
    return _request_auth_context.get()


def require_user(context: AuthContext = Depends(current_auth_context)) -> AuthContext:
    _require_beta_access(context)
    return context


def require_study_user(context: AuthContext = Depends(current_study_auth_context)) -> AuthContext:
    if context.provider != "study-demo":
        _require_beta_access(context)
    return context


def require_admin(context: AuthContext = Depends(current_auth_context)) -> AuthContext:
    if context.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return context


def _require_beta_access(context: AuthContext) -> None:
    settings = get_settings()
    if not settings.beta_allowlist_enabled or context.role == "admin":
        return
    if not context.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Beta access requires an approved email")
    try:
        with get_conn() as conn:
            conn.row_factory = dict_row
            row = conn.execute(
                """
                SELECT status
                FROM beta_access
                WHERE lower(email) = lower(%(email)s)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                {"email": context.email},
            ).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Beta access check unavailable") from exc
    if not row or row["status"] != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Beta access pending")
