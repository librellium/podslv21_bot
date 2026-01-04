from sqlalchemy import Boolean, Column, Integer, String

from .base import Base


class User(Base):
    __tablename__ = "users"

    chat_id = Column(Integer, primary_key=True)
    is_blocked = Column(Boolean, default=False)
    language = Column(String(2), default="ru")
