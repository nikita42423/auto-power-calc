import uuid

from redis.asyncio import Redis

from core.config import settings

redis_client: Redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def create_session(user_id: int) -> str:
    session_id = uuid.uuid4().hex
    await redis_client.set(
        f"session:{session_id}",
        str(user_id),
        ex=settings.SESSION_TTL,
    )
    return session_id


async def get_session_user(session_id: str) -> int | None:
    value = await redis_client.get(f"session:{session_id}")
    return int(value) if value is not None else None


async def delete_session(session_id: str) -> None:
    await redis_client.delete(f"session:{session_id}")
