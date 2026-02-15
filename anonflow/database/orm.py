from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func
)
from sqlalchemy.orm import relationship

from .base import Base


class Ban(Base):
    __tablename__ = "bans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    is_active = Column(Boolean, nullable=False, default=True)

    banned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    unbanned_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    banned_by = Column(Integer, ForeignKey("moderators.user_id"))
    unbanned_by = Column(Integer, ForeignKey("moderators.user_id"))

    user = relationship("User", back_populates="bans")

class Moderator(Base):
    __tablename__ = "moderators"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)

    can_approve_posts = Column(Boolean, nullable=False, default=True)
    can_manage_bans = Column(Boolean, nullable=False, default=False)
    can_manage_moderators = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="moderator")

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    language = Column(String(2), default="ru")

    moderator = relationship(
        "Moderator",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )
    bans = relationship(
        "Ban",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Ban.banned_at.desc()"
    )
