import datetime
import pytz
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

tz = pytz.timezone("America/Chicago")

def create_calendar_edit_url(event_html_link):
    if 'calendar.google.com' in event_html_link and 'eid=' in event_html_link:
        return event_html_link.replace('/event?', '/eventedit?')
    return event_html_link

def generate_summary_html(credentials_map: dict[str, Credentials]) -> str:
    tomorrow = datetime.datetime.now(tz) + datetime.timedelta(days=1)
    tomorrow_date = tomorrow.date()

    # === Gather all events ===
    all_events = []
    for email, creds in credentials_map.items():
        service = build('calendar', 'v3', credentials=creds)

        start_of_day = tz.localize(datetime.datetime.combine(tomorrow_date, datetime.time.min)).isoformat()
        end_of_day = tz.localize(datetime.datetime.combine(tomorrow_date, datetime.time.max)).isoformat()

        events_result = service.events().list(
            calendarId=email,
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        for event in events:
            start = event['start'].get('dateTime')
            end = event['end'].get('dateTime')
            if not start or not end:
                continue

            all_events.append({
                "start": datetime.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(tz),
                "end": datetime.datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone(tz),
                "summary": event.get('summary', 'No Title'),
                "creator": event.get('creator', {}).get('email', email),
                "link": event.get('htmlLink', '#'),
                "id": event.get('id', ''),
                "calendar_email": email
            })

    all_events.sort(key=lambda x: x['start'])

    tomorrow_str = tomorrow.strftime("%A, %B %d, %Y")
    html = f"""<!DOCTYPE html>
    <html><head><meta charset="UTF-8">
    <title>Daily Calendar Summary</title>
    <style>
    body {{ font-family: 'Segoe UI', sans-serif; padding: 20px; background: #f9f9ff; color: #333; font-size: 14px; line-height: 1.3; }}
    h1, h2 {{ color: #5b4fc7; margin: 10px 0 6px 0; }}
    .event {{ padding: 6px 10px; margin: 6px 0; border-left: 4px solid #a88efb; background: #fff; }}
    .event time {{ font-weight: bold; margin-right: 6px; display: inline-block; width: 120px; }}
    .event a {{ color: #4a5bdc; text-decoration: none; }}
    small {{ color: #666; font-size: 12px; }}
    .conflict {{ color: #b33; font-weight: bold; margin: 4px 0; }}
    .suggestion {{ color: #228B22; font-style: italic; margin-left: 20px; }}
    .suggestion a {{ color: #1a7a1a; text-decoration: none; font-weight: bold; }}
    .suggestion a:hover {{ text-decoration: underline; }}
    </style></head><body>
    <h1>📅 {tomorrow_str} Schedule</h1>
    """

    for event in all_events:
        html += f"""
        <div class="event">
          <div><time>{event['start'].strftime('%I:%M %p')} – {event['end'].strftime('%I:%M %p')}</time><a href="{event['link']}" target="_blank">{event['summary']}</a></div>
          <div><small>{event['creator']}</small></div>
        </div>
        """

    def overlap(a, b):
        return max(a['start'], b['start']) < min(a['end'], b['end'])

    conflicts = []
    for i in range(len(all_events)):
        for j in range(i + 1, len(all_events)):
            if overlap(all_events[i], all_events[j]):
                conflicts.append((all_events[i], all_events[j]))

    def get_busy_times_for_date_range(start_date, end_date):
        all_busy = []
        for email, creds in credentials_map.items():
            service = build('calendar', 'v3', credentials=creds)
            body = {
                "timeMin": tz.localize(datetime.datetime.combine(start_date, datetime.time(8, 0))).isoformat(),
                "timeMax": tz.localize(datetime.datetime.combine(end_date, datetime.time(17, 0))).isoformat(),
                "timeZone": "America/Chicago",
                "items": [{"id": email}]
            }
            try:
                freebusy = service.freebusy().query(body=body).execute()
                for cal in freebusy.get('calendars', {}).values():
                    all_busy.extend([
                        (datetime.datetime.fromisoformat(busy['start'].replace('Z', '+00:00')).astimezone(tz),
                         datetime.datetime.fromisoformat(busy['end'].replace('Z', '+00:00')).astimezone(tz))
                        for busy in cal.get('busy', [])
                    ])
            except Exception as e:
                print(f"Error querying freebusy for {email}: {e}")
        return all_busy

    all_busy = get_busy_times_for_date_range(tomorrow_date, tomorrow_date)

    def is_slot_free(start, end, busy_times):
        for busy_start, busy_end in busy_times:
            if max(start, busy_start) < min(end, busy_end):
                return False
        return True

    if conflicts:
        html += "<h2 style='margin-top: 20px;'>⚠ Conflicts Detected</h2>"
        global_suggested_times = []
        processed_events = set()

        for a, b in conflicts:
            html += f"<p class=\"conflict\">🔥 {a['summary']} ↔ {b['summary']}<br>🕐 {a['start'].strftime('%I:%M %p')}–{a['end'].strftime('%I:%M %p')} ↔ {b['start'].strftime('%I:%M %p')}–{b['end'].strftime('%I:%M %p')}</p>"
            event = a
            event_key = (event['summary'], event['start'], event['end'])
            if event_key in processed_events:
                continue
            processed_events.add(event_key)

            duration = event['end'] - event['start']
            now = datetime.datetime.now(tz)
            suggestion_found = False

            for offset in range(14):
                candidate_day = tomorrow_date + datetime.timedelta(days=offset)
                if candidate_day.weekday() >= 5:
                    continue
                candidate_busy_times = get_busy_times_for_date_range(candidate_day, candidate_day)

                for hour in range(8, 17):
                    for minute in [0, 30]:
                        proposed_start = tz.localize(datetime.datetime.combine(candidate_day, datetime.time(hour, minute)))
                        proposed_end = proposed_start + duration
                        if proposed_end.time() > datetime.time(17, 0) or proposed_start <= now:
                            continue
                        if any(max(proposed_start, s) < min(proposed_end, e) for s, e in global_suggested_times):
                            continue
                        if is_slot_free(proposed_start, proposed_end, candidate_busy_times):
                            day_name = proposed_start.strftime('%A')
                            date_str = proposed_start.strftime('%B %d')
                            time_str = proposed_start.strftime('%I:%M %p')
                            end_time_str = proposed_end.strftime('%I:%M %p')
                            edit_url = create_calendar_edit_url(event['link'])

                            html += f"""<p class='suggestion'>✅ Suggest moving '<strong>{event['summary']}</strong>' to 
                            <a href="{edit_url}" target="_blank">{day_name}, {date_str} at {time_str}–{end_time_str}</a></p>"""
                            global_suggested_times.append((proposed_start, proposed_end))
                            suggestion_found = True
                            break
                    if suggestion_found:
                        break
                if suggestion_found:
                    break

            if not suggestion_found:
                html += f"<p class='suggestion'>❌ No free slots found in the next 2 weeks for '{event['summary']}' ({duration})</p>"

    html += "</body></html>"
    return html

