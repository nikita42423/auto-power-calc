from datetime import datetime
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models.device import Device
from models.like import Like
from api.deps import CURRENT_USER_ID
from api.schemas import DeviceOut
from minio_client import upload_file

router = APIRouter(prefix="/api")


def _to_out(device: Device) -> dict:
    return {
        "id_device": device.id_device,
        "name": device.name,
        "description": device.description,
        "status": device.status,
        "image_url": device.image_url,
        "video_url": device.video_url,
        "power": device.power,
        "resistance": device.resistance,
        "date_created": device.date_created,
        "id_user": device.id_user,
        "is_creator": 1 if device.id_user == CURRENT_USER_ID else 0,
    }


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
    return [_to_out(d) for d in devices]


@router.get("/device/{id_device}")
async def get_device(
    id_device: int,
    next: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Device).where(Device.status == "опубликован").order_by(Device.id_device)
    result = await db.execute(stmt)
    pub = result.scalars().all()
    if not pub:
        return {"error": "no devices"}

    idx = next((i for i, d in enumerate(pub) if d.id_device == id_device), None)
    if idx is None:
        return {"error": "not found"}

    if next:
        idx = (idx + 1) % len(pub)

    device = pub[idx]
    like_count_result = await db.execute(
        select(func.count()).select_from(Like).where(Like.id_device == device.id_device)
    )
    like_count = like_count_result.scalar_one()
    out = _to_out(device)
    out["like_count"] = like_count
    return out


@router.get("/device")
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
    return _to_out(device)


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
        return {"error": "draft already exists"}

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
    return _to_out(device)


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
        return {"error": "not found"}
    if device.status != "черновик":
        return {"error": f"cannot publish from status '{device.status}'"}
    if device.id_user != CURRENT_USER_ID:
        return {"error": "not your device"}

    device.power = power
    device.resistance = resistance
    device.description = description
    device.status = "опубликован"
    device.date_formed = datetime.now()
    await db.commit()
    await db.refresh(device)
    return _to_out(device)


@router.delete("/device/{id_device}")
async def delete_device(
    id_device: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id_device == id_device))
    device = result.scalar_one_or_none()
    if device is None:
        return {"error": "not found"}
    if device.id_user != CURRENT_USER_ID:
        return {"error": "not your device"}
    if device.status == "удален":
        return {"error": "already deleted"}

    device.status = "удален"
    device.date_completed = datetime.now()
    await db.commit()
    return {"status": "ok"}


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