#!/bin/bash
# Auto-Sync Script - Für Cron alle 30 Minuten
# Macht nur Quick-Sync, kein Full-Extraction

set -e

cd /opt/UntisCalSync
source venv/bin/activate

LOG_FILE="logs/auto_sync_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

# Logging Funktion
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================"
log "🤖 Auto-Sync gestartet (alle 30 Min)"
log "========================================"

# IMMER voller Sync - Änderungen kommen von WebUntis!
log "� Führe VOLLEN Sync aus (WebUntis → Google Calendar)"
./run_full_sync.sh >> "$LOG_FILE" 2>&1

# Status aktualisieren
STATUS_JSON="sync_status.json"
cat > "$STATUS_JSON" << EOF
{
  "last_sync": "$(date -Iseconds)",
  "next_sync": $(date -d "+30 minutes" +%s),
  "status": "success",
  "type": "full"
}
EOF

log "✅ Auto-Sync abgeschlossen"
log "📊 Log: $LOG_FILE"
log "========================================"

exit 0
