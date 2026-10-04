from fastapi import APIRouter, Depends, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models.user import User

router = APIRouter(prefix="/api")


@router.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none() is not None:
        return {"error": "username taken"}

    user = User(username=username, password=password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id_user": user.id_user, "username": user.username}


@router.post("/login")
async def login():
    return {"message": "stub"}


@router.post("/logout")
async def logout():
    return {"message": "stub"}