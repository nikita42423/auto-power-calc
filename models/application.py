from sqlalchemy import Column, Integer, ForeignKey
from db.base import Base

class Applications(Base):
    __tablename__ = "applications"

    id_user = Column(Integer, ForeignKey("users.id_user"), primary_key=True)
    id_device = Column(Integer, ForeignKey("devices.id_device"), primary_key=True)
