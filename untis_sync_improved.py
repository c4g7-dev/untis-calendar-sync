#!/usr/bin/env python3
"""
Verbessertes WebUntis zu Google Calendar Sync
- Unterstützt mehrere Wochen
- Automatische Extraktion direkt aus dem Browser
- Duplikat-Erkennung
"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import hashlib

SCOPES = ['https://www.googleapis.com/auth/calendar']

class UntisLesson:
    """Repräsentiert eine einzelne Unterrichtsstunde"""
    def __init__(self, start_time: str, end_time: str, subject: str, 
                 teacher: str, room: str, date: str):
        self.start_time = start_time
        self.end_time = end_time
        self.subject = subject
        self.teacher = teacher
        self.room = room
        self.date = date
        
        # Erstelle eine eindeutige ID für Duplikat-Erkennung
        self.uid = self._generate_uid()
    
    def _generate_uid(self) -> str:
        """Generiert eine eindeutige ID für diese Lesson"""
        # Normalisiere Raum: entferne Raumänderungen aber behalte Hauptraum
        # "+O1101, O1104" -> "O1104" (nimm zweiten wenn erster mit + beginnt)
        # "O1027, +O1101, +O1102" -> "O1027" (nimm ersten)
        # "N/A" -> "N/A"
        room_parts = [r.strip() for r in self.room.split(',')]
        
        # Filter: Nimm ersten Raum der NICHT mit + beginnt
        room_normalized = None
        for part in room_parts:
            clean_part = part.lstrip('+').strip()
            if clean_part and clean_part != 'N/A':
                room_normalized = clean_part
                break
        
        # Fallback auf originalen Raum wenn nichts gefunden
        if not room_normalized:
            room_normalized = room_parts[0].lstrip('+').strip() if room_parts else self.room
        
        data = f"{self.date}_{self.start_time}_{self.end_time}_{self.subject}_{room_normalized}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def __repr__(self):
        return f"Lesson({self.date} {self.start_time}-{self.end_time}: {self.subject} @ {self.room})"
    
    def to_dict(self):
        result = {
            'uid': self.uid,
            'date': self.date,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'subject': self.subject,
            'teacher': self.teacher,
            'room': self.room
        }
        # Füge Notiz hinzu falls vorhanden
        if hasattr(self, 'note') and self.note:
            result['note'] = self.note
        return result

class ImprovedUntisParser:
    """Verbesserter Parser der mehrere Tage/Wochen unterstützt"""
    
    def __init__(self, json_file: str):
        with open(json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.base_date = self._extract_date_from_url()
        
    def _extract_date_from_url(self) -> str:
        """Extrahiert das Datum aus der URL"""
        url = self.data['timetable']['url']
        match = re.search(r'date=(\d{4}-\d{2}-\d{2})', url)
        if match:
            return match.group(1)
        return datetime.now().strftime('%Y-%m-%d')
    
    def parse_lessons(self) -> List[UntisLesson]:
        """Parst alle Lessons - erkennt Wochentage durch Zeit-Resets"""
        lessons = []
        raw_lessons = self.data['timetable']['lessons']
        
        print(f"Analysiere {len(raw_lessons)} Einträge...")
        print(f"Basis-Datum aus URL: {self.base_date}")
        
        # Versuche die Wochenstruktur zu erkennen
        current_day_offset = 0  # Montag = 0, Dienstag = 1, etc.
        last_start_time = None
        last_lesson_card_index = -1
        
        i = 0
        while i < len(raw_lessons):
            lesson = raw_lessons[i]
            class_name = lesson.get('className', '')
            text = lesson.get('text', '').strip()
            
            # Prüfe ob das ein Lesson-Card Container ist
            # Nur die Haupt-lesson-card zählt (nicht lesson-card-container, etc.)
            if 'lesson-card ' in class_name or class_name.startswith('lesson-card '):
                # Extrahiere Zeit aus diesem Lesson
                time_match = re.search(r'(\d{2}):(\d{2})', text)
                if time_match:
                    current_time = f"{time_match.group(1)}:{time_match.group(2)}"
                    
                    # Wenn die Zeit KLEINER ist als die letzte Zeit UND
                    # wir haben schon mindestens eine Lesson gesehen,
                    # dann ist das ein neuer Tag
                    if last_start_time and current_time < last_start_time:
                        current_day_offset += 1
                        print(f"  → Tag wechsel erkannt bei Index {i}: {last_start_time} → {current_time}, jetzt Tag {current_day_offset}")
                    
                    last_start_time = current_time
                
                # Parse diese Lesson
                parsed = self._parse_lesson_card(raw_lessons, i, current_day_offset)
                if parsed:
                    lessons.append(parsed)
                    print(f"  ✓ Tag {current_day_offset} → {parsed.date} ({datetime.strptime(parsed.date, '%Y-%m-%d').strftime('%A')}): {parsed.start_time}-{parsed.end_time} {parsed.subject} @ {parsed.room}")
                
                last_lesson_card_index = i
            
            i += 1
        
        # Sortiere nach Datum und Zeit
        lessons.sort(key=lambda l: (l.date, l.start_time))
        
        print(f"\n✓ {len(lessons)} Lessons über {current_day_offset + 1} Tage gefunden")
        
        return lessons
    
    def _parse_lesson_card(self, lessons_list: List[Dict], start_index: int, day_offset: int) -> Optional[UntisLesson]:
        """Parst eine einzelne Lesson-Card"""
        try:
            # Berechne das Datum basierend auf day_offset
            base = datetime.strptime(self.base_date, '%Y-%m-%d')
            
            # Wenn base_date ein Montag ist, addiere day_offset Tage
            # Ansonsten finde den Montag dieser Woche
            weekday = base.weekday()  # 0 = Montag
            monday = base - timedelta(days=weekday)
            lesson_date = monday + timedelta(days=day_offset)
            lesson_date_str = lesson_date.strftime('%Y-%m-%d')
            
            main_text = lessons_list[start_index].get('text', '').strip()
            
            # Extrahiere Zeiten
            time_pattern = r'(\d{2}):(\d{2})'
            times = re.findall(time_pattern, main_text)
            
            if len(times) < 2:
                return None
            
            start_time = f"{times[0][0]}:{times[0][1]}"
            end_time = f"{times[1][0]}:{times[1][1]}"
            
            # Extrahiere Komponenten
            teacher = None
            subject = None
            room = None
            note = None  # Für Hinweise wie "Klassenarbeit"
            
            for i in range(start_index, min(start_index + 35, len(lessons_list))):
                item = lessons_list[i]
                text = item.get('text', '').strip()
                dataset = item.get('dataset', {})
                testid = dataset.get('testid', '')
                
                # Lehrer
                if 'lesson-card-resources-with-change-teachers' in testid:
                    if not teacher:  # Nur setzen wenn noch nicht gesetzt
                        for j in range(i, min(i + 3, len(lessons_list))):
                            next_text = lessons_list[j].get('text', '').strip()
                            if next_text and len(next_text) < 20 and not ':' in next_text:
                                teacher = next_text
                                break
                
                # Fach
                elif 'lesson-card-subject' in testid or testid == 'lesson-card-subjects':
                    if not subject:  # Nur setzen wenn noch nicht gesetzt
                        for j in range(i, min(i + 3, len(lessons_list))):
                            next_text = lessons_list[j].get('text', '').strip()
                            if next_text and len(next_text) < 20 and not ':' in next_text:
                                subject = next_text
                                break
                
                # Raum (WICHTIG: hat Priorität vor Notizen)
                elif 'lesson-card-resources-with-change-rooms' in testid:
                    if not room:  # Nur setzen wenn noch nicht gesetzt
                        for j in range(i, min(i + 3, len(lessons_list))):
                            next_text = lessons_list[j].get('text', '').strip()
                            # Prüfe ob es wie ein Raum aussieht (O + Zahlen)
                            if next_text and re.match(r'O\d{3,4}', next_text):
                                room = next_text
                                break
                
                # Hinweis/Notiz (z.B. "Klassenarbeit Lit") - NACH Raum-Check!
                elif 'lesson-card-text-content-container' in testid:
                    if not note:  # Nur setzen wenn noch nicht gesetzt
                        for j in range(i, min(i + 3, len(lessons_list))):
                            next_text = lessons_list[j].get('text', '').strip()
                            # Nur als Notiz nehmen wenn es NICHT wie ein Raum aussieht
                            if next_text and len(next_text) < 50 and not ':' in next_text:
                                if not re.match(r'O\d{3,4}', next_text):
                                    note = next_text
                                    break
                
                # Stop bei nächster lesson-card
                class_name = item.get('className', '')
                if i > start_index and 'lesson-card' in class_name and 'lesson-card-' not in class_name:
                    break
            
            # Fallback: Versuche Raum aus main_text zu extrahieren wenn nicht gefunden
            if not room or room == 'N/A':
                # Pattern: Nach Lehrername und Fach kommt Raumnummer
                # "12:5014:20FayKLitO1027, +O1101, +O1102+2"
                # Entferne Zeiten und suche nach O + Zahlen
                room_match = re.search(r'(O\d{3,4}(?:,\s*\+O\d{3,4})*)', main_text)
                if room_match:
                    room = room_match.group(1)
            
            if start_time and end_time:
                # Wenn wir einen Hinweis haben, füge ihn zur Beschreibung hinzu aber nicht zum Raum
                final_room = room or 'N/A'
                
                # Erstelle Lesson mit optionalem Hinweis
                lesson = UntisLesson(
                    start_time=start_time,
                    end_time=end_time,
                    subject=subject or 'Unbekannt',
                    teacher=teacher or 'N/A',
                    room=final_room,
                    date=lesson_date_str
                )
                
                # Füge Hinweis als Attribut hinzu (für spätere Nutzung)
                if note:
                    lesson.note = note
                
                return lesson
        
        except Exception as e:
            print(f"  ⚠ Fehler: {e}")
        
        return None

class GoogleCalendarSync:
    """Synchronisiert mit Google Calendar - mit Duplikat-Erkennung"""
    
    def __init__(self, calendar_id: str = 'primary'):
        self.calendar_id = calendar_id
        self.service = self._authenticate()
        self.existing_events = self._load_existing_events()
    
    def _authenticate(self):
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
    
    def _load_existing_events(self) -> Dict[str, str]:
        """Lade existierende Events um Duplikate zu vermeiden"""
        existing_by_uid = {}
        existing_by_signature = {}
        
        try:
            # Hole Events - erweitere den Zeitraum und erhöhe das Limit
            now = datetime.utcnow()
            
            # Gehe 7 Tage zurück (falls alte Events vorhanden)
            time_min = (now - timedelta(days=7)).isoformat() + 'Z'
            time_max = (now + timedelta(days=90)).isoformat() + 'Z'
            
            print("  🔍 Lade existierende Events...")
            
            all_events = []
            page_token = None
            
            # Paginate durch ALLE Events (nicht nur erste 1000)
            while True:
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=2500,  # Maximum pro Request
                    singleEvents=True,
                    orderBy='startTime',
                    pageToken=page_token
                ).execute()
                
                events = events_result.get('items', [])
                all_events.extend(events)
                
                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break
            
            print(f"  📊 {len(all_events)} Events im Zeitraum gefunden")
            
            # Filtere nur Events die wie Untis-Events aussehen
            untis_count = 0
            
            for event in all_events:
                summary = event.get('summary', '')
                location = event.get('location', '')
                
                # Prüfe ob es ein Untis-Event sein könnte
                # Kriterien: Kurzer Name (< 10 Zeichen) UND Raum-Pattern (O + Zahlen)
                is_short_name = len(summary) <= 10
                has_room_pattern = location and (
                    location.startswith('O') and any(c.isdigit() for c in location)
                )
                
                # Nur Events die beides haben sind wahrscheinlich Untis-Events
                if not (is_short_name and has_room_pattern):
                    continue
                
                untis_count += 1
                
                # Methode 1: Per untis_uid
                extended = event.get('extendedProperties', {}).get('private', {})
                uid = extended.get('untis_uid')
                if uid:
                    existing_by_uid[uid] = event['id']
                
                # Methode 2: Per Signatur
                try:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    
                    if 'T' in start:
                        # Parse als datetime
                        if start.endswith('Z'):
                            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromisoformat(start)
                        
                        date_str = dt.strftime('%Y-%m-%d')
                        time_str = dt.strftime('%H:%M')
                        
                        # Erstelle Signatur: Datum_Zeit_Fach_Raum
                        signature = f"{date_str}_{time_str}_{summary}_{location}"
                        existing_by_signature[signature] = event['id']
                except Exception as e:
                    print(f"  ⚠ Fehler beim Parsen von Event: {e}")
            
            print(f"  ✓ {untis_count} Untis-Events erkannt")
            print(f"    - {len(existing_by_uid)} mit UID")
            print(f"    - {len(existing_by_signature)} mit Signatur")
        
        except Exception as e:
            print(f"  ⚠ Fehler beim Laden: {e}")
            import traceback
            traceback.print_exc()
        
        return {
            'by_uid': existing_by_uid,
            'by_signature': existing_by_signature
        }
    
    def create_event(self, lesson: UntisLesson, skip_duplicates: bool = True) -> Optional[str]:
        """Erstellt ein Event - mit verbesserter Duplikat-Prüfung"""
        try:
            # Prüfe auf Duplikate - Methode 1: Per UID
            if skip_duplicates and lesson.uid in self.existing_events['by_uid']:
                return 'DUPLICATE_UID'
            
            start_datetime = datetime.strptime(
                f"{lesson.date} {lesson.start_time}", 
                "%Y-%m-%d %H:%M"
            )
            end_datetime = datetime.strptime(
                f"{lesson.date} {lesson.end_time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Prüfe auf Duplikate - Methode 2: Per Signatur
            # Normalisiere Raum genauso wie für UID
            room_parts = [r.strip() for r in lesson.room.split(',')]
            room_normalized = None
            for part in room_parts:
                clean_part = part.lstrip('+').strip()
                if clean_part and clean_part != 'N/A':
                    room_normalized = clean_part
                    break
            if not room_normalized:
                room_normalized = room_parts[0].lstrip('+').strip() if room_parts else lesson.room
            
            signature = f"{lesson.date}_{lesson.start_time}_{lesson.subject}_{room_normalized}"
            if skip_duplicates and signature in self.existing_events['by_signature']:
                return 'DUPLICATE_SIG'
            
            # Erstelle Beschreibung mit optionaler Notiz
            description_parts = [f'Lehrer: {lesson.teacher}', f'Raum: {lesson.room}']
            if hasattr(lesson, 'note') and lesson.note:
                description_parts.append(f'📝 {lesson.note}')
            description = '\n'.join(description_parts)
            
            event = {
                'summary': lesson.subject,
                'location': lesson.room,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/Berlin',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Berlin',
                },
                'colorId': '6',  # Orange (passend zu Untis)
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
                'extendedProperties': {
                    'private': {
                        'untis_uid': lesson.uid,
                        'untis_source': 'automated_sync'
                    }
                }
            }
            
            event_result = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            # Speichere in existierenden Events (WICHTIG!)
            event_id = event_result.get('id')
            self.existing_events['by_uid'][lesson.uid] = event_id
            self.existing_events['by_signature'][signature] = event_id
            
            return event_id
        
        except HttpError as error:
            print(f'  ✗ HTTP Error: {error}')
            return None
    
    def sync_lessons(self, lessons: List[UntisLesson], dry_run: bool = False):
        """Synchronisiert alle Lessons"""
        print(f"\n{'='*60}")
        print(f"Synchronisiere {len(lessons)} Lessons...")
        print(f"{'='*60}\n")
        
        created = 0
        duplicates = 0
        failed = 0
        
        for i, lesson in enumerate(lessons, 1):
            print(f"[{i}/{len(lessons)}] {lesson.date} {lesson.subject} ({lesson.start_time}-{lesson.end_time}) @ {lesson.room}", end='')
            
            if dry_run:
                print(" ✓ (Dry-Run)")
                created += 1
            else:
                result = self.create_event(lesson)
                if result in ['DUPLICATE_UID', 'DUPLICATE_SIG']:
                    print(" ⊘ (Duplikat)")
                    duplicates += 1
                elif result:
                    print(" ✓")
                    created += 1
                else:
                    print(" ✗")
                    failed += 1
        
        print(f"\n{'='*60}")
        print(f"✓ Neu erstellt: {created}")
        if duplicates > 0:
            print(f"⊘ Übersprungen (Duplikate): {duplicates}")
        if failed > 0:
            print(f"✗ Fehlgeschlagen: {failed}")
        print(f"{'='*60}\n")
    
    def sync_lessons_silent(self, lessons: List[UntisLesson]) -> tuple:
        """Synchronisiert Lessons ohne viel Output (für Automatisierung)"""
        created = 0
        duplicates = 0
        failed = 0
        
        for lesson in lessons:
            result = self.create_event(lesson)
            if result in ['DUPLICATE_UID', 'DUPLICATE_SIG']:
                duplicates += 1
            elif result:
                created += 1
            else:
                failed += 1
        
        return (created, duplicates, failed)

def main():
    """Hauptprogramm"""
    print("="*60)
    print("📅 WebUntis zu Google Calendar Sync (Verbessert)")
    print("="*60 + "\n")
    
    json_file = 'manual_data.json'
    
    if not os.path.exists(json_file):
        print(f"❌ {json_file} nicht gefunden!\n")
        print("📋 ANLEITUNG: Daten aus WebUntis extrahieren\n")
        print("1. Öffne WebUntis und gehe zu einer WOCHE deines Stundenplans")
        print("2. Drücke F12 → Console")
        print("3. Kopiere diesen Code:\n")
        print("""
const data = {localStorage: {}, timetable: {url: window.location.href, lessons: []}};
for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    data.localStorage[key] = localStorage.getItem(key);
}
const selectors = ['div[class*="lesson"]'];
for (const selector of selectors) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
        elements.forEach((el, i) => {
            data.timetable.lessons.push({
                index: i, text: el.textContent.trim(),
                html: el.innerHTML.substring(0, 300),
                className: el.className, dataset: {...el.dataset}
            });
        });
        break;
    }
}
copy(JSON.stringify(data, null, 2));
console.log('✓ Kopiert! Füge in manual_data.json ein');
        """)
        print("\n4. Füge die kopierten Daten in 'manual_data.json' ein")
        print("5. Führe das Script erneut aus\n")
        return
    
    print(f"📖 Lese {json_file}...")
    parser = ImprovedUntisParser(json_file)
    
    print("🔍 Parse Lessons...\n")
    lessons = parser.parse_lessons()
    
    print(f"\n✓ {len(lessons)} Lessons gefunden!")
    
    # Gruppiere nach Datum
    by_date = {}
    for lesson in lessons:
        if lesson.date not in by_date:
            by_date[lesson.date] = []
        by_date[lesson.date].append(lesson)
    
    print(f"📅 Über {len(by_date)} Tage verteilt:\n")
    for date in sorted(by_date.keys()):
        count = len(by_date[date])
        weekday = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
        print(f"  {date} ({weekday}): {count} Lessons")
    
    # Speichere
    with open('parsed_lessons.json', 'w', encoding='utf-8') as f:
        json.dump([l.to_dict() for l in lessons], f, indent=2, ensure_ascii=False)
    print(f"\n💾 Gespeichert: parsed_lessons.json\n")
    
    print("="*60)
    response = input("Zu Google Calendar hinzufügen? (j/n/d für dry-run): ").lower()
    
    if response in ['j', 'y', 'd']:
        dry_run = (response == 'd')
        
        try:
            syncer = GoogleCalendarSync()
            syncer.sync_lessons(lessons, dry_run=dry_run)
            
            if not dry_run:
                print("✅ Synchronisation abgeschlossen!")
                print("🌐 Öffne Google Calendar!\n")
        
        except Exception as e:
            print(f"\n❌ Fehler: {e}\n")
    else:
        print("\n✋ Abgebrochen.\n")

if __name__ == "__main__":
    main()
