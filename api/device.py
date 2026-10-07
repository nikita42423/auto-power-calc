from datetime import datetime
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models.device import Device
from models.like import Like
from api.deps import CURRENT_USER_ID
from api.serializers import device_serializer
from minio_client import upload_file

router = APIRouter(prefix="/api")


@router.get("/devices")
async def get_devices(
    power_min: int | None = Query(None),
    power_max: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Device).where(Device.status == "опубликован")
    if power_min is not None:
        stmt = stmt.where(Device.power >= power_min)
    if power_max is not None:
        stmt = stmt.where(Device.power <= power_max)
    result = await db.execute(stmt)
    devices = result.scalars().all()
    return [
        {**device_serializer(d), "is_creator": 1 if d.id_user == CURRENT_USER_ID else 0}
        for d in devices
    ]


async def _feed_out(db: AsyncSession, device: Device) -> dict:
    like_count_result = await db.execute(
        select(func.count()).select_from(Like).where(Like.id_device == device.id_device)
    )
    like_count = like_count_result.scalar_one()
    user_like_result = await db.execute(
        select(Like)
        .where(Like.id_device == device.id_device)
        .where(Like.id_user == CURRENT_USER_ID)
    )
    is_liked = 1 if user_like_result.scalar_one_or_none() is not None else 0
    out = device_serializer(device)
    out["like_count"] = like_count
    out["is_liked"] = is_liked
    return out


@router.get("/device/draft")
async def get_draft(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Device)
        .where(Device.status == "черновик")
        .where(Device.id_user == CURRENT_USER_ID)
        .limit(1)
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        return None
    return device_serializer(device)


@router.get("/device")
@router.get("/device/{id_device}")
async def get_device(
    id_device: int | None = None,
    go_next: bool = Query(False, alias="next"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Device).where(Device.status == "опубликован").order_by(Device.id_device)
    result = await db.execute(stmt)
    pub = result.scalars().all()
    if not pub:
        return Response(status_code=404)

    if id_device is None:
        idx = 0
    else:
        idx = next((i for i, d in enumerate(pub) if d.id_device == id_device), None)
        if idx is None:
            return Response(status_code=404)

    if go_next:
        idx = (idx + 1) % len(pub)

    return await _feed_out(db, pub[idx])


@router.post("/device")
async def create_device(
    name: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Device)
        .where(Device.status == "черновик")
        .where(Device.id_user == CURRENT_USER_ID)
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return Response(status_code=500)

    image_url = upload_file(await image.read(), image.filename)
    video_url = upload_file(await video.read(), video.filename)

    device = Device(
        name=name,
        image_url=image_url,
        video_url=video_url,
        status="черновик",
        date_created=datetime.now(),
        id_user=CURRENT_USER_ID,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device_serializer(device)


@router.put("/device/{id_device}")
async def publish_device(
    id_device: int,
    power: float = Form(...),
    resistance: float = Form(...),
    description: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id_device == id_device))
    device = result.scalar_one_or_none()
    if device is None:
        return Response(status_code=404)
    if device.status != "черновик":
        return Response(status_code=500)
    if device.id_user != CURRENT_USER_ID:
        return Response(status_code=500)

    device.power = power
    device.resistance = resistance
    device.description = description
    device.status = "опубликован"
    device.date_formed = datetime.now()
    await db.commit()
    await db.refresh(device)
    return device_serializer(device)


@router.delete("/device/{id_device}")
async def delete_device(
    id_device: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id_device == id_device))
    device = result.scalar_one_or_none()
    if device is None:
        return Response(status_code=404)
    if device.id_user != CURRENT_USER_ID:
        return Response(status_code=500)
    if device.status == "удален":
        return Response(status_code=404)

    device.status = "удален"
    device.date_completed = datetime.now()
    await db.commit()
    return Response(status_code=200)


@router.post("/device/{id_device}")
async def like_device(
    id_device: int,
    like: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Like)
        .where(Like.id_user == CURRENT_USER_ID)
        .where(Like.id_device == id_device)
    )
    like_row = existing.scalar_one_or_none()

    if like == 1 and like_row is None:
        db.add(Like(id_user=CURRENT_USER_ID, id_device=id_device))
        await db.commit()
    elif like == 0 and like_row is not None:
        await db.delete(like_row)
        await db.commit()

    count_result = await db.execute(
        select(func.count()).select_from(Like).where(Like.id_device == id_device)
    )
    return {"like_count": count_result.scalar_one()}
