import locale
import tkinter as tk
import urllib.request
from datetime import date, datetime
from tkinter import font
from typing import TypedDict

from icalendar import Calendar  # pyright: ignore[reportMissingModuleSource]
from icalendar.cal import Component  # pyright: ignore[reportMissingModuleSource]

ICAL_URL: str = "https://www.supersaas.nl/info/webcal/3327E8.ics"
# "https://supersaas.nl/schedule/download/Stadshuuslochem/Ruimtes?format=ics&from=09/06/2026&to=13/06/2026&resources=0&button="  # TODO: Make the days dynamic!!!


class EventDict(TypedDict):
    time: datetime | date
    is_all_day: bool
    summary: str
    description: str


def fetch_today_events(url: str) -> list[EventDict]:
    """Fetches the ics file, parses it, and returns sorted events for today."""
    try:
        req: urllib.request.Request = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:  # pyright: ignore[reportAny]
            ical_data: bytes = response.read()  # pyright: ignore[reportAny]

        cal: Component = Calendar.from_ical(ical_data)  # pyright: ignore[reportArgumentType]
        today: date = date(day=10, month=6, year=2026)  # Kept custom date
        events: list[EventDict] = []

        for component in cal.walk():
            if component.name == "VEVENT":
                dtstart_prop = component.get("dtstart")  # pyright: ignore[reportAny]
                if not dtstart_prop:
                    continue

                dtstart: datetime | date = dtstart_prop.dt  # pyright: ignore[reportAny]

                event_date: date
                is_all_day: bool
                if isinstance(dtstart, datetime):
                    event_date = dtstart.date()
                    is_all_day = False
                else:
                    event_date = dtstart
                    is_all_day = True

                if event_date == today:
                    summary: str = str(component.get("summary", "No Title"))  # pyright: ignore[reportAny]
                    description: str = str(component.get("description", ""))  # pyright: ignore[reportAny]

                    events.append(
                        {
                            "time": dtstart,
                            "is_all_day": is_all_day,
                            "summary": summary,
                            "description": description,
                        }
                    )

        events.sort(
            key=lambda e: (
                not e["is_all_day"],
                e["time"] if isinstance(e["time"], datetime) else datetime.min,
            )
        )
        return events
    except Exception:
        return []


def create_vfill(parent: tk.Widget) -> tk.Frame:
    spacer: tk.Frame = tk.Frame(parent, bg="#121212")
    spacer.pack(expand=True, fill="both")
    return spacer


def build_gui() -> None:
    root: tk.Tk = tk.Tk()
    root.title("Stadshuus evenementen viewer")

    _ = root.attributes("-fullscreen", True)  # pyright: ignore[reportUnknownMemberType]
    _ = root.configure(bg="#121212")
    _ = root.bind("<Escape>", lambda e: root.destroy())
    _ = root.bind("q", lambda e: root.destroy())

    # Get screen width to calculate dynamic text wrap length for two columns
    screen_width: int = root.winfo_screenwidth()
    # Subtracting padding and time column width (~400px), split remaining space in 2
    column_wrap_width: int = (screen_width - 400) // 2

    title_font: font.Font = font.Font(family="Helvetica", size=42, weight="bold")
    event_font: font.Font = font.Font(family="Helvetica", size=28)
    desc_font: font.Font = font.Font(family="Helvetica", size=22)

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
        no_event_label.pack()
        # _ = create_vfill(events_frame)
    else:
        for item in agenda:
            time_str: str
            time_color: str
            if item["is_all_day"]:
                time_str = "All Day "
                time_color = "#FFA500"
            else:
                time_str = item["time"].strftime("%H:%M")
                time_color = "#00ADB5"

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
    _ = locale.setlocale(locale.LC_ALL, "nl_NL.UTF-8")
    build_gui()
