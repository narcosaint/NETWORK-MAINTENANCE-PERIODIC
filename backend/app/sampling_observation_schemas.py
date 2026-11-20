"""Typed client observations. No client-provided completion or verified flag."""
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, IPvAnyAddress, model_validator
from app.sampling_schemas import StrictInput


class SamplingNotes(StrictInput):
    condition: Literal['untested', 'good', 'attention', 'problem'] = 'untested'
    notes: str = Field(default='', max_length=5000)
    findings: str = Field(default='', max_length=5000)
    action: str = Field(default='', max_length=5000)
    recommendation: str = Field(default='', max_length=5000)

    @model_validator(mode='after')
    def explain_problem(self):
        if self.condition in ('attention', 'problem') and not (self.findings.strip() or self.notes.strip()):
            raise ValueError('Isi temuan untuk kondisi perlu perhatian/bermasalah')
        return self


class WifiConnection(StrictInput):
    source: Literal['android_native']
    observed_at: AwareDatetime
    transport: Literal['wifi']
    ssid: str | None = Field(default=None, max_length=32)
    bssid: str | None = Field(default=None, pattern=r'^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
    frequency_mhz: int | None = Field(default=None, ge=2300, le=7200, strict=True)
    rssi_dbm: int | None = Field(default=None, ge=-127, le=0, strict=True)
    link_speed_mbps: float | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    ip_address: IPvAnyAddress | None = None
    gateway: IPvAnyAddress | None = None


class ScanNetwork(StrictInput):
    ssid: str = Field(max_length=32)
    bssid: str = Field(pattern=r'^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
    frequency_mhz: int = Field(ge=2300, le=7200, strict=True)
    rssi_dbm: int = Field(ge=-127, le=0, strict=True)
    observed_at: AwareDatetime | None = None
    cached: bool | None = None


class WifiScan(StrictInput):
    source: Literal['android_native']
    observed_at: AwareDatetime
    cached: bool
    requested_band: Literal['2.4 GHz', '5 GHz'] | None = None
    reason: str | None = Field(default=None, max_length=500)
    networks: list[ScanNetwork] = Field(max_length=256)

    @model_validator(mode='after')
    def preserve_provenance(self):
        if any(network.cached for network in self.networks) and not self.cached:
            raise ValueError('Batch dengan hasil cache harus ditandai cached')
        if self.requested_band:
            for network in self.networks:
                matches = 2400 <= network.frequency_mhz <= 2500 if self.requested_band == '2.4 GHz' else 5000 <= network.frequency_mhz < 5925
                if not matches:
                    raise ValueError('Frekuensi jaringan tidak sesuai band scan')
        return self


class ObservationCreate(StrictInput):
    id: UUID
    expected_visit_version: int = Field(ge=1)
    expected_session_version: int = Field(ge=1)
    captured_at: AwareDatetime
    notes: SamplingNotes
    wifi_connection: WifiConnection | None = None
    wifi_scan: WifiScan | None = None
