#!/usr/bin/env python3
"""
Quick Sync - Schneller Update ohne vollen Resync
Nur für bereits extrahierte Daten
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

def quick_sync():
    """Schneller Sync der bereits extrahierten Daten"""
    
    print("="*60)
    print("🔄 Quick Sync - Update Calendar")
    print("="*60)
    
    # Prüfe ob Daten vorhanden
    week_files = list(Path('weekly_data').glob('week_*.json'))
    
    if not week_files:
        print("\n⚠️  Keine Daten gefunden - führe vollen Sync aus")
        print("   Verwende: ./run_full_sync.sh")
        return 1
    
    print(f"\n📁 {len(week_files)} Wochen-Dateien gefunden")
    
    # Führe nur Sync aus (keine Extraktion)
    os.chdir('/opt/UntisCalSync')
    import subprocess
    subprocess.run(['/opt/UntisCalSync/venv/bin/python3', 'sync_all_weeks.py'])
    
    # Speichere letzten Sync-Zeitpunkt
    status = {
        'last_sync': datetime.now().isoformat(),
        'next_sync': (datetime.now().timestamp() + 1800),  # +30 Minuten
        'status': 'success'
    }
    
    with open('sync_status.json', 'w') as f:
        json.dump(status, f, indent=2)
    
    print("\n✅ Quick Sync abgeschlossen!")
    return 0

if __name__ == '__main__':
    sys.exit(quick_sync())
