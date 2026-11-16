from datetime import date, datetime
from app.site_profile import SiteMaintenanceProfile
from ipaddress import ip_address
import re
from typing import Literal, Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints, Field, AwareDatetime, field_validator, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Username = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, pattern=r'^[a-z0-9_.-]{3,100}$')]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
Notes = Annotated[str, StringConstraints(max_length=5000)]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

class HotelInput(Input):
    name: Name
    address: Notes | None = None
    customer_name: Name | None = None
    maintenance_profile: SiteMaintenanceProfile | None = None

class HotelOutput(HotelInput):
    id: UUID
    created_at: datetime

class DeviceInput(Input):
    hotel_id: UUID
    name: Name
    device_type: Literal['router', 'switch', 'ap']
    serial_number: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None

    brand: Annotated[str, StringConstraints(max_length=100)] | None = None
    model: Annotated[str, StringConstraints(max_length=100)] | None = None
    location: Annotated[str, StringConstraints(max_length=200)] | None = None
    ip_address: Annotated[str, StringConstraints(max_length=45)] | None = None
    mac_address: Annotated[str, StringConstraints(max_length=17)] | None = None
    notes: Notes | None = None

    @field_validator('brand', 'model', 'location', 'ip_address', 'mac_address', 'notes', mode='before')
    @classmethod
    def trim_optional_details(cls, value):
        return (value.strip() or None) if isinstance(value, str) else value

    @field_validator('ip_address')
    @classmethod
    def valid_ip(cls, value):
        if value is None:
            return None
        if '%' in value:
            raise ValueError('Use an IPv4 or IPv6 address without a zone identifier')
        return str(ip_address(value))

    @field_validator('mac_address')
    @classmethod
    def valid_mac(cls, value):
        if value is None:
            return None
        value = value.replace('-', ':').lower()
        if not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', value):
            raise ValueError('Use six hexadecimal pairs, for example aa:bb:cc:dd:ee:ff')
        return value


class DeviceOutput(DeviceInput):
    id: UUID
    created_at: datetime

class UserInput(Input):
    username: Username
    name: Name
    role: Literal['technician', 'supervisor']
    active: bool = True

class UserCreate(UserInput):
    password: Password

class UserUpdate(UserInput):
    password: Password | None = None

class UserOutput(UserInput):
    id: UUID

class Login(Input):
    username: Username
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]

class ScheduleInput(Input):
    device_id: UUID
    technician_id: UUID
    month: date
    status: Literal['pending', 'completed'] = 'pending'
    notes: Notes | None = None

    @field_validator('month')
    @classmethod
    def first_day(cls, value):
        if value.day != 1:
            raise ValueError('month must be the first day of the month')
        return value

class ScheduleOutput(ScheduleInput):
    id: UUID

class Progress(Input):
    status: Literal['pending', 'completed']
    notes: Notes | None = None


class VisitCreate(Input):
    schedule_id: UUID
    template_id: UUID | None = None


class CheckIn(Input):
    expected_version: int = Field(ge=1, strict=True)
    device_time: AwareDatetime
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    gps_exception_reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)] | None = None

    @model_validator(mode='after')
    def coordinates_or_reason(self):
        present = [value is not None for value in (self.latitude, self.longitude, self.accuracy_m)]
        if any(present) and not all(present):
            raise ValueError('Provide latitude, longitude and accuracy together')
        if all(present) == (self.gps_exception_reason is not None):
            raise ValueError('Provide either GPS coordinates or a GPS exception reason')
        return self


class VisitOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    schedule_id: UUID
    technician_id: UUID
    status: Literal['assigned', 'in_progress', 'submitted', 'revision_requested', 'approved']
    version: int
    created_at: datetime
    checked_in_at: datetime | None
    device_time: datetime | None
    latitude: float | None
    longitude: float | None
    accuracy_m: float | None
    gps_exception_reason: str | None

    template_id: UUID | None
    checked_out_at: datetime | None
    checkout_device_time: datetime | None
    checkout_latitude: float | None
    checkout_longitude: float | None
    checkout_accuracy_m: float | None
    checkout_gps_exception_reason: str | None
    pic_exception_reason: str | None


class TemplateItemInput(Input):
    label: Name
    required: bool = True


class TemplateCreate(Input):
    name: Name
    device_type: Literal['router', 'switch', 'ap']
    items: list[TemplateItemInput] = Field(min_length=1, max_length=100)


class TemplateItemOutput(TemplateItemInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    position: int


class TemplateOutput(BaseModel):
    id: UUID
    name: str
    device_type: str
    items: list[TemplateItemOutput]


class ChecklistAnswer(Input):
    item_id: UUID
    answer: Literal['pass', 'fail', 'not_applicable']
    notes: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)] | None = None

    @model_validator(mode='after')
    def explain_failure(self):
        if self.answer != 'pass' and not self.notes:
            raise ValueError('Failure or not-applicable requires a reason/action note')
        return self


class ChecklistSave(Input):
    expected_version: int = Field(ge=1, strict=True)
    answers: list[ChecklistAnswer] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_items(self):
        if len({a.item_id for a in self.answers}) != len(self.answers):
            raise ValueError('Duplicate checklist item')
        return self


class CheckOut(CheckIn):
    pic_exception_reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class VisitTemplate(Input):
    expected_version: int = Field(ge=1, strict=True)
    template_id: UUID


class VisitVersion(Input):
    expected_version: int = Field(ge=1, strict=True)


class VisitReview(VisitVersion):
    decision: Literal['revision_requested', 'approved']
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class VisitEventOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    visit_id: UUID
    actor_id: UUID
    version: int
    action: Literal['submitted', 'revision_requested', 'resubmitted', 'approved']
    reason: str | None
    created_at: datetime
    snapshot: dict
