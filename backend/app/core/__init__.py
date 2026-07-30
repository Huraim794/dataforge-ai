from typing import Any


def __getattr__(name: str) -> Any:
    if name == "settings":
        from app.core.config import settings as _settings

        return _settings
    if name in ("get_async_session", "engine", "Base"):
        from app.core.database import get_async_session, engine, Base  # noqa: F401

        return locals()[name]
    if name in ("get_current_user", "get_optional_user", "get_db"):
        from app.core.deps import get_current_user, get_optional_user, get_db  # noqa: F401

        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
