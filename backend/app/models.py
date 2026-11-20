import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, ForeignKeyConstraint, DateTime, Date, Float, CheckConstraint, UniqueConstraint, JSON, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB
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
    contact_profile: Mapped[dict | None] = mapped_column(JSON)


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
        CheckConstraint('(visit_device_id IS NOT NULL AND sampling_session_id IS NULL) OR (visit_device_id IS NULL AND sampling_session_id IS NOT NULL)', name='ck_speedtest_one_scope'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sampling_session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('sampling_sessions.id', ondelete='RESTRICT'), index=True)
    visit_device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('hotel_visit_devices.id', ondelete='RESTRICT'), index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    band: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default='running')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


class HotelFloor(Base):
    __tablename__ = 'hotel_floors'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotels.id', ondelete='RESTRICT'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column()
    default_sampling_count: Mapped[int] = mapped_column(server_default='4')
    version: Mapped[int] = mapped_column(server_default='1')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("trim(name) <> ''", name='ck_floor_name'),
        CheckConstraint('position >= 0', name='ck_floor_position'),
        CheckConstraint('default_sampling_count > 0', name='ck_floor_target'),
        CheckConstraint('version >= 1', name='ck_floor_version'),
        Index('uq_hotel_floors_active_name', hotel_id, func.lower(func.trim(name)), unique=True,
              postgresql_where=text('archived_at IS NULL'), sqlite_where=text('archived_at IS NULL')),
        Index('ix_hotel_floors_active_order', hotel_id, position, id,
              postgresql_where=text('archived_at IS NULL'), sqlite_where=text('archived_at IS NULL')),
    )


class SamplingPoint(Base):
    __tablename__ = 'sampling_points'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    floor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel_floors.id', ondelete='RESTRICT'), index=True)
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column()
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('devices.id', ondelete='RESTRICT'), index=True)
    version: Mapped[int] = mapped_column(server_default='1')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("trim(name) <> ''", name='ck_point_name'),
        CheckConstraint('position >= 0', name='ck_point_position'),
        CheckConstraint('version >= 1', name='ck_point_version'),
        Index('uq_sampling_points_active_name', floor_id, func.lower(func.trim(name)), unique=True,
              postgresql_where=text('archived_at IS NULL'), sqlite_where=text('archived_at IS NULL')),
        Index('ix_sampling_points_active_order', floor_id, position, id,
              postgresql_where=text('archived_at IS NULL'), sqlite_where=text('archived_at IS NULL')),
    )


class SamplingCoverage(Base):
    __tablename__ = 'sampling_coverages'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel_visits.id', ondelete='RESTRICT'))
    period: Mapped[date] = mapped_column(Date)
    hotel_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'))
    photo_policy_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'))
    schema_version: Mapped[int] = mapped_column(server_default='1')
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint('hotel_visit_id', name='uq_coverage_visit'),
        CheckConstraint('EXTRACT(DAY FROM period) = 1', name='ck_coverage_period').ddl_if(dialect='postgresql'),
        CheckConstraint('schema_version = 1', name='ck_coverage_schema_version'),
    )


class SamplingCoverageFloor(Base):
    __tablename__ = 'sampling_coverage_floors'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    coverage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sampling_coverages.id', ondelete='RESTRICT'))
    floor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel_floors.id', ondelete='RESTRICT'), index=True)
    name_snapshot: Mapped[str] = mapped_column(String(100))
    position_snapshot: Mapped[int] = mapped_column()
    target_count: Mapped[int] = mapped_column()
    __table_args__ = (
        UniqueConstraint('coverage_id', 'floor_id', name='uq_coverage_floor'),
        UniqueConstraint('id', 'coverage_id', name='uq_coverage_floor_scope'),
        CheckConstraint("trim(name_snapshot) <> ''", name='ck_coverage_floor_name'),
        CheckConstraint('position_snapshot >= 0', name='ck_coverage_floor_position'),
        CheckConstraint('target_count > 0', name='ck_coverage_floor_target'),
    )


class SamplingSession(Base):
    __tablename__ = 'sampling_sessions'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    coverage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sampling_coverages.id', ondelete='RESTRICT'))
    coverage_floor_id: Mapped[uuid.UUID] = mapped_column()
    sampling_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sampling_points.id', ondelete='RESTRICT'), index=True)
    point_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'))
    position_snapshot: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), server_default='untested')
    version: Mapped[int] = mapped_column(server_default='1')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(['coverage_floor_id', 'coverage_id'],
            ['sampling_coverage_floors.id', 'sampling_coverage_floors.coverage_id'],
            name='fk_session_coverage_floor', ondelete='RESTRICT'),
        UniqueConstraint('coverage_id', 'sampling_point_id', name='uq_session_point'),
        CheckConstraint('position_snapshot >= 0', name='ck_session_position'),
        CheckConstraint('version >= 1', name='ck_session_version'),
        CheckConstraint("status IN ('untested', 'good', 'attention', 'problem')", name='ck_session_status'),
        Index('ix_sampling_sessions_coverage_floor_id_coverage_id', 'coverage_floor_id', 'coverage_id'),
        Index('ix_sampling_sessions_coverage_id_status', 'coverage_id', 'status'),
    )


class SamplingObservation(Base):
    """Append-only client observation; a reported source is not radio attestation."""
    __tablename__ = 'sampling_observations'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sampling_sessions.id', ondelete='RESTRICT'))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    session_version: Mapped[int] = mapped_column()
    visit_version: Mapped[int] = mapped_column()
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'))
    __table_args__ = (
        UniqueConstraint('session_id', 'session_version', name='uq_observation_session_version'),
        CheckConstraint('session_version >= 2', name='ck_observation_session_version'),
        CheckConstraint('visit_version >= 1', name='ck_observation_visit_version'),
    )


class SamplingSpeedtestAttempt(Base):
    __tablename__ = 'sampling_speedtest_attempts'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sampling_sessions.id', ondelete='RESTRICT'), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('network_speedtests.id', ondelete='RESTRICT'), unique=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    failure_reason: Mapped[str | None] = mapped_column(Text)
    request_payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), 'postgresql'))
    __table_args__ = (CheckConstraint(
        "(run_id IS NOT NULL AND failure_reason IS NULL) OR "
        "(run_id IS NULL AND failure_reason IS NOT NULL AND length(trim(failure_reason)) > 0)",
        name='ck_sampling_speedtest_evidence'),)
