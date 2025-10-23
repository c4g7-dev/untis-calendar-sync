#!/usr/bin/env python3
"""
Status API - Zeigt aktuellen Sync-Status
Kann als JSON endpoint verwendet werden
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import glob

def get_sync_status():
    """Hole aktuellen Status"""
    
    status = {
        'current_time': datetime.now().isoformat(),
        'last_sync': None,
        'next_sync': None,
        'weeks_extracted': 0,
        'total_lessons': 0,
        'changes_today': [],
        'changes_this_week': []
    }
    
    # Lese letzten Sync-Status
    if os.path.exists('sync_status.json'):
        with open('sync_status.json', 'r') as f:
            sync_data = json.load(f)
            status['last_sync'] = sync_data.get('last_sync')
            if 'next_sync' in sync_data:
                next_sync_ts = sync_data['next_sync']
                status['next_sync'] = datetime.fromtimestamp(next_sync_ts).isoformat()
    
    # Zähle extrahierte Wochen
    week_files = glob.glob('weekly_data/week_*.json')
    status['weeks_extracted'] = len(week_files)
    
    # Zähle Lessons
    if os.path.exists('parsed_lessons_all_weeks.json'):
        with open('parsed_lessons_all_weeks.json', 'r') as f:
            lessons = json.load(f)
            status['total_lessons'] = len(lessons)
    
    # Analysiere Log-Dateien für Änderungen
    log_files = sorted(glob.glob('logs/full_sync_*.log'), reverse=True)
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    for log_file in log_files[:10]:  # Letzte 10 Logs
        # Extrahiere Datum aus Dateinamen: full_sync_20251023_220106.log
        try:
            basename = Path(log_file).stem
            date_str = basename.split('_')[2]  # 20251023
            log_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            # Lese Log
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Extrahiere Statistiken
            if '✓ Neu erstellt:' in content:
                import re
                match = re.search(r'✓ Neu erstellt: (\d+)', content)
                if match:
                    created = int(match.group(1))
                    
                    change_entry = {
                        'date': log_date.isoformat(),
                        'created': created,
                        'time': basename.split('_')[3][:6]  # HHMMSS -> HHMMSS
                    }
                    
                    if log_date == today:
                        status['changes_today'].append(change_entry)
                    
                    if log_date >= week_ago:
                        status['changes_this_week'].append(change_entry)
        
        except Exception as e:
            continue
    
    return status

def main():
    """Hauptprogramm"""
    import sys
    
    os.chdir('/opt/UntisCalSync')
    
    status = get_sync_status()
    
    # Wenn --json Flag, nur JSON ausgeben
    if '--json' in sys.argv:
        print(json.dumps(status, indent=2))
    else:
        # Hübsche Ausgabe
        print("="*60)
        print("📊 Untis Sync Status")
        print("="*60)
        
        print(f"\n⏰ Aktuelle Zeit: {status['current_time']}")
        
        if status['last_sync']:
            print(f"🔄 Letzter Sync: {status['last_sync']}")
        else:
            print("🔄 Letzter Sync: Noch nie ausgeführt")
        
        if status['next_sync']:
            next_dt = datetime.fromisoformat(status['next_sync'])
            minutes_until = int((next_dt - datetime.now()).total_seconds() / 60)
            print(f"⏭️  Nächster Sync: {status['next_sync']} (in {minutes_until} Min)")
        
        print(f"\n📁 Extrahierte Wochen: {status['weeks_extracted']}")
        print(f"📅 Gesamt Lessons: {status['total_lessons']}")
        
        if status['changes_today']:
            print(f"\n📝 Änderungen heute ({len(status['changes_today'])}):")
            for change in status['changes_today']:
                time_fmt = f"{change['time'][:2]}:{change['time'][2:4]}:{change['time'][4:]}"
                print(f"   {time_fmt} - {change['created']} Events hinzugefügt")
        else:
            print("\n📝 Keine Änderungen heute")
        
        if status['changes_this_week']:
            print(f"\n📅 Änderungen diese Woche ({len(status['changes_this_week'])}):")
            for change in status['changes_this_week'][:5]:  # Zeige nur erste 5
                time_fmt = f"{change['time'][:2]}:{change['time'][2:4]}"
                print(f"   {change['date']} {time_fmt} - {change['created']} Events")
        
        print("\n" + "="*60)

if __name__ == '__main__':
    main()
