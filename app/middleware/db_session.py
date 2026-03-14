from fastapi import Request
from typing import Callable
from app.db.models import SessionLocal

async def db_session_middleware(request: Request, call_next):
    """Middleware to provide database session per request."""
    request.state.db = SessionLocal()
    try:
        response = await call_next(request)
        request.state.db.commit()
        return response
    except Exception as e:
        request.state.db.rollback()
        raise
    finally:
        request.state.db.close()