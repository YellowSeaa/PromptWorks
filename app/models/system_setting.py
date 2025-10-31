from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import JSONBCompat
from app.models.base import Base


class SystemSetting(Base):
    """存储全局配置项的键值对。"""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(120),
        primary_key=True,
        doc="配置项唯一标识",
    )
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        doc="配置项内容，统一使用 JSON 结构存储",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="配置项说明",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="最近更新时间",
    )


__all__ = ["SystemSetting"]
