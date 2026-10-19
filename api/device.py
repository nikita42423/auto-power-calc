from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_optional_user
from api.serializers import device_serializer
from db.session import get_db
from minio_client import upload_file
from models.device import Device
from models.like import Like
from models.user import User

router = APIRouter(prefix="/api/devices", tags=["Услуги"])

DEVICE_NOT_FOUND = "Устройство не найдено"
NOT_OWNER = "Нет прав: устройство принадлежит другому пользователю"
NOT_DRAFT = "Устройство уже опубликовано или удалено"


@router.get(
    "",
    summary="Список опубликованных услуг (с фильтром)",
    description=(
        "Публичный метод: возвращает все опубликованные устройства "
        "с фильтрацией по мощности (power_min/power_max). "
        "Доступно без авторизации. Если пользователь аутентифицирован, "
        "в ответ входит is_creator; для гостя is_creator=0."
    ),
    responses={
        200: {"description": "Список опубликованных устройств"},
    },
)
async def get_devices(
    power_min: int | None = Query(None, description="Минимальная мощность, Вт"),
    power_max: int | None = Query(None, description="Максимальная мощность, Вт"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    stmt = select(Device).where(Device.status == "опубликован")
    if power_min is not None:
        stmt = stmt.where(Device.power >= power_min)
    if power_max is not None:
        stmt = stmt.where(Device.power <= power_max)
    result = await db.execute(stmt)
    devices = result.scalars().all()
    user_id = current_user.id_user if current_user else None
    return [
        {**device_serializer(d), "is_creator": 1 if d.id_user == user_id else 0}
        for d in devices
    ]


async def _feed_out(db: AsyncSession, device: Device, user: User | None) -> dict:
    like_count_result = await db.execute(
        select(func.count()).select_from(Like).where(Like.id_device == device.id_device)
    )
    like_count = like_count_result.scalar_one()
    is_liked = 0
    if user is not None:
        user_like_result = await db.execute(
            select(Like)
            .where(Like.id_device == device.id_device)
            .where(Like.id_user == user.id_user)
        )
        is_liked = 1 if user_like_result.scalar_one_or_none() is not None else 0
    out = device_serializer(device)
    out["like_count"] = like_count
    out["is_liked"] = is_liked
    return out


@router.get(
    "/feed",
    summary="Лента: устройство по id / следующее / первое",
    description=(
        "Публичный метод ленты: без id — первое опубликованное устройство; "
        "с id_device — это устройство; с next=true — следующее опубликованное (по кругу). "
        "В ответ входят like_count и is_liked. Доступно без авторизации."
    ),
    responses={
        200: {"description": "Элемент ленты"},
        404: {"description": "Устройство не найдено или нет опубликованных"},
    },
)
async def get_feed(
    id_device: int | None = Query(None, description="Id устройства ленты"),
    go_next: bool = Query(False, alias="next", description="Взять следующее устройство ленты"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    stmt = select(Device).where(Device.status == "опубликован").order_by(Device.id_device)
    result = await db.execute(stmt)
    pub = result.scalars().all()
    if not pub:
        raise HTTPException(status_code=404, detail="Нет опубликованных устройств")

    if id_device is None:
        idx = 0
    else:
        idx = next((i for i, d in enumerate(pub) if d.id_device == id_device), None)
        if idx is None:
            raise HTTPException(status_code=404, detail=DEVICE_NOT_FOUND)

    if go_next:
        idx = (idx + 1) % len(pub)

    return await _feed_out(db, pub[idx], current_user)


@router.get(
    "/draft",
    summary="Поля черновика текущего пользователя",
    description=(
        "Метод создателя: возвращает черновик (status=черновик) "
        "текущего аутентифицированного пользователя или null. "
        "Требуется cookie-авторизация; для гостя — 401."
    ),
    responses={
        200: {"description": "Черновик устройства или null, если черновика нет"},
        401: {"description": "Не аутентифицирован"},
    },
)
async def get_draft(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Device)
        .where(Device.status == "черновик")
        .where(Device.id_user == current_user.id_user)
        .limit(1)
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        return None
    return device_serializer(device)


@router.post(
    "",
    summary="Добавить услугу (создание черновика с картинкой и видео)",
    description=(
        "Метод создателя: создаёт устройство со статусом «черновик», "
        "загружает image и video в MinIO. "
        "Пользователь (id_user) автоматически берётся из cookie-сессии. "
        "У одного пользователя может быть только один черновик (иначе 409). "
        "Требуется авторизация; для гостя — 401."
    ),
    responses={
        200: {"description": "Черновик создан"},
        401: {"description": "Не аутентифицирован"},
        409: {"description": "У пользователя уже есть черновик"},
    },
)
async def create_device(
    name: str = Form(..., description="Название услуги"),
    image: UploadFile = File(..., description="Изображение устройства"),
    video: UploadFile = File(..., description="Видео устройства"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(Device)
        .where(Device.status == "черновик")
        .where(Device.id_user == current_user.id_user)
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Черновик уже существует")

    image_url = upload_file(await image.read(), image.filename)
    video_url = upload_file(await video.read(), video.filename)

    device = Device(
        name=name,
        image_url=image_url,
        video_url=video_url,
        status="черновик",
        date_created=datetime.now(),
        id_user=current_user.id_user,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device_serializer(device)


@router.put(
    "/{id_device}",
    summary="Опубликовать услугу",
    description=(
        "Метод создателя: заполняет power/resistance/description и переводит "
        "устройство из «черновик» в «опубликован». "
        "Гость — 401; чужое устройство — 403; уже опубликовано/удалено — 409."
    ),
    responses={
        200: {"description": "Устройство опубликовано"},
        401: {"description": "Не аутентифицирован"},
        403: {"description": "Нет прав на публикацию"},
        404: {"description": DEVICE_NOT_FOUND},
        409: {"description": NOT_DRAFT},
    },
)
async def publish_device(
    id_device: int,
    power: float = Form(..., description="Мощность, Вт"),
    resistance: float = Form(..., description="Сопротивление, Ом"),
    description: str = Form(..., description="Описание услуги"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Device).where(Device.id_device == id_device))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail=DEVICE_NOT_FOUND)
    if device.status != "черновик":
        raise HTTPException(status_code=409, detail=NOT_DRAFT)
    if device.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail=NOT_OWNER)

    device.power = power
    device.resistance = resistance
    device.description = description
    device.status = "опубликован"
    device.date_formed = datetime.now()
    await db.commit()
    await db.refresh(device)
    return device_serializer(device)


@router.delete(
    "/{id_device}",
    summary="Удалить услугу (мягкое удаление)",
    description=(
        "Метод создателя: переводит устройство в статус «удален». "
        "Гость — 401; чужое устройство — 403; отсутствует/удалено — 404."
    ),
    responses={
        200: {"description": "Устройство удалено"},
        401: {"description": "Не аутентифицирован"},
        403: {"description": "Нет прав на удаление"},
        404: {"description": DEVICE_NOT_FOUND},
    },
)
async def delete_device(
    id_device: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Device).where(Device.id_device == id_device))
    device = result.scalar_one_or_none()
    if device is None or device.status == "удален":
        raise HTTPException(status_code=404, detail=DEVICE_NOT_FOUND)
    if device.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail=NOT_OWNER)

    device.status = "удален"
    device.date_completed = datetime.now()
    await db.commit()
    return {"message": "Устройство удалено"}


@router.post(
    "/{id_device}/likes",
    summary="Поставить/снять лайк",
    description=(
        "Метод аутентифицированного пользователя: like=1 — поставить лайк, "
        "like=0 — снять. Возвращает актуальный like_count. "
        "Требуется авторизация; для гостя — 401."
    ),
    responses={
        200: {"description": "Актуальное количество лайков"},
        401: {"description": "Не аутентифицирован"},
    },
)
async def like_device(
    id_device: int,
    like: int = Form(..., description="1 — поставить лайк, 0 — снять"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(Like)
        .where(Like.id_user == current_user.id_user)
        .where(Like.id_device == id_device)
    )
    like_row = existing.scalar_one_or_none()

    if like == 1 and like_row is None:
        db.add(Like(id_user=current_user.id_user, id_device=id_device))
        await db.commit()
    elif like == 0 and like_row is not None:
        await db.delete(like_row)
        await db.commit()

    count_result = await db.execute(
        select(func.count()).select_from(Like).where(Like.id_device == id_device)
    )
    return {"like_count": count_result.scalar_one()}
