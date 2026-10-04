from datetime import datetime
from decimal import Decimal

from fastapi import FastAPI, APIRouter, Request, Query, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models.device import Device
from models.like import Like
from models.user import User



router = APIRouter()
templates = Jinja2Templates(directory="templates")

def fmt_num(value):
    if value is None:
        return ""
    s = f"{value:.10f}".rstrip("0").rstrip(".")
    return s

templates.env.filters["fmt_num"] = fmt_num

CURRENT_USER_ID = 1


@router.get("/feed")
@router.get("/feed/{id_device}")
async def get_feed(
    request: Request,
    id_device: int | None = None,
    par_next: str | None = Query(None, alias="next"),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Device)
        .where(Device.status == "опубликован")
        .order_by(Device.id_device)
    )
    result = await db.execute(stmt)
    pub = result.scalars().all()

    if not pub:
        return RedirectResponse("/grid")

    if id_device is None:
        device = pub[0]
    else:
        device = next((d for d in pub if d.id_device == id_device), None)

    if device is None:
        return RedirectResponse("/grid")

    idx = None
    if id_device is None:
        idx = 0
    else:
        idx = next((i for i, d in enumerate(pub) if d.id_device == id_device), None)

    if idx is None:
        return RedirectResponse("/grid")

    if par_next == "true":
            idx = (idx + 1) % len(pub)

    device = pub[idx]
    like_count_result = await db.execute(
        select(func.count())
        .select_from(Like)
        .where(Like.id_device == device.id_device)
    )
    like_count = like_count_result.scalar_one()
    next_id = pub[(idx + 1) % len(pub)].id_device

    return templates.TemplateResponse(
        request=request,
        name="feed.html",
        context={
            "device": device,
            "next_id": next_id,
            "like_count": like_count,
        }
    )

@router.get("/add")
async def get_add(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Device)
        .where(Device.status == "черновик")
        .where(Device.id_user == CURRENT_USER_ID)
        .limit(1)
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={
            "device": device,
            "has_draft": device is not None,
        },
    )

@router.get("/grid")
async def get_devices(
    request: Request,
    power_min: int | None = Query(None),
    power_max: int | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Device)
        .where(Device.status == "опубликован")
    )

    if power_min is not None:
        stmt = stmt.where(Device.power >= power_min)
    if power_max is not None:
        stmt = stmt.where(Device.power <= power_max)

    result = await db.execute(stmt)
    devices = result.scalars().all()

    if devices:
        ids = [d.id_device for d in devices]
        counts_result = await db.execute(
            select(Like.id_device, func.count())
            .where(Like.id_device.in_(ids))
            .group_by(Like.id_device)
        )
        like_counts = dict(counts_result.all())
    else:
        like_counts = {}

    return templates.TemplateResponse(
        request=request,
        name="grid.html",
        context={
            "devices": devices,
            "like_counts": like_counts,
            "power_min": power_min or 0,
            "power_max": power_max or 2000,
        }
    )

@router.post("/add")
async def post_add(
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Device)
        .where(Device.status == "черновик")
        .where(Device.id_user == CURRENT_USER_ID)
        .limit(1)
    )

    if existing.scalar_one_or_none() is not None:
        return RedirectResponse("/add", status_code=303)

    device = Device(
        name=name,
        image_url="/static/img/default.png",
        video_url="/static/video/default.mp4",
        power=None,
        resistance=None,
        description=None,
        status="черновик",
        date_created=datetime.now(),
        id_user=CURRENT_USER_ID,
    )
    db.add(device)
    await db.commit()

    return RedirectResponse("/add", status_code=303)

@router.post("/publish")
async def post_publish(
    request: Request,
    power: Decimal = Form(...),
    resistance: Decimal = Form(...),
    description: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Device)
        .where(Device.status == "черновик")
        .where(Device.id_user == CURRENT_USER_ID)
        .limit(1)
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if device is None:
        return RedirectResponse("/add", status_code=303)

    device.power = power
    device.resistance = resistance
    device.description = description
    device.status = "опубликован"
    device.date_formed = datetime.now()
    await db.commit()

    return RedirectResponse("/feed", status_code=303)

@router.post("/device/{id_device}/delete")
async def delete_device(id_device: int, db: AsyncSession = Depends(get_db)):
    update_query = """
        UPDATE devices
        SET status = 'удален'
        WHERE id_device = :id_device
    """

    await db.execute(text(update_query), {"id_device": id_device})
    await db.commit()

    return RedirectResponse(url="/feed", status_code=303)
