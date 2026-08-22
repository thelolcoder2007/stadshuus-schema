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


def create_activity_gui(
    morning_locations,
    morning_organisations,
    morning_activities,
    afternoon_locations,
    afternoon_organisations,
    afternoon_activities,
    evening_locations,
    evening_organisations,
    evening_activities,
):
    root = tk.Tk()
    root.title("Activiteitenoverzicht")
    root.configure(bg=WHITE)
    root.attributes("-fullscreen", True)
    root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))

    header_font = tkfont.Font(family="Helvetica", size=26, weight="bold")
    column_header_font = tkfont.Font(
        family="Helvetica", size=18, weight="bold", underline=True
    )
    row_font = tkfont.Font(family="Helvetica", size=20)
    date_font = tkfont.Font(family="Helvetica", size=18, weight="bold")

    # ---------- Top blue bar ----------
    top_bar = tk.Frame(root, bg=BLUE, height=90)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    try:
        logo_img = Image.open(LOGO_PATH)
        logo_img.thumbnail((200, 2000))
        logo_photo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(top_bar, image=logo_photo, bg=BLUE)
        logo_label.image = logo_photo  # keep a reference, or it gets garbage collected  # pyright: ignore[reportAttributeAccessIssue]
        logo_label.pack(side="left", padx=25, pady=10)
    except Exception as e:
        print(f"Could not load logo from '{LOGO_PATH}': {e}")

    date_label = tk.Label(
        top_bar,
        text=today.strftime("%A %d %B %Y"),
        bg=BLUE,
        fg=WHITE,
        font=date_font,
    )
    date_label.pack(side="right", padx=25)

    # ---------- Content area ----------
    # A Canvas always clips its contents to its own visible area. We pin the
    # inner "content" frame to the TOP of the canvas (anchor="n"). If content
    # ends up taller than the canvas, the excess extends past the bottom and
    # is clipped there - the top stays fully visible, which is what we want.
    canvas = tk.Canvas(root, bg=WHITE, highlightthickness=0)
    canvas.pack(side="top", fill="both", expand=True)

    content = tk.Frame(canvas, bg=WHITE)
    content_window = canvas.create_window((0, 0), window=content, anchor="n")

    row_frames = []  # every per-activity row, so we can re-wrap text on resize

    def _on_canvas_resize(event):
        # Keep the inner frame exactly as wide as the canvas, and re-center
        # it horizontally at the top. This is what makes the three columns
        # responsive to window resizing.
        canvas.itemconfig(content_window, width=event.width)
        canvas.coords(content_window, event.width / 2, 0)

        # Re-wrap each label's text to roughly a third of the new width, so
        # long names wrap inside their own column instead of drifting into
        # the neighbouring one.
        col_width = max(event.width // 3 - 40, 80)
        for row in row_frames:
            for label in row.winfo_children():
                label.configure(wraplength=col_width)

    canvas.bind("<Configure>", _on_canvas_resize)

    now = datetime.now().time()
    show_morning = now < time(12, 30)
    show_afternoon = now < time(17, 0)

    def add_grid_row(parent, texts, font, pady=6):
        """Lay out three values across the same responsive column grid used
        everywhere else, so headings and data rows always line up."""
        row = tk.Frame(parent, bg=WHITE)
        row.pack(pady=pady, fill="x", padx=40)
        row_frames.append(row)

        row.columnconfigure(0, weight=1, uniform="activity_cols")
        row.columnconfigure(1, weight=1, uniform="activity_cols")
        row.columnconfigure(2, weight=1, uniform="activity_cols")

        for col, text in enumerate(texts):
            tk.Label(
                row,
                text=text,
                bg=WHITE,
                fg=BLACK,
                font=font,
                anchor="center",
                justify="center",
            ).grid(row=0, column=col, sticky="nsew", padx=15)

    def add_section(title, locations, organisations, activities, visible):
        if not visible and not IS_TESTING:
            return

        # The time-of-day heading, centered across the full content width.
        tk.Label(
            content,
            text=title,
            bg=WHITE,
            fg=BLACK,
            font=header_font,
            anchor="w",
            justify="left",
        ).pack(padx=50, pady=(30, 10), fill="x")

        # Column headers, aligned with the data columns below them.
        add_grid_row(
            content,
            ("ORGANISATOR", "EVENEMENT", "LOCATIE"),
            column_header_font,
            pady=(0, 8),  # pyright: ignore[reportArgumentType]
        )

        if not organisations and not activities and not locations:
            tk.Label(
                content,
                text="Geen Activiteiten",
                bg=WHITE,
                fg=BLACK,
                font=row_font,
            ).pack(pady=5)
            return

        # Build the rows explicitly as dicts first - this makes it obvious
        # (and easy to check) that each row keeps its own organisation,
        # activity, and location together, instead of the three columns
        # accidentally ending up showing the same value.
        activity_rows = [
            {"organisation": org, "activity": act, "location": loc}
            for org, act, loc in zip(organisations, activities, locations)
        ]

        for entry in activity_rows:
            add_grid_row(
                content,
                (entry["organisation"], entry["activity"], entry["location"]),
                row_font,
            )

    add_section(
        "OCHTEND",
        morning_locations,
        morning_organisations,
        morning_activities,
        show_morning,
    )
    add_section(
        "MIDDAG",
        afternoon_locations,
        afternoon_organisations,
        afternoon_activities,
        show_afternoon,
    )
    add_section(
        "AVOND", evening_locations, evening_organisations, evening_activities, True
    )

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
