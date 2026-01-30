import json
from zoneinfo import ZoneInfo
import datetime

def iso_to_local_dt(iso_string, timezone_name):
    return datetime.datetime.fromisoformat(iso_string).astimezone(ZoneInfo(timezone_name))

def format_forecast(response_text, timezone_name):
    response_json = json.loads(response_text)

    local_event_time = iso_to_local_dt(response_json["data"]["time"], timezone_name)

    type = response_json["data"]["type"]
    title = f"<b>{"🌅" if type == "sunrise" else "🌄"} {type.capitalize()} quality forecast for {local_event_time.strftime("%a, %d.%m")}:</b>"

    if response_json["data"]["model_data"] == True:
        quality = f"{response_json["data"]["quality_text"]} {round(response_json["data"]["quality"] * 100)}%"
        cloud_cover = f"{round(response_json["data"]["cloud_cover"] * 100)}%"
    else:
        quality = "Unavailable"
        cloud_cover = "Also unavailable. Try again in a couple of hours."
    

    direction = f"{response_json["data"]["direction"]}°"
    golden_hour = f"{iso_to_local_dt(response_json["data"]["magics"]["golden_hour"][0], timezone_name).strftime("%H:%M")} - " \
        f"{iso_to_local_dt(response_json["data"]["magics"]["golden_hour"][1], timezone_name).strftime("%H:%M")}"
    blue_hour = f"{iso_to_local_dt(response_json["data"]["magics"]["blue_hour"][0], timezone_name).strftime("%H:%M")} - " \
        f"{iso_to_local_dt(response_json["data"]["magics"]["blue_hour"][1], timezone_name).strftime("%H:%M")}"
    

    return f"""{title}
{"─" * 26}
📸 Quality: {quality}
🌥️ Cloud cover: {cloud_cover}

🕒 Time: {local_event_time.strftime("%H:%M")}
🧭 Direction: {direction}

🟧 Golden hour: {golden_hour}
🟦 Blue hour: {blue_hour}"""
    
    