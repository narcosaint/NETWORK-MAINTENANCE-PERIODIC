from datetime import date, datetime
from app.site_profile import SiteMaintenanceProfile
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StringConstraints, model_validator
from app.schemas import Input, VisitVersion, CheckIn, Notes, Name

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Number = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class HotelVisitCreate(Input):
    hotel_id: UUID
    technician_id: UUID
    planned_date: date


class SampleCreate(VisitVersion):
    device_id: UUID
    floor: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    point: Short


class BandResult(Input):
    status: Literal['measured', 'unavailable', 'not_tested'] = 'not_tested'
    signal_dbm: float | None = Field(default=None, ge=-150, le=0, allow_inf_nan=False)
    channel: int | None = Field(default=None, ge=1, le=233, strict=True)
    bandwidth_mbps: Number | None = None
    ssid: Annotated[str, StringConstraints(max_length=32)] | None = None
    bssid: Annotated[str, StringConstraints(max_length=17)] | None = None
    reason: Reason | None = None
    source: Literal['manual'] = 'manual'

    @model_validator(mode='after')
    def honest_measurement(self):
        values=(self.signal_dbm,self.channel,self.bandwidth_mbps,self.ssid,self.bssid)
        if self.status != 'measured' and any(v is not None for v in values):
            raise ValueError('Unmeasured band must not contain measurement values')
        return self


class DeviceResult(Input):
    outcome: Literal['pass', 'fail', 'not_applicable'] | None = None
    notes: Notes | None = None
    band_24: BandResult = Field(default_factory=BandResult)
    band_5: BandResult = Field(default_factory=BandResult)


class DeviceResultSave(VisitVersion):
    result: DeviceResult


class BackboneResult(Input):
    download_mbps: Number | None = None
    upload_mbps: Number | None = None
    link_test_radio: Notes | None = None
    agreement_download_mbps: Number | None = None
    agreement_upload_mbps: Number | None = None
    minimum_percent: float | None = Field(default=None, gt=0, le=100, allow_inf_nan=False)
    conformity_reason: Literal['calculated', 'profile_missing', 'measurement_missing'] | None = None

    agreement_mbps: Number | None = None
    speedtest_mbps: Number | None = None
    conformity: Literal['conforming', 'not_conforming'] | None = None
    signal_dbm: float | None = Field(default=None, ge=-150, le=0, allow_inf_nan=False)
    tx_mbps: Number | None = None
    rx_mbps: Number | None = None
    ccq_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    notes: Notes | None = None
    source: Literal['manual'] = 'manual'


class HotelReport(Input):
    form_version: Literal[1, 2] = 1
    site_profile: SiteMaintenanceProfile | None = None
    router_connector_notes: Notes | None = None
    switch_connector_notes: Notes | None = None
    signal_test_notes: Notes | None = None
    blank_spot_notes: Notes | None = None
    hotspot_notes: Notes | None = None

    customer_company: Name | None = None
    pic_name: Name | None = None
    pic_contact: Short | None = None
    backbone_mode: Literal['fo_only', 'wireless_only', 'both', 'failover', 'bonding'] | None = None
    fo: BackboneResult | None = None
    wireless: BackboneResult | None = None
    router_connector: Literal['normal', 'abnormal', 'not_applicable'] | None = None
    switch_connector: Literal['normal', 'abnormal', 'not_applicable'] | None = None
    signal_test: Literal['poor', 'good', 'not_applicable'] | None = None
    blank_spot: bool | None = None
    hotspot: bool | None = None
    lan_notes: Notes | None = None
    summary: Notes | None = None
    work_status: Literal['completed', 'pending'] | None = None
    pending_reason: Reason | None = None
    customer_feedback: Notes | None = None
    solution: Notes | None = None
    pic_exception_reason: Reason | None = None

    @model_validator(mode='after')
    def connection_scope(self):
        if self.backbone_mode == 'fo_only' and self.wireless is not None:
            raise ValueError('FO-only report must not contain wireless results')
        if self.backbone_mode == 'wireless_only' and self.fo is not None:
            raise ValueError('Wireless-only report must not contain FO results')
        return self


class HotelReportSave(VisitVersion):
    report: HotelReport
