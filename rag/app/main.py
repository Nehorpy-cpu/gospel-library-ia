from fastapi import FastAPI

from app.api.routes import router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Gospel Library IA RAG", version="0.1.0")
app.include_router(router)
