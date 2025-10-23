#!/usr/bin/env python3
"""
Cleanup Script - Löscht alle Untis-Events aus Google Calendar
Nützlich um neu zu starten oder Duplikate zu entfernen
"""

import pickle
import os
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate():
    """Authentifiziere mit Google Calendar API"""
    creds = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

def find_untis_events(service, calendar_id='primary', days_forward=90):
    """Finde alle Untis-Events - mit sehr breiten Kriterien"""
    print(f"🔍 Suche Events der nächsten {days_forward} Tage...\n")
    
    now = datetime.utcnow()
    # Gehe auch in die Vergangenheit
    time_min = (now - timedelta(days=14)).isoformat() + 'Z'
    time_max = (now + timedelta(days=days_forward)).isoformat() + 'Z'
    
    all_events = []
    page_token = None
    
    # Hole ALLE Events mit Pagination
    while True:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=2500,
            singleEvents=True,
            orderBy='startTime',
            pageToken=page_token
        ).execute()
        
        events = events_result.get('items', [])
        all_events.extend(events)
        
        page_token = events_result.get('nextPageToken')
        if not page_token:
            break
    
    print(f"📊 {len(all_events)} Events total gefunden\n")
    
    # Filter: Finde Events die wie Untis-Events aussehen
    untis_events = []
    
    # Liste bekannter Fächer (erweitere diese Liste falls nötig)
    known_subjects = [
        'Deu', 'Mat', 'Eng', 'Fra', 'Spa', 'Ita',  # Sprachen
        'Phy', 'Che', 'Bio',  # Naturwissenschaften
        'GeGk', 'Geo', 'Ges', 'WiRe', 'Pol',  # Gesellschaft
        'Inf', 'IfKo',  # Informatik
        'Spo', 'Sport',  # Sport
        'Mus', 'Kun', 'Rel', 'Eth'  # Andere
    ]
    
    for event in all_events:
        summary = event.get('summary', '')
        location = event.get('location', '')
        description = event.get('description', '')
        
        # Kriterien für Untis-Events (sehr breit gefasst):
        is_untis = False
        reason = ""
        
        # 1. Hat untis_uid (100% sicher)
        extended = event.get('extendedProperties', {}).get('private', {})
        if 'untis_uid' in extended:
            is_untis = True
            reason = "hat UID"
        
        # 2. Fach-Name passt
        elif summary in known_subjects:
            is_untis = True
            reason = f"Fach: {summary}"
        
        # 3. Raum-Pattern: O + 4 Ziffern (z.B. O1027)
        elif location and len(location) <= 10:
            if location.startswith('O') and any(c.isdigit() for c in location):
                is_untis = True
                reason = f"Raum: {location}"
        
        # 4. Kurzer Name (max 6 Zeichen) UND hat Location
        elif len(summary) <= 6 and location:
            is_untis = True
            reason = f"kurz + Location"
        
        # 5. Beschreibung enthält "Lehrer:" oder "Raum:"
        elif 'Lehrer:' in description or 'Raum:' in description:
            is_untis = True
            reason = "hat Lehrer/Raum in Beschreibung"
        
        if is_untis:
            start = event['start'].get('dateTime', event['start'].get('date'))
            untis_events.append({
                'id': event['id'],
                'summary': summary,
                'start': start,
                'location': location,
                'description': description[:50],
                'reason': reason
            })
    
    print(f"✓ {len(untis_events)} potentielle Untis-Events gefunden\n")
    
    return untis_events

def delete_events(service, events, calendar_id='primary', dry_run=False):
    """Löscht Events"""
    print(f"\n{'='*60}")
    print(f"{'DRY RUN - ' if dry_run else ''}Lösche {len(events)} Events...")
    print(f"{'='*60}\n")
    
    deleted = 0
    failed = 0
    
    for i, event in enumerate(events, 1):
        event_date = event['start'].split('T')[0] if 'T' in event['start'] else event['start']
        print(f"[{i}/{len(events)}] {event_date} {event['summary']:15} @ {event['location']:10}", end='')
        
        if dry_run:
            print(" ✓ (würde gelöscht)")
            deleted += 1
        else:
            try:
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=event['id']
                ).execute()
                print(" ✓")
                deleted += 1
            except Exception as e:
                print(f" ✗ ({e})")
                failed += 1
    
    print(f"\n{'='*60}")
    if dry_run:
        print(f"Würde löschen: {deleted}")
    else:
        print(f"✓ Gelöscht: {deleted}")
        if failed > 0:
            print(f"✗ Fehlgeschlagen: {failed}")
    print(f"{'='*60}\n")

def main():
    print("="*60)
    print("🧹 Untis Calendar Cleanup")
    print("="*60 + "\n")
    
    service = authenticate()
    
    # Finde Events
    events = find_untis_events(service)
    
    if not events:
        print("✓ Keine Untis-Events gefunden. Calendar ist sauber!\n")
        return
    
    # Zeige Zusammenfassung
    print(f"📊 Gefundene Events: {len(events)}")
    
    # Gruppiere nach Datum
    by_date = {}
    for event in events:
        date = event['start'].split('T')[0] if 'T' in event['start'] else event['start']
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(event)
    
    print(f"📅 Über {len(by_date)} Tage verteilt:\n")
    for date in sorted(by_date.keys())[:15]:  # Zeige erste 15 Tage
        events_on_date = by_date[date]
        count = len(events_on_date)
        
        # Zeige Details für jeden Tag
        print(f"  {date}:")
        for event in events_on_date[:5]:  # Max 5 pro Tag
            print(f"    • {event['summary']:8} @ {event.get('location', 'N/A'):8} [{event['reason']}]")
        if len(events_on_date) > 5:
            print(f"    ... und {len(events_on_date) - 5} weitere")
    
    if len(by_date) > 15:
        print(f"\n  ... und {len(by_date) - 15} weitere Tage")
    
    # Frage Nutzer
    print("\n" + "="*60)
    print("⚠️  WARNUNG: Dies löscht ALLE oben aufgeführten Events!")
    print("="*60)
    response = input("\nFortfahren? (j/n/d für dry-run): ").lower()
    
    if response in ['j', 'y', 'd']:
        dry_run = (response == 'd')
        delete_events(service, events, dry_run=dry_run)
        
        if not dry_run:
            print("✅ Cleanup abgeschlossen!")
            print("💡 Führe jetzt 'untis_sync_improved.py' aus um neu zu synchronisieren.\n")
    else:
        print("\n✋ Abgebrochen. Keine Events wurden gelöscht.\n")

if __name__ == "__main__":
    main()
