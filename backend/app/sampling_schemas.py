from datetime import datetime
from uuid import UUID, uuid4
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class FloorCreate(StrictInput):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=100)
    position: int = Field(ge=0)
    default_sampling_count: int = Field(default=4, gt=0)


class FloorPatch(StrictInput):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    position: int | None = Field(default=None, ge=0)
    default_sampling_count: int | None = Field(default=None, gt=0)
    archived: bool | None = None

    @field_validator('name', 'position', 'default_sampling_count', 'archived')
    @classmethod
    def nonnull(cls, value):
        if value is None:
            raise ValueError('Field cannot be null')
        return value


class PointCreate(StrictInput):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=4000)
    position: int = Field(ge=0)
    device_id: UUID | None = None


class PointPatch(StrictInput):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=4000)
    position: int | None = Field(default=None, ge=0)
    device_id: UUID | None = None
    archived: bool | None = None

    @field_validator('name', 'position', 'archived')
    @classmethod
    def nonnull(cls, value):
        return FloorPatch.nonnull(value)


class FloorOutput(FloorCreate):
    model_config = ConfigDict(from_attributes=True)
    hotel_id: UUID
    version: int
    created_at: datetime
    archived_at: datetime | None


class PointOutput(PointCreate):
    model_config = ConfigDict(from_attributes=True)
    floor_id: UUID
    version: int
    created_at: datetime
    archived_at: datetime | None


class ReviewedPoint(StrictInput):
    id: UUID
    version: int = Field(ge=1)


class ReviewedFloor(ReviewedPoint):
    points: list[ReviewedPoint]


class PhotoPolicy(StrictInput):
    sampling_categories: list[Literal['ap', 'device', 'area', 'finding']]
    infrastructure_categories: list[Literal['router', 'switch', 'rack', 'backbone', 'ap', 'cable', 'finding']]


class CoverageCreate(StrictInput):
    expected_version: int = Field(ge=1)
    floors: list[ReviewedFloor] = Field(min_length=1)
    photo_policy: PhotoPolicy
