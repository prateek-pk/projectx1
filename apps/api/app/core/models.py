from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Uuid, DateTime, FetchedValue, text, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from uuid import UUID, uuid7
from datetime import datetime
import json

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

class Membership(Base):
    __tablename__ = "memberships"

    __table_args__ = (UniqueConstraint("user_id", "workspace_id", name="uq_membership_user_workspace"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    user_id : Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id : Mapped[UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    role : Mapped[str] = mapped_column(nullable=False)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())

class Capability(Base):
    __tablename__ = "capabilities"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    key : Mapped[str] = mapped_column(unique=True, nullable=False)
    name : Mapped[str] = mapped_column(nullable=False)
    description : Mapped[str | None] = mapped_column(Text, nullable=True)
    version : Mapped [int] = mapped_column(nullable=False, server_default=text("1"))
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())

class WorkspaceCapability(Base):
    __tablename__ = "workspace_capabilities"

    __table_args__ = (UniqueConstraint("workspace_id", "capability_id", name="uq_workspace_capability"), Index("ix_workspace_capabilities_capability_id_workspace_id", "capability_id", "workspace_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    workspace_id : Mapped[UUID] = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    capability_id : Mapped[UUID] = mapped_column(Uuid, ForeignKey("capabilities.id", ondelete="RESTRICT"), nullable=False)
    enabled : Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    configuration : Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=FetchedValue())