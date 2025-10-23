#!/usr/bin/env python3
"""
Manual Google Auth für Headless Server
Erstellt token.pickle ohne Browser
"""

import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

def main():
    print("="*60)
    print("🔐 Google Calendar Authentifizierung (Headless Mode)")
    print("="*60)
    
    # Starte Flow ohne lokalen Server
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', 
        SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )
    
    # Zeige Auth URL
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    print('\n📋 ANLEITUNG:')
    print('1. Kopiere die URL unten')
    print('2. Öffne sie in einem Browser')
    print('3. Logge dich in Google ein')
    print('4. Autorisiere die App')
    print('5. Google zeigt dir einen CODE')
    print('6. Kopiere den Code und füge ihn hier ein\n')
    
    print('='*60)
    print('🔗 AUTH URL:')
    print('='*60)
    print(auth_url)
    print('='*60)
    
    # Warte auf Code-Eingabe
    code = input('\n✋ Gib den Autorisierungs-Code hier ein: ').strip()
    
    if not code:
        print('\n❌ Kein Code eingegeben. Abbruch.')
        return 1
    
    try:
        # Hole Token
        print('\n🔄 Hole Access Token...')
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Speichere
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        
        print('\n' + '='*60)
        print('✅ ERFOLG!')
        print('='*60)
        print('token.pickle wurde erstellt!')
        print('Du kannst jetzt auto_sync.py ausführen.')
        print('='*60 + '\n')
        
        return 0
        
    except Exception as e:
        print(f'\n❌ Fehler: {e}')
        print('Bitte stelle sicher dass der Code korrekt ist.')
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
