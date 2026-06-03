from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chat import ChatMessage, ChatSession


class ConversationMemory:
    def __init__(self) -> None:
        self.settings = get_settings()

    def get_or_create_session(
        self,
        db: Session,
        *,
        session_id: UUID | None,
        user_id: UUID | None,
        language: str | None,
        mode: str,
        first_message: str,
    ) -> ChatSession:
        if session_id:
            session = db.get(ChatSession, session_id)
            if session:
                return session
        session = ChatSession(
            user_id=user_id,
            language=language,
            mode=mode,
            title=first_message[:80],
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def recent_messages(self, db: Session, session_id: UUID) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(self.settings.memory_max_messages)
        )
        return list(reversed(db.scalars(stmt).all()))

    def save_message(
        self,
        db: Session,
        *,
        session_id: UUID,
        role: str,
        content: str,
        citations: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            meta=metadata or {},
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
