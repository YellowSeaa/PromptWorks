from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

TimeoutSecondsType = Annotated[int, Field(ge=1, le=600)]


class TestingTimeoutsBase(BaseModel):
    quick_test_timeout: TimeoutSecondsType = Field(
        ...,
        description="快速测试的超时时间，单位：秒",
    )
    test_task_timeout: TimeoutSecondsType = Field(
        ...,
        description="测试任务的超时时间，单位：秒",
    )


class TestingTimeoutsUpdate(TestingTimeoutsBase):
    """更新快速测试/测试任务超时配置的请求体。"""


class TestingTimeoutsRead(TestingTimeoutsBase):
    """返回快速测试/测试任务超时配置的响应体。"""

    updated_at: datetime | None = Field(
        default=None,
        description="配置最近更新时间，若尚未设置则为空",
    )


__all__ = [
    "TestingTimeoutsRead",
    "TestingTimeoutsUpdate",
]
