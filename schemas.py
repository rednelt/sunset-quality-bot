from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Magics(BaseModel):
    golden_hour: List[datetime]
    blue_hour: List[datetime]


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
