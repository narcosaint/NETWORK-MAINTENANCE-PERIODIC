import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, DateTime, Date, Float, CheckConstraint, UniqueConstraint, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Hotel(Base):
    __tablename__ = 'hotels'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    customer_name: Mapped[str | None] = mapped_column(String(200))
    maintenance_profile: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    __tablename__ = 'devices'
    __table_args__ = (CheckConstraint("device_type IN ('router', 'switch', 'ap')", name='ck_devices_type'),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotels.id', ondelete='RESTRICT'), index=True)
    name: Mapped[str] = mapped_column(String(200))
    device_type: Mapped[str] = mapped_column(String(20))
    serial_number: Mapped[str | None] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    mac_address: Mapped[str | None] = mapped_column(String(17))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (CheckConstraint("role IN ('technician', 'supervisor')", name='ck_users_role'),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(default=True)


class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Schedule(Base):
    __tablename__ = 'maintenance_schedules'
    __table_args__ = (
        UniqueConstraint('device_id', 'month', name='uq_schedule_device_month'),
        CheckConstraint("status IN ('pending', 'completed')", name='ck_schedule_status'),
        CheckConstraint('EXTRACT(DAY FROM month) = 1', name='ck_schedule_month').ddl_if(dialect='postgresql'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('devices.id', ondelete='RESTRICT'), index=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    month: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    notes: Mapped[str | None] = mapped_column(Text)


class Visit(Base):
    __tablename__ = 'visits'
    __table_args__ = (
        CheckConstraint("status IN ('assigned', 'in_progress', 'submitted', 'revision_requested', 'approved')", name='ck_visit_status'),
        CheckConstraint('version >= 1', name='ck_visit_version'),
        CheckConstraint("(status IN ('submitted', 'revision_requested', 'approved') AND checked_out_at IS NOT NULL AND pic_exception_reason IS NOT NULL) OR "
                        "(status IN ('assigned', 'in_progress') AND checked_out_at IS NULL)", name='ck_visit_checkout'),
        CheckConstraint("(status = 'assigned' AND checked_in_at IS NULL) OR "
                        "(status IN ('in_progress', 'submitted', 'revision_requested', 'approved') AND checked_in_at IS NOT NULL)", name='ck_visit_checkin'),
        CheckConstraint('(latitude IS NULL AND longitude IS NULL AND accuracy_m IS NULL) OR '
                        '(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 '
                        'AND accuracy_m >= 0 AND latitude IS NOT NULL AND longitude IS NOT NULL '
                        'AND accuracy_m IS NOT NULL)', name='ck_visit_coordinates'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('maintenance_schedules.id', ondelete='RESTRICT'), unique=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    status: Mapped[str] = mapped_column(String(20), default='assigned')
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    device_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    accuracy_m: Mapped[float | None] = mapped_column(Float)
    gps_exception_reason: Mapped[str | None] = mapped_column(Text)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('checklist_templates.id', ondelete='RESTRICT'))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkout_device_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkout_latitude: Mapped[float | None] = mapped_column(Float)
    checkout_longitude: Mapped[float | None] = mapped_column(Float)
    checkout_accuracy_m: Mapped[float | None] = mapped_column(Float)
    checkout_gps_exception_reason: Mapped[str | None] = mapped_column(Text)
    pic_exception_reason: Mapped[str | None] = mapped_column(Text)



class ChecklistTemplate(Base):
    """Immutable template revision: changes require a new template ID."""
    __tablename__ = 'checklist_templates'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    device_type: Mapped[str] = mapped_column(String(20))
    __table_args__ = (CheckConstraint("device_type IN ('router', 'switch', 'ap')", name='ck_template_device_type'),)


class ChecklistItem(Base):
    __tablename__ = 'checklist_items'
    __table_args__ = (UniqueConstraint('template_id', 'position', name='uq_checklist_position'),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('checklist_templates.id', ondelete='RESTRICT'), index=True)
    position: Mapped[int] = mapped_column()
    label: Mapped[str] = mapped_column(String(200))
    required: Mapped[bool] = mapped_column()


class ChecklistResult(Base):
    __tablename__ = 'checklist_results'
    __table_args__ = (
        UniqueConstraint('visit_id', 'item_id', name='uq_checklist_visit_item'),
        CheckConstraint("answer IN ('pass', 'fail', 'not_applicable')", name='ck_checklist_answer'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('visits.id', ondelete='RESTRICT'), index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('checklist_items.id', ondelete='RESTRICT'))
    answer: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)


class VisitEvent(Base):
    """Append-only workflow history with the exact evidence at each decision."""
    __tablename__ = 'visit_events'
    __table_args__ = (
        UniqueConstraint('visit_id', 'version', name='uq_visit_event_version'),
        CheckConstraint("action IN ('submitted', 'revision_requested', 'resubmitted', 'approved')", name='ck_visit_event_action'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('visits.id', ondelete='RESTRICT'), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    version: Mapped[int] = mapped_column()
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    snapshot: Mapped[dict] = mapped_column(JSON)


class HotelVisit(Base):
    __tablename__ = 'hotel_visits'
    __table_args__ = (
        CheckConstraint("status IN ('assigned', 'in_progress', 'submitted', 'revision_requested', 'approved')", name='ck_hotel_visit_status'),
        CheckConstraint('version >= 1', name='ck_hotel_visit_version'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotels.id', ondelete='RESTRICT'), index=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    planned_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default='assigned')
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    checkin: Mapped[dict | None] = mapped_column(JSON)
    checkout: Mapped[dict | None] = mapped_column(JSON)
    report: Mapped[dict] = mapped_column(JSON, default=dict)


class HotelVisitDevice(Base):
    __tablename__ = 'hotel_visit_devices'
    __table_args__ = (UniqueConstraint('visit_id', 'device_id', name='uq_hotel_visit_device'),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel_visits.id', ondelete='RESTRICT'), index=True)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('devices.id', ondelete='RESTRICT'))
    device_snapshot: Mapped[dict] = mapped_column(JSON)
    floor: Mapped[str | None] = mapped_column(String(100))
    point: Mapped[str | None] = mapped_column(String(200))
    result: Mapped[dict] = mapped_column(JSON, default=dict)


class DevicePhoto(Base):
    __tablename__ = 'device_photos'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel_visit_devices.id', ondelete='RESTRICT'), index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    object_key: Mapped[str] = mapped_column(String(50), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column()
    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()


class HotelVisitEvent(Base):
    __tablename__ = 'hotel_visit_events'
    __table_args__ = (UniqueConstraint('visit_id', 'version', name='uq_hotel_visit_event_version'),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel_visits.id', ondelete='RESTRICT'), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    version: Mapped[int] = mapped_column()
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    snapshot: Mapped[dict] = mapped_column(JSON)


class NetworkSpeedtest(Base):
    __tablename__ = 'network_speedtests'
    __table_args__ = (
        CheckConstraint("status IN ('running', 'completed', 'failed', 'aborted')", name='ck_speedtest_status'),
        CheckConstraint("band IN ('band_24', 'band_5')", name='ck_speedtest_band'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel_visit_devices.id', ondelete='RESTRICT'), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    band: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default='running')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
