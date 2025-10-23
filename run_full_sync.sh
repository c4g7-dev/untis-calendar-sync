#!/bin/bash
# WebUntis Full Sync Script
# Extrahiert Daten von WebUntis und synchronisiert zu Google Calendar

set -e  # Stop bei Fehler

cd /opt/UntisCalSync
source venv/bin/activate

# Lade .env und exportiere Variablen
set -a  # Auto-export alle Variablen
source .env
set +a

LOG_FILE="logs/full_sync_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

# Funktion für Logging (Console + File)
log() {
    echo "$1" | tee -a "$LOG_FILE"
}

log "========================================"
log "🚀 WebUntis Full Sync gestartet"
log "⏰ Zeit: $(date '+%Y-%m-%d %H:%M:%S')"
log "========================================"
log ""

# 1. Extrahiere von WebUntis
log "📥 Schritt 1: Extrahiere Daten von WebUntis..."
log "   Schule: $UNTIS_SCHOOL"
log "   User: $UNTIS_USERNAME"
log "   Wochen: $UNTIS_WEEKS"
log ""

if python3 extractor.py >> "$LOG_FILE" 2>&1; then
    log "✅ Extraktion erfolgreich!"
    
    # Zähle extrahierte Dateien
    WEEK_COUNT=$(ls -1 weekly_data/week_*.json 2>/dev/null | wc -l)
    log "   📁 $WEEK_COUNT Wochen-Dateien erstellt"
    log ""
    
    # 2. Sync ALLE Wochen zu Google Calendar
    log "📤 Schritt 2: Synchronisiere ALLE Wochen zu Google Calendar..."
    
    # Nutze sync_all_weeks.py statt auto_sync.py
    if python3 sync_all_weeks.py 2>&1 | tee -a "$LOG_FILE"; then
        log ""
        log "✅ Google Calendar Sync erfolgreich!"
        
        # Zähle Events
        if [ -f "parsed_lessons_all_weeks.json" ]; then
            EVENT_COUNT=$(python3 -c "import json; print(len(json.load(open('parsed_lessons_all_weeks.json'))))" 2>/dev/null || echo "?")
            log "   📅 $EVENT_COUNT Events total verarbeitet"
        fi
    else
        log "❌ Google Calendar Sync fehlgeschlagen!"
        log "   Siehe Log für Details: $LOG_FILE"
        exit 1
    fi
else
    log "❌ Extraktion fehlgeschlagen!"
    log "   Mögliche Gründe:"
    log "   - WebUntis Login fehlgeschlagen"
    log "   - Netzwerkproblem"
    log "   - Browser-Fehler"
    log "   Siehe Log für Details: $LOG_FILE"
    exit 1
fi

log ""
log "========================================"
log "🎉 Sync abgeschlossen!"
log "⏰ Fertig: $(date '+%Y-%m-%d %H:%M:%S')"
log "📊 Log: $LOG_FILE"
log "========================================"

exit 0
