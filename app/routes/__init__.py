"""
Routes package for DigiCloset API endpoints.

Contains all FastAPI route modules for different API versions and features.
"""

from .merchant_dashboard import router as dashboard_router

__all__ = [
    "dashboard_router",
]