from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.redis import create_session, delete_session
from core.security import hash_password, verify_password
from db.session import get_db
from models.user import User

router = APIRouter(prefix="/api", tags=["Аутентификация"])


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_TTL,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/register",
    summary="Регистрация пользователя",
    description=(
        "Создаёт нового пользователя с хешированным (bcrypt) паролем. "
        "Доступно без авторизации. При повторном username возвращается 409."
    ),
    responses={
        201: {"description": "Пользователь создан"},
        409: {"description": "Пользователь с таким username уже существует"},
    },
)
async def register(
    username: str = Form(..., description="Уникальное имя пользователя"),
    password: str = Form(..., description="Пароль (хранится в виде bcrypt-хеша)"),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Пользователь уже существует")

    user = User(username=username, password=hash_password(password))
    db.add(user)
    await db.commit()
    return Response(status_code=201)


@router.post(
    "/login",
    status_code=200,
    summary="Аутентификация (вход)",
    description=(
        "Проверяет username и пароль, создаёт сессию в Redis "
        "(ключ session:{sid} хранит id пользователя, TTL — параметр SESSION_TTL) "
        "и устанавливает HttpOnly-cookie session_id. "
        "Cookie используется для авторизации остальных методов "
        "(кнопка Authorize в Swagger или заголовок Cookie в Insomnia/Postman)."
    ),
    responses={
        200: {
            "description": "Вход выполнен, в ответе установлен cookie session_id",
            "headers": {
                "Set-Cookie": {
                    "description": "session_id=<sid>; HttpOnly; SameSite=Lax",
                    "schema": {"type": "string"},
                }
            },
        },
        403: {"description": "Неверный username или пароль"},
    },
)
async def login(
    username: str = Form(..., description="Имя пользователя"),
    password: str = Form(..., description="Пароль"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password):
        raise HTTPException(status_code=403, detail="Неверный username или пароль")

    session_id = await create_session(user.id_user)
    response = JSONResponse(content={"session": session_id})
    _set_session_cookie(response, session_id)
    return response


@router.post(
    "/logout",
    response_class=Response,
    summary="Выход (завершение сессии)",
    description=(
        "Удаляет сессию пользователя из Redis и сбрасывает cookie session_id. "
        "Без cookie — no-op, всё равно 200 без тела."
    ),
    responses={
        200: {"description": "Сессия завершена (или её и не было)"},
    },
)
async def logout(
    session_id: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE_NAME),
):
    if session_id is not None:
        await delete_session(session_id)
    response = Response()
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return response
