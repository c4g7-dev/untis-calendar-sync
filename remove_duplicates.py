#!/usr/bin/env python3
"""
Entfernt Duplikate aus Google Calendar basierend auf untis_uid
"""

import os
import pickle
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

def find_and_remove_duplicates(dry_run=True):
    """Findet und entfernt Duplikate"""
    service = authenticate()
    
    print("="*60)
    print("🔍 Suche nach Duplikaten in Google Calendar")
    print("="*60)
    
    # Hole Events
    now = datetime.utcnow()
    time_min = (now - timedelta(days=7)).isoformat() + 'Z'
    time_max = (now + timedelta(days=90)).isoformat() + 'Z'
    
    print(f"\n📅 Zeitraum: {time_min[:10]} bis {time_max[:10]}")
    
    all_events = []
    page_token = None
    
    while True:
        events_result = service.events().list(
            calendarId='primary',
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
    
    print(f"📊 {len(all_events)} Events gefunden\n")
    
    # Gruppiere nach untis_uid
    by_uid = {}
    
    for event in all_events:
        extended = event.get('extendedProperties', {}).get('private', {})
        uid = extended.get('untis_uid')
        
        if not uid:
            continue
        
        if uid not in by_uid:
            by_uid[uid] = []
        
        by_uid[uid].append(event)
    
    # Finde Duplikate
    duplicates_found = 0
    duplicates_to_delete = []
    
    for uid, events in by_uid.items():
        if len(events) > 1:
            duplicates_found += len(events) - 1
            
            # Sortiere nach Erstellungsdatum (älteste behalten)
            events.sort(key=lambda e: e.get('created', ''))
            
            # Erste behalten, Rest löschen
            keep = events[0]
            delete = events[1:]
            
            print(f"\n🔴 Duplikat gefunden (UID: {uid}):")
            print(f"   ✓ Behalte: {keep.get('summary')} am {keep['start'].get('dateTime', '')[:10]}")
            print(f"              Google ID: {keep['id'][:20]}...")
            print(f"              Erstellt: {keep.get('created', 'unbekannt')[:10]}")
            
            for dup in delete:
                print(f"   ✗ Lösche:  {dup.get('summary')} am {dup['start'].get('dateTime', '')[:10]}")
                print(f"              Google ID: {dup['id'][:20]}...")
                print(f"              Erstellt: {dup.get('created', 'unbekannt')[:10]}")
                duplicates_to_delete.append(dup)
    
    if duplicates_found == 0:
        print("✅ Keine Duplikate gefunden!")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 Zusammenfassung:")
    print(f"   🔴 {duplicates_found} Duplikate gefunden")
    print(f"   🗑️  {len(duplicates_to_delete)} Events zu löschen")
    print(f"{'='*60}\n")
    
    if dry_run:
        print("⚠️  DRY RUN - Keine Events wurden gelöscht!")
        print("   Führe mit --delete aus um wirklich zu löschen:")
        print("   python3 remove_duplicates.py --delete")
        return
    
    # Wirklich löschen
    print("🗑️  Lösche Duplikate...")
    deleted = 0
    failed = 0
    
    for event in duplicates_to_delete:
        try:
            service.events().delete(
                calendarId='primary',
                eventId=event['id']
            ).execute()
            deleted += 1
            print(f"   ✓ Gelöscht: {event.get('summary')} ({event['id'][:20]}...)")
        except Exception as e:
            failed += 1
            print(f"   ✗ Fehler: {event.get('summary')} - {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Fertig!")
    print(f"   ✓ Gelöscht: {deleted}")
    if failed > 0:
        print(f"   ✗ Fehlgeschlagen: {failed}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    import sys
    
    dry_run = '--delete' not in sys.argv
    
    if dry_run:
        print("\n⚠️  DRY RUN Modus - Zeigt nur was gelöscht würde\n")
    else:
        print("\n⚠️  LÖSCH-MODUS - Duplikate werden wirklich gelöscht!\n")
        response = input("Bist du sicher? (j/n): ")
        if response.lower() not in ['j', 'y']:
            print("Abgebrochen.")
            sys.exit(0)
    
    find_and_remove_duplicates(dry_run=dry_run)
