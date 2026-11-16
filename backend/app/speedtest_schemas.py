from typing import Literal
from pydantic import Field, model_validator
from app.schemas import Input, VisitVersion
from app.hotel_schemas import Short, Reason


class StartSpeedtest(VisitVersion):
    band: Literal['band_24', 'band_5']
    network: Literal['hotel_wifi', 'cellular', 'ethernet', 'unknown']
    wifi_confirmed: bool = False
    observed_type: Literal['wifi', 'cellular', 'ethernet', 'unknown', 'none'] = 'unknown'
    ssid: Short | None = None
    bssid: Short | None = None

    @model_validator(mode='after')
    def honest_network(self):
        if self.network == 'hotel_wifi' and not self.wifi_confirmed:
            raise ValueError('Confirm the Wi-Fi hotel/AP connection before starting')
        if self.network == 'hotel_wifi' and self.observed_type in ('cellular', 'ethernet', 'none'):
            raise ValueError('Observed connection does not match hotel Wi-Fi')
        return self


class Metrics(Input):
    download_mbps: float = Field(ge=0, le=1_000_000, allow_inf_nan=False)
    upload_mbps: float = Field(ge=0, le=1_000_000, allow_inf_nan=False)
    ping_ms: float = Field(ge=0, le=120_000, allow_inf_nan=False)
    jitter_ms: float = Field(ge=0, le=120_000, allow_inf_nan=False)


class FinishSpeedtest(Input):
    status: Literal['completed', 'failed', 'aborted']
    metrics: Metrics | None = None
    error: Reason | None = None

    @model_validator(mode='after')
    def actual_results(self):
        if self.status == 'completed' and self.metrics is None:
            raise ValueError('Completed tests require all measurements')
        if self.status != 'completed' and self.metrics is not None:
            raise ValueError('Failed/aborted tests must not pretend to contain completed results')
        return self
