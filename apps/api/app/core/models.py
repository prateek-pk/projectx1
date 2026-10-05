from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Uuid, DateTime, FetchedValue, text
from uuid import UUID, uuid7
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    auth_user_id : Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    name : Mapped[str]
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    name : Mapped[str]
    slug : Mapped[str] = mapped_column(unique=True, nullable=False)
    type : Mapped[str | None] = mapped_column(nullable=True)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())