from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.logging import logger
from app.services.auth import AuthContext, current_auth_context, normalize_user_id, require_admin, require_user
from app.services.db import get_conn

router = APIRouter(prefix="/api", tags=["beta"])
log = logger(__name__)

FeedbackType = Literal["bug", "suggestion", "doctrinal_source_issue", "ui_issue", "other"]
FeedbackStatus = Literal["new", "reviewing", "resolved", "closed"]


class BetaAccessRequest(BaseModel):
    email: str = Field(max_length=320)
    name: str | None = Field(default=None, max_length=160)
    message: str | None = Field(default=None, max_length=1000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        clean = value.strip().lower()
        if "@" not in clean or "." not in clean.rsplit("@", 1)[-1]:
            raise ValueError("Invalid email")
        return clean


class BetaOnboardingPayload(BaseModel):
    callingProfile: str = Field(min_length=2, max_length=160)
    language: str = Field(default="es", max_length=16)
    preferredSources: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("preferredSources")
    @classmethod
    def clean_sources(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class FeedbackPayload(BaseModel):
    page: str = Field(default="/", max_length=300)
    type: FeedbackType = "other"
    message: str = Field(min_length=5, max_length=4000)
    screenshotUrl: str | None = Field(default=None, max_length=1000)


class FeedbackStatusPayload(BaseModel):
    status: FeedbackStatus


class BetaApprovalPayload(BaseModel):
    email: str = Field(max_length=320)
    status: Literal["pending", "approved", "rejected"] = "approved"
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return BetaAccessRequest.validate_email(value)


@router.get("/beta/version")
def beta_version():
    settings = get_settings()
    return {
        "name": "Gospel Library IA Beta",
        "version": settings.beta_version,
        "environment": settings.beta_environment,
        "changelog": "/CHANGELOG.md",
    }


@router.get("/beta/status")
def beta_status(context: AuthContext = Depends(current_auth_context)):
    settings = get_settings()
    status_value = "approved" if not settings.beta_allowlist_enabled or context.role == "admin" else "pending"
    row = None
    if context.email:
        with get_conn() as conn:
            conn.row_factory = dict_row
            row = conn.execute(
                """
                SELECT status, approved_at, onboarding_completed_at, preferred_language, preferred_sources, study_profile
                FROM beta_access
                WHERE lower(email) = lower(%(email)s)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                {"email": context.email},
            ).fetchone()
    if row and settings.beta_allowlist_enabled and context.role != "admin":
        status_value = row["status"]
    return {
        "userId": context.user_id,
        "email": context.email,
        "allowlistEnabled": settings.beta_allowlist_enabled,
        "status": status_value,
        "approved": status_value == "approved",
        "onboardingCompleted": bool(row and row["onboarding_completed_at"]),
        "preferredLanguage": row["preferred_language"] if row else None,
        "preferredSources": row["preferred_sources"] if row else [],
        "studyProfile": row["study_profile"] if row else None,
        "limits": _beta_limits(),
    }


@router.post("/beta/request-access", status_code=status.HTTP_201_CREATED)
def request_beta_access(payload: BetaAccessRequest):
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO beta_access (email, name, status, request_message)
            VALUES (%(email)s, %(name)s, 'pending', %(message)s)
            ON CONFLICT (email) DO UPDATE SET
              name = COALESCE(EXCLUDED.name, beta_access.name),
              request_message = COALESCE(EXCLUDED.request_message, beta_access.request_message),
              updated_at = now()
            RETURNING id::text, email, name, status, created_at, updated_at
            """,
            {"email": str(payload.email).lower(), "name": payload.name, "message": payload.message},
        ).fetchone()
        conn.commit()
    return _beta_access_row(row)


@router.post("/beta/onboarding")
def complete_onboarding(
    payload: BetaOnboardingPayload,
    context: AuthContext = Depends(current_auth_context),
):
    email = (context.email or f"{context.user_id}@local.beta").lower()
    status_value = "approved" if not get_settings().beta_allowlist_enabled or context.role == "admin" else "pending"
    with get_conn() as conn:
        conn.row_factory = dict_row
        existing = conn.execute(
            "SELECT status FROM beta_access WHERE lower(email) = lower(%(email)s)",
            {"email": email},
        ).fetchone()
        effective_status = status_value
        if status_value != "approved" and existing and existing["status"]:
            effective_status = existing["status"]
        row = conn.execute(
            """
            INSERT INTO beta_access (
              user_id, email, name, status, study_profile, preferred_language,
              preferred_sources, onboarding_completed_at
            )
            VALUES (
              %(user_id)s, %(email)s, %(name)s, %(status)s, %(study_profile)s,
              %(preferred_language)s, %(preferred_sources)s, now()
            )
            ON CONFLICT (email) DO UPDATE SET
              user_id = EXCLUDED.user_id,
              status = EXCLUDED.status,
              study_profile = EXCLUDED.study_profile,
              preferred_language = EXCLUDED.preferred_language,
              preferred_sources = EXCLUDED.preferred_sources,
              approved_at = CASE WHEN EXCLUDED.status = 'approved' THEN now() ELSE beta_access.approved_at END,
              onboarding_completed_at = now(),
              updated_at = now()
            RETURNING id::text, user_id::text, email, name, status, study_profile,
                      preferred_language, preferred_sources, onboarding_completed_at, created_at, updated_at
            """,
            {
                "user_id": context.user_id,
                "email": email,
                "name": context.external_id,
                "status": effective_status,
                "study_profile": payload.callingProfile,
                "preferred_language": payload.language,
                "preferred_sources": Jsonb(payload.preferredSources),
            },
        ).fetchone()
        conn.commit()
    log.info("beta_onboarding_completed", user_id=context.user_id, status=row["status"])
    return _beta_access_row(row)


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackPayload,
    context: AuthContext = Depends(require_user),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    user_id = normalize_user_id(context.user_id)
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO beta_feedback (user_id, email, page, type, message, screenshot_url)
            VALUES (%(user_id)s, %(email)s, %(page)s, %(type)s, %(message)s, %(screenshot_url)s)
            RETURNING id::text, user_id::text, email, page, type, message, screenshot_url, status, created_at, updated_at
            """,
            {
                "user_id": user_id,
                "email": x_user_email,
                "page": payload.page,
                "type": payload.type,
                "message": payload.message,
                "screenshot_url": payload.screenshotUrl,
            },
        ).fetchone()
        conn.commit()
    log.info("beta_feedback_created", feedback_id=row["id"], user_id=user_id, feedback_type=payload.type)
    return _feedback_row(row)


@router.get("/admin/beta", dependencies=[Depends(require_admin)])
def admin_beta(limit: int = Query(default=50, ge=1, le=200)):
    with get_conn() as conn:
        conn.row_factory = dict_row
        users = conn.execute(
            """
            SELECT id::text, user_id::text, email, name, status, study_profile,
                   preferred_language, preferred_sources, onboarding_completed_at,
                   approved_at, created_at, updated_at
            FROM beta_access
            ORDER BY updated_at DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        feedback = conn.execute(
            """
            SELECT id::text, user_id::text, email, page, type, message, screenshot_url, status, created_at, updated_at
            FROM beta_feedback
            ORDER BY created_at DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        metrics = _beta_metrics(conn)
    return {
        "version": {
            "name": "Gospel Library IA Beta",
            "version": get_settings().beta_version,
            "environment": get_settings().beta_environment,
        },
        "limits": _beta_limits(),
        "users": [_beta_access_row(row) for row in users],
        "feedback": [_feedback_row(row) for row in feedback],
        "metrics": metrics,
    }


@router.post("/admin/beta/approve", dependencies=[Depends(require_admin)])
def approve_beta_user(payload: BetaApprovalPayload):
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            INSERT INTO beta_access (email, status, admin_notes, approved_at)
            VALUES (
              %(email)s, %(status)s::varchar, %(notes)s,
              CASE WHEN %(is_approved)s THEN now() ELSE NULL END
            )
            ON CONFLICT (email) DO UPDATE SET
              status = EXCLUDED.status,
              admin_notes = EXCLUDED.admin_notes,
              approved_at = CASE WHEN EXCLUDED.status = 'approved'::varchar THEN now() ELSE beta_access.approved_at END,
              updated_at = now()
            RETURNING id::text, user_id::text, email, name, status, study_profile,
                      preferred_language, preferred_sources, onboarding_completed_at, approved_at, created_at, updated_at
            """,
            {
                "email": str(payload.email).lower(),
                "status": payload.status,
                "notes": payload.notes,
                "is_approved": payload.status == "approved",
            },
        ).fetchone()
        conn.commit()
    return _beta_access_row(row)


@router.patch("/admin/feedback/{feedback_id}", dependencies=[Depends(require_admin)])
def update_feedback_status(feedback_id: str, payload: FeedbackStatusPayload):
    with get_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            """
            UPDATE beta_feedback
            SET status = %(status)s, updated_at = now()
            WHERE id::text = %(feedback_id)s
            RETURNING id::text, user_id::text, email, page, type, message, screenshot_url, status, created_at, updated_at
            """,
            {"feedback_id": feedback_id, "status": payload.status},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
        conn.commit()
    return _feedback_row(row)


def _beta_limits() -> dict:
    settings = get_settings()
    return {
        "maxWorkspacesPerUser": settings.beta_max_workspaces_per_user,
        "maxAiSearchesPerDay": settings.max_user_chat_messages_per_day,
        "maxTalkBuilderPerDay": settings.max_user_talk_builder_per_day,
        "maxExportsPerDay": settings.max_user_exports_per_day,
        "textualFallback": "high_limit",
    }


def _beta_metrics(conn) -> dict:
    def scalar(sql: str) -> int:
        row = conn.execute(sql).fetchone()
        if not row:
            return 0
        if isinstance(row, dict):
            for value in row.values():
                try:
                    return int(value or 0)
                except (TypeError, ValueError):
                    continue
            return 0
        return int(row[0] or 0)

    return {
        "betaUsers": scalar("SELECT count(*) FROM beta_access"),
        "approvedUsers": scalar("SELECT count(*) FROM beta_access WHERE status = 'approved'"),
        "activeUsers": scalar("SELECT count(DISTINCT user_id) FROM study_workspaces WHERE updated_at >= now() - interval '30 days'"),
        "workspacesCreated": scalar("SELECT count(*) FROM study_workspaces WHERE deleted_at IS NULL"),
        "savedQuotes": scalar("SELECT count(*) FROM saved_citations WHERE deleted_at IS NULL"),
        "postItsCreated": scalar("SELECT count(*) FROM post_its WHERE deleted_at IS NULL"),
        "exports": scalar("SELECT count(*) FROM beta_activity_events WHERE kind = 'export'"),
        "feedback": scalar("SELECT count(*) FROM beta_feedback"),
        "documentsIndexed": scalar("SELECT count(*) FROM documents WHERE is_indexed IS TRUE"),
        "recentErrors": scalar("SELECT count(*) FROM ingestion_jobs WHERE lower(status) IN ('failed', 'error')"),
    }


def _beta_access_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "userId": row.get("user_id"),
        "email": row["email"],
        "name": row.get("name"),
        "status": row["status"],
        "studyProfile": row.get("study_profile"),
        "preferredLanguage": row.get("preferred_language"),
        "preferredSources": row.get("preferred_sources") or [],
        "onboardingCompletedAt": row.get("onboarding_completed_at").isoformat() if row.get("onboarding_completed_at") else None,
        "approvedAt": row.get("approved_at").isoformat() if row.get("approved_at") else None,
        "createdAt": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updatedAt": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _feedback_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "userId": row.get("user_id"),
        "email": row.get("email"),
        "page": row["page"],
        "type": row["type"],
        "message": row["message"],
        "screenshotUrl": row.get("screenshot_url"),
        "status": row["status"],
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }
