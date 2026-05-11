import datetime
from zoneinfo import ZoneInfo

from schemas import ForecastResponse


def format_forecast(forecast_response: ForecastResponse, timezone_name: str) -> str:
    data = forecast_response.data
    local_event_time = data.time.astimezone(ZoneInfo(timezone_name))

    type_ = data.type
    title = f"<b>{'🌅' if type_ == 'sunrise' else '🌄'} {type_.capitalize()} quality forecast for {local_event_time.strftime('%a, %d.%m')}:</b>"

    if data.model_data:
        quality = f"{data.quality_text} {round(data.quality * 100)}%"
        cloud_cover = f"{round(data.cloud_cover * 100)}%"
    else:
        quality = "Unavailable"
        cloud_cover = "Also unavailable. Try again in a couple of hours."

    direction = f"{data.direction}°"

    # Fix for API issue where it doesn't return blue/golden hour start/end times
    if not data.magics.golden_hour[0]:
        data.magics.golden_hour[0] = (
            datetime.datetime.now()
            .astimezone(ZoneInfo(timezone_name))
            .replace(hour=0, minute=0)
        )
    if not data.magics.golden_hour[1]:
        data.magics.golden_hour[1] = (
            datetime.datetime.now()
            .astimezone(ZoneInfo(timezone_name))
            .replace(hour=23, minute=59)
        )
    if not data.magics.blue_hour[0]:
        data.magics.blue_hour[0] = (
            datetime.datetime.now()
            .astimezone(ZoneInfo(timezone_name))
            .replace(hour=0, minute=0)
        )
    if not data.magics.blue_hour[1]:
        data.magics.blue_hour[1] = (
            datetime.datetime.now()
            .astimezone(ZoneInfo(timezone_name))
            .replace(hour=23, minute=59)
        )

    gh_start = data.magics.golden_hour[0].astimezone(ZoneInfo(timezone_name))
    gh_end = data.magics.golden_hour[1].astimezone(ZoneInfo(timezone_name))
    bh_start = data.magics.blue_hour[0].astimezone(ZoneInfo(timezone_name))
    bh_end = data.magics.blue_hour[1].astimezone(ZoneInfo(timezone_name))

    golden_hour = f"{gh_start.strftime('%H:%M')} - {gh_end.strftime('%H:%M')}"
    blue_hour = f"{bh_start.strftime('%H:%M')} - {bh_end.strftime('%H:%M')}"

    return f"""
{title}
{"─" * 26}
📸 Quality: {quality}
🌥️ Cloud cover: {cloud_cover}

🕒 Time: {local_event_time.strftime("%H:%M")}
🧭 Direction: {direction}

🟧 Golden hour: {golden_hour}
🟦 Blue hour: {blue_hour}
"""
