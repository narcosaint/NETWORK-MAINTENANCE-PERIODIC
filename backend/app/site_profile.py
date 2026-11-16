"""Site-level maintenance values, configured once by supervisors."""
from pydantic import BaseModel, ConfigDict, Field


class ServiceBandwidth(BaseModel):
    model_config = ConfigDict(extra='forbid')
    download_mbps: float | None = Field(default=None, gt=0, le=1_000_000, allow_inf_nan=False)
    upload_mbps: float | None = Field(default=None, gt=0, le=1_000_000, allow_inf_nan=False)


class SiteMaintenanceProfile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    minimum_percent: float | None = Field(default=None, gt=0, le=100, allow_inf_nan=False)
    fo: ServiceBandwidth | None = None
    wireless: ServiceBandwidth | None = None
