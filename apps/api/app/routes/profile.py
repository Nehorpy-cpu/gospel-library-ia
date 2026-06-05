from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from app.core.logging import logger
from app.services.auth import get_request_auth_context, normalize_user_id, require_user
from app.services.db import get_conn

router = APIRouter(prefix="/api/profile", tags=["profile"], dependencies=[Depends(require_user)])
log = logger(__name__)


class CallingPreferencePayload(BaseModel):
    callingCategory: str | None = Field(default=None, max_length=120)
    callingName: str | None = Field(default=None, max_length=200)
    customCallingName: str | None = Field(default=None, max_length=200)
    callingFocusEnabled: bool = False


def current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        context = get_request_auth_context()
        if context:
            return context.user_id
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return normalize_user_id(x_user_id)


@router.get("/preferences")
def get_preferences(user_id: str | None = Header(default=None, alias="X-User-Id")):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            SELECT user_id::text, calling_category, calling_name, custom_calling_name,
                   calling_focus_enabled, updated_at
            FROM user_preferences
            WHERE user_id = %(user_id)s
            """,
            {"user_id": user_id},
        ).fetchone()
    if not row:
        return _preference_row(
            {
                "user_id": user_id,
                "calling_category": None,
                "calling_name": None,
                "custom_calling_name": None,
                "calling_focus_enabled": False,
                "updated_at": None,
            }
        )
    return _preference_row(row)


@router.patch("/preferences")
def update_preferences(
    payload: CallingPreferencePayload,
    user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = current_user_id(user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO user_preferences (
              user_id, calling_category, calling_name, custom_calling_name, calling_focus_enabled
            )
            VALUES (
              %(user_id)s, %(calling_category)s, %(calling_name)s,
              %(custom_calling_name)s, %(calling_focus_enabled)s
            )
            ON CONFLICT (user_id) DO UPDATE SET
              calling_category = EXCLUDED.calling_category,
              calling_name = EXCLUDED.calling_name,
              custom_calling_name = EXCLUDED.custom_calling_name,
              calling_focus_enabled = EXCLUDED.calling_focus_enabled,
              updated_at = now()
            RETURNING user_id::text, calling_category, calling_name, custom_calling_name,
                      calling_focus_enabled, updated_at
            """,
            {
                "user_id": user_id,
                "calling_category": payload.callingCategory,
                "calling_name": payload.callingName,
                "custom_calling_name": payload.customCallingName,
                "calling_focus_enabled": payload.callingFocusEnabled,
            },
        ).fetchone()
        conn.commit()
    log.info("user_calling_preferences_updated", user_id=user_id, calling_name=payload.callingName)
    return _preference_row(row)


def _preference_row(row: dict) -> dict:
    return {
        "userId": row["user_id"],
        "callingCategory": row["calling_category"],
        "callingName": row["calling_name"],
        "customCallingName": row["custom_calling_name"],
        "callingFocusEnabled": row["calling_focus_enabled"],
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }
