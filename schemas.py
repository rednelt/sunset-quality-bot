from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Magics(BaseModel):
    golden_hour: List[
        datetime | None
    ]  # sometimes the API returns None, due to reasons not known to me. tested in Greenland
    blue_hour: List[datetime | None]


class ForecastData(BaseModel):
    time: datetime
    type: str
    model_data: bool
    quality_text: Optional[str] = None
    quality: Optional[float] = None
    cloud_cover: Optional[float] = None
    direction: float
    magics: Magics


class ForecastResponse(BaseModel):
    data: ForecastData
