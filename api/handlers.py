from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from data.collections import devices_db


router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/grid")
def get_devices(request: Request, power_min: int = Query(None), power_max: int = Query(None)):
    devices = [{**d, "like_count": len(d["likes"])} for d in devices_db if d["status"] == "опубликован"]

    if power_min is not None:
        devices = [d for d in devices if d["power"] >= power_min]
    if power_max is not None:
        devices = [d for d in devices if d["power"] <= power_max]

    return templates.TemplateResponse(
        request=request,
        name="grid.html",
        context={"devices": devices, "power_min": power_min or 0, "power_max": power_max or 2000}
    )

@router.get("/feed")
@router.get("/feed/{device_id}")
def get_feed(request: Request, device_id: int = None, par_next: str = Query(None, alias="next")):
    pub = [d for d in devices_db if d["status"] == "опубликован"]

    if device_id is None:
        device = pub[0] if pub else None
    else:
        device = next(
            (d for d in devices_db if d["id"] == device_id and d["status"] == "опубликован"),
            None,
        )

    if not pub or device is None:
        return RedirectResponse("/grid")

    idx = pub.index(device)
    if par_next == "true":
        idx = (idx + 1) % len(pub)

    device = {**pub[idx], "like_count": len(pub[idx]["likes"])}
    next_id = pub[(idx + 1) % len(pub)]["id"]

    return templates.TemplateResponse(
        request=request,
        name="feed.html",
        context={"device": device, "next_id": next_id}
    )

@router.get("/add")
def get_add(request: Request):
    device = next((d for d in devices_db if d["status"] == "черновик"), None)

    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={"device": device}
    )
