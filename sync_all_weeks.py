#!/usr/bin/env python3
"""
Sync alle Wochen zu Google Calendar
Liest alle week_*.json Dateien, parsed sie und synchronisiert zu Google Calendar
"""

import os
import sys
import json
import glob
from pathlib import Path
from untis_sync_improved import ImprovedUntisParser, GoogleCalendarSync, UntisLesson

def sync_all_weeks():
    print("=" * 60)
    print("📅 WebUntis Multi-Week Sync zu Google Calendar")
    print("=" * 60)
    
    # Finde alle week_*.json Dateien
    week_files = sorted(glob.glob('weekly_data/week_*.json'))
    
    if not week_files:
        print("\n❌ Keine weekly_data/week_*.json gefunden!")
        print("   Führe zuerst extractor.py aus!")
        return 1
    
    print(f"\n📁 {len(week_files)} Wochen gefunden:")
    for f in week_files:
        print(f"   - {f}")
    
    # Parse alle Wochen
    all_lessons = []
    
    for week_file in week_files:
        week_num = Path(week_file).stem.split('_')[1]
        
        print(f"\n{'='*60}")
        print(f"📖 Verarbeite Woche {week_num}: {week_file}")
        print(f"{'='*60}")
        
        try:
            parser = ImprovedUntisParser(week_file)
            lessons = parser.parse_lessons()
            
            if len(lessons) == 0:
                print(f"⚠️  Keine Lessons gefunden - möglicherweise Ferien oder kein Stundenplan veröffentlicht")
            else:
                print(f"✓ {len(lessons)} Lessons aus Woche {week_num} geparsed")
                
                # Zeige Datum-Range
                if lessons:
                    dates = sorted(set(l.date for l in lessons))
                    print(f"  Datumsbereich: {dates[0]} bis {dates[-1]}")
            
            all_lessons.extend(lessons)
            
        except Exception as e:
            print(f"❌ Fehler beim Parsen von Woche {week_num}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not all_lessons:
        print("\n❌ Keine Lessons gefunden!")
        return 1
    
    # Sortiere alle Lessons
    all_lessons.sort(key=lambda l: (l.date, l.start_time))
    
    print(f"\n{'='*60}")
    print(f"📊 GESAMT: {len(all_lessons)} Lessons")
    print(f"{'='*60}")
    
    # Gruppiere nach Datum für Übersicht
    from datetime import datetime
    by_date = {}
    for lesson in all_lessons:
        if lesson.date not in by_date:
            by_date[lesson.date] = []
        by_date[lesson.date].append(lesson)
    
    print(f"\n📅 Über {len(by_date)} Tage verteilt:\n")
    for date in sorted(by_date.keys()):
        count = len(by_date[date])
        weekday = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
        print(f"  {date} ({weekday}): {count} Lessons")
    
    # Speichere kombinierte Lessons
    output_file = 'parsed_lessons_all_weeks.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([l.to_dict() for l in all_lessons], f, indent=2, ensure_ascii=False)
    print(f"\n💾 Gespeichert: {output_file}")
    
    # Synchronisiere zu Google Calendar
    print(f"\n{'='*60}")
    print("🔄 Synchronisiere zu Google Calendar...")
    print(f"{'='*60}\n")
    
    try:
        syncer = GoogleCalendarSync()
        created, duplicates, failed = syncer.sync_lessons_silent(all_lessons)
        
        print(f"\n{'='*60}")
        print("✅ Synchronisation abgeschlossen!")
        print(f"{'='*60}")
        print(f"✓ Neu erstellt: {created}")
        print(f"⊘ Übersprungen (Duplikate): {duplicates}")
        if failed > 0:
            print(f"✗ Fehlgeschlagen: {failed}")
        print(f"{'='*60}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Fehler bei Google Calendar Sync: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(sync_all_weeks())

