from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

class DeviceOut(BaseModel):
    id_device: int
    name: str
    description: str | None
    status: str
    image_url: str
    video_url: str
    power: Decimal | None
    resistance: Decimal | None
    date_created: datetime
    id_user: int
    is_creator: int

    class Config:
        from_attributes = True