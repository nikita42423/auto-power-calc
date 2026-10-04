from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

CURRENT_USER_ID = 1

async def get_current_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id_user == CURRENT_USER_ID))
    return result.scalar_one()