#!/bin/bash
# Quick Status Check - Zeigt aktuellen Status an

echo "════════════════════════════════════════════════════════"
echo "🤖 Untis Calendar Sync - System Status"
echo "════════════════════════════════════════════════════════"
echo ""

# Crontab Status
echo "⏰ CRONTAB:"
crontab -l | grep -E "auto_sync|run_full_sync" | sed 's/^/   /'
echo ""

# Server Status
if pgrep -f status_server.py > /dev/null; then
    PID=$(pgrep -f status_server.py)
    echo "🌐 STATUS SERVER: ✅ Läuft (PID: $PID)"
    echo "   Dashboard: http://localhost:8080/dashboard"
    echo "   JSON API:  http://localhost:8080/status"
else
    echo "🌐 STATUS SERVER: ❌ Gestoppt"
    echo "   Starten: nohup python3 status_server.py > logs/status_server.log 2>&1 &"
fi
echo ""

# Sync Status
cd /opt/UntisCalSync
python3 status_api.py --json > /tmp/status.json 2>/dev/null

LAST_SYNC=$(python3 -c "import json; data=json.load(open('/tmp/status.json')); print(data.get('last_sync', 'Nie'))" 2>/dev/null || echo "Nie")
NEXT_SYNC=$(python3 -c "import json; data=json.load(open('/tmp/status.json')); print(data.get('next_sync', 'Unbekannt'))" 2>/dev/null || echo "Unbekannt")
WEEKS=$(python3 -c "import json; data=json.load(open('/tmp/status.json')); print(data.get('weeks_extracted', 0))" 2>/dev/null || echo "0")
LESSONS=$(python3 -c "import json; data=json.load(open('/tmp/status.json')); print(data.get('total_lessons', 0))" 2>/dev/null || echo "0")

echo "📊 SYNC STATUS:"
echo "   Letzter Sync: $LAST_SYNC"

if [ "$NEXT_SYNC" != "Unbekannt" ] && [ "$NEXT_SYNC" != "null" ]; then
    NEXT_TS=$(date -d "$NEXT_SYNC" +%s 2>/dev/null || echo "0")
    NOW_TS=$(date +%s)
    if [ "$NEXT_TS" != "0" ]; then
        MINS_LEFT=$(( ($NEXT_TS - $NOW_TS) / 60 ))
        if [ $MINS_LEFT -gt 0 ]; then
            echo "   Nächster in: $MINS_LEFT Minuten"
        else
            echo "   Nächster in: überfällig"
        fi
    fi
fi

echo "   Wochen: $WEEKS | Lessons: $LESSONS"
echo ""

# Letzte Log-Einträge
echo "📝 LETZTE LOGS:"
if [ -f logs/cron.log ]; then
    tail -3 logs/cron.log | sed 's/^/   /'
else
    echo "   Noch keine Logs vorhanden"
fi
echo ""

echo "════════════════════════════════════════════════════════"
echo "💡 Befehle:"
echo "   Status:     python3 status_api.py"
echo "   Dashboard:  xdg-open http://localhost:8080/dashboard"
echo "   Quick-Sync: python3 quick_sync.py"
echo "   Full-Sync:  ./run_full_sync.sh"
echo "════════════════════════════════════════════════════════"
