from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Text
from db.base import Base

class Device(Base):
    __tablename__ = "devices"

    id_device = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(9), nullable=False)
    image_url = Column(String(255), nullable=False)
    video_url = Column(String(255), nullable=False)
    power = Column(Numeric(6,2), nullable=True)
    resistance = Column(Numeric(6,3), nullable=True)
    date_created = Column(DateTime, nullable=False)
    creator = Column(String(50), nullable=False)
    date_formed = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False) # Поле для мягкого удаления
