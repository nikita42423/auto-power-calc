from fastapi import Cookie, Depends, HTTPException, Security
from fastapi.security import APIKeyCookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.redis import get_session_user
from db.session import get_db
from models.user import User

# deprecated: используется только legacy HTML-обработчиками (api/handlers.py)
CURRENT_USER_ID = 1

cookie_scheme = APIKeyCookie(name=settings.SESSION_COOKIE_NAME, auto_error=False)


async def get_optional_user(
    session_id: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if session_id is None:
        return None
    user_id = await get_session_user(session_id)
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id_user == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    _cookie_doc: str | None = Security(cookie_scheme),
    user: User | None = Depends(get_optional_user),
) -> User:
    """Защищённая зависимость: Security(cookie_scheme) добавляет APIKeyCookie
    в OpenAPI только для методов, которые ею пользуются (кнопка Authorize)."""
    if user is None:
        raise HTTPException(status_code=401, detail="Не аутентифицирован")
    return user
