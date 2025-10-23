#!/usr/bin/env python3
"""
Simple HTTP Server für Status API
Zeigt Sync-Status auf http://localhost:8080
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys

# Importiere unsere Status-Funktion
sys.path.insert(0, '/opt/UntisCalSync')
from status_api import get_sync_status

class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/status':
            # JSON Status
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            status = get_sync_status()
            self.wfile.write(json.dumps(status, indent=2).encode())
        
        elif self.path == '/dashboard':
            # HTML Dashboard
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = self.generate_dashboard()
            self.wfile.write(html.encode())
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def generate_dashboard(self):
        """Generiere HTML Dashboard"""
        status = get_sync_status()
        
        from datetime import datetime
        
        # Berechne Zeit bis nächstem Update
        if status['next_sync']:
            next_dt = datetime.fromisoformat(status['next_sync'])
            minutes_until = int((next_dt - datetime.now()).total_seconds() / 60)
            next_update = f"{minutes_until} Minuten"
        else:
            next_update = "Unbekannt"
        
        # Änderungen heute
        changes_today_html = ""
        if status['changes_today']:
            for change in status['changes_today']:
                time_fmt = f"{change['time'][:2]}:{change['time'][2:4]}"
                changes_today_html += f"<li>{time_fmt} - {change['created']} Events hinzugefügt</li>"
        else:
            changes_today_html = "<li>Keine Änderungen</li>"
        
        # Änderungen Woche
        changes_week_html = ""
        if status['changes_this_week']:
            for change in status['changes_this_week'][:7]:
                time_fmt = f"{change['time'][:2]}:{change['time'][2:4]}"
                changes_week_html += f"<li>{change['date']} {time_fmt} - {change['created']} Events</li>"
        else:
            changes_week_html = "<li>Keine Änderungen</li>"
        
        html = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Untis Sync Status</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 800px;
            width: 100%;
            padding: 40px;
        }}
        h1 {{
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-align: center;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }}
        .status-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        .status-card h2 {{
            font-size: 1.5em;
            margin-bottom: 15px;
        }}
        .status-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }}
        .status-item:last-child {{ border-bottom: none; }}
        .status-label {{ font-weight: 500; }}
        .status-value {{ font-weight: 700; }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h3 {{
            color: #333;
            font-size: 1.3em;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #667eea;
        }}
        ul {{
            list-style: none;
            padding-left: 0;
        }}
        li {{
            padding: 10px 15px;
            background: #f8f9fa;
            margin-bottom: 8px;
            border-radius: 8px;
            color: #333;
        }}
        .footer {{
            text-align: center;
            color: #999;
            margin-top: 30px;
            font-size: 0.9em;
        }}
        .refresh-info {{
            text-align: center;
            background: #e3f2fd;
            padding: 15px;
            border-radius: 10px;
            color: #1976d2;
            margin-bottom: 20px;
        }}
    </style>
    <script>
        // Auto-refresh alle 60 Sekunden
        setTimeout(function(){{ location.reload(); }}, 60000);
    </script>
</head>
<body>
    <div class="container">
        <h1>📅 Untis Calendar Sync</h1>
        <p class="subtitle">Automatische Synchronisation mit Google Calendar</p>
        
        <div class="refresh-info">
            🔄 Seite aktualisiert sich automatisch jede Minute
        </div>
        
        <div class="status-card">
            <h2>⏰ Sync Status</h2>
            <div class="status-item">
                <span class="status-label">Letzter Sync:</span>
                <span class="status-value">{status['last_sync'] or 'Nie'}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Nächster Update:</span>
                <span class="status-value">{next_update}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Extrahierte Wochen:</span>
                <span class="status-value">{status['weeks_extracted']}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Gesamt Lessons:</span>
                <span class="status-value">{status['total_lessons']}</span>
            </div>
        </div>
        
        <div class="section">
            <h3>📝 Änderungen Heute</h3>
            <ul>
                {changes_today_html}
            </ul>
        </div>
        
        <div class="section">
            <h3>📅 Änderungen Diese Woche</h3>
            <ul>
                {changes_week_html}
            </ul>
        </div>
        
        <div class="footer">
            <p>🤖 Automatischer Sync alle 30 Minuten</p>
            <p>🔗 JSON API: <a href="/status">/status</a></p>
        </div>
    </div>
</body>
</html>
        """
        return html
    
    def log_message(self, format, *args):
        # Unterdrücke Standard-Logs
        pass

def main():
    PORT = 8080
    
    os.chdir('/opt/UntisCalSync')
    
    print("="*60)
    print("🌐 Status Server gestartet")
    print("="*60)
    print(f"\n📊 Dashboard: http://localhost:{PORT}/dashboard")
    print(f"📡 JSON API:  http://localhost:{PORT}/status")
    print(f"\n🔄 Auto-Refresh: Seite aktualisiert sich jede Minute")
    print(f"\n⚠️  Drücke Ctrl+C zum Beenden\n")
    
    server = HTTPServer(('0.0.0.0', PORT), StatusHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✋ Server gestoppt")
        server.shutdown()

if __name__ == '__main__':
    main()
