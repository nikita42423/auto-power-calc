from sqlalchemy import Column, Integer, ForeignKey
from db.base import Base

class Like(Base):
    __tablename__ = "likes"

    id_user = Column(Integer, ForeignKey("users.id_user"), primary_key=True)
    id_device = Column(Integer, ForeignKey("devices.id_device"), primary_key=True)
