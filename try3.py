#!/usr/bin/env python3
import locale
import os
import tkinter as tk
from datetime import datetime, time, timedelta
from tkinter import font as tkfont

import requests
from PIL import Image, ImageTk

PUBLIC_SCHEDULE_ID = os.environ["STADSHUUS_PUBLIC_SCHEDULE_ID"]
PUBLIC_API_KEY = os.environ["STADSHUUS_PUBLIC_API_KEY"]

PRIVATE_SCHEDULE_ID = os.environ["STADSHUUS_PRIVATE_SCHEDULE_ID"]
PRIVATE_API_KEY = os.environ["STADSHUUS_PRIVATE_API_KEY"]


LOGO_PATH = "stadshuus.png"

BLUE = "#0057B8"
WHITE = "white"
BLACK = "black"

IS_TESTING = True
today = datetime.now().date() - timedelta(days=2)  # noqa: DTZ005

locale.setlocale(locale.LC_TIME, "nl_NL")


def get_schedule(id: str, key: str):
    url = f"https://www.supersaas.com/api/range/{id}.json"
    parameters = {
        "api_key": key,
        "from": str(today - timedelta(days=1)),
        "to": str(today + timedelta(days=1)),
        "limit": "1000",
        "form": "true",
    }
    try:
        response = requests.get(url, params=parameters, timeout=30)
    except requests.exceptions.RequestException as fout:
        print("FOUT: kon geen verbinding maken met Supersaas voor vandaag.")
        print(f"Details: {fout}")
        return None

    if response.status_code != 200:
        print("FOUT: Supersaas gaf geen succesvol antwoord terug voor vandaag.")
        print(f"Statuscode: {response.status_code}")
        print(response.text[:500])
        return None

    data = response.json()
    return data["bookings"]


def filter_today(bookings):
    bookings_today = []
    for booking in bookings:
        if datetime.fromisoformat(booking["start"]).date() == today:
            bookings_today.append(booking)

    return bookings_today


def extract_time_of_day(bookings):
    morning = []
    afternoon = []
    evening = []
    for booking in bookings:
        start_time = datetime.fromisoformat(booking["start"]).time()
        end_time = datetime.fromisoformat(booking["start"]).time()
        if time(9, 0) <= start_time <= time(12, 30):
            morning.append(booking)
        elif time(12, 30) <= start_time <= time(17, 1):
            afternoon.append(booking)
        elif time(19, 0) <= start_time <= time(22, 30):
            evening.append(booking)

        if time(9, 0) <= end_time <= time(12, 30) and booking not in morning:
            morning.append(booking)
        elif time(12, 30) <= end_time <= time(17, 1) and booking not in afternoon:
            afternoon.append(booking)
        elif time(19, 0) <= end_time <= time(22, 30) and booking not in evening:
            evening.append(booking)
    return morning, afternoon, evening


def extract_data(bookings):
    location = []
    orga = []
    activity = []
    if bookings != []:
        for booking in bookings:
            location.append(booking["res_name"])
            orga.append(booking["field_1"])
            activity.append(booking["description"])
    return location, orga, activity

    # Header display
    today_str: str = datetime.now().strftime("%A, %B %d, %Y")
    header: tk.Label = tk.Label(
        root, text=today_str, fg="#FFFFFF", bg="#121212", font=title_font
    )
    header.pack(pady=(60, 10))

    events_frame: tk.Frame = tk.Frame(root, bg="#121212")
    events_frame.pack(fill="both", expand=True, padx=100)

    agenda: list[EventDict] = fetch_today_events(ICAL_URL)

    # Insert initial \vfill before the first event
    _ = create_vfill(events_frame)

    if not agenda:
        no_event_label: tk.Label = tk.Label(
            events_frame,
            text="Vandaag geen evenementen",
            fg="#A0A0A0",
            bg="#121212",
            font=event_font,
        )

            row: tk.Frame = tk.Frame(events_frame, bg="#121212")
            row.pack(fill="x")

            # Column 1: Time
            time_label: tk.Label = tk.Label(
                row,
                text=time_str,
                fg=time_color,
                bg="#121212",
                font=event_font,
                width=10,
                anchor="ne",
                justify="left",
            )
            time_label.pack(side="left", anchor="n")

            # Column 2: Summary
            # Using expand=True ensures this column takes exactly half the available remaining space
            summary_label: tk.Label = tk.Label(
                row,
                text=item["summary"],
                fg="#EEEEEE",
                bg="#121212",
                font=event_font,
                anchor="ne",
                justify="left",
                wraplength=column_wrap_width,
            )
            summary_label.pack(
                side="left", padx=(500, 10), expand=False, fill="x", anchor="n"
            )

            # Column 3: Description
            # Using expand=True ensures this column takes the other half
            desc_label: tk.Label = tk.Label(
                row,
                text=item["description"],
                fg="#AAAAAA",
                bg="#121212",
                font=desc_font,
                anchor="ne",
                justify="right",
                wraplength=column_wrap_width,
            )
            desc_label.pack(
                side="right", padx=(10, 20), expand=True, fill="x", anchor="n"
            )

            # Insert \vfill after each event to distribute vertical space
            _ = create_vfill(events_frame)

    root.mainloop()


if __name__ == "__main__":
    public_bookings = filter_today(get_schedule(PUBLIC_SCHEDULE_ID, PUBLIC_API_KEY))
    private_bookings = filter_today(get_schedule(PRIVATE_SCHEDULE_ID, PRIVATE_API_KEY))
    bookings = public_bookings + private_bookings
    morning, afternoon, evening = extract_time_of_day(bookings)

    morning_location, morning_orga, morning_activity = extract_data(morning)
    afternoon_location, afternoon_orga, afternoon_activity = extract_data(afternoon)
    evening_location, evening_orga, evening_activity = extract_data(evening)
    create_activity_gui(
        morning_location,
        morning_orga,
        morning_activity,
        afternoon_location,
        afternoon_orga,
        afternoon_activity,
        evening_location,
        evening_orga,
        evening_activity,
    )
