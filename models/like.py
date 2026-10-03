from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from db.base import Base

class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("id_user", "id_device"),)

    id_like = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"), nullable=False)
    id_device = Column(Integer, ForeignKey("devices.id_device"), nullable=False)
