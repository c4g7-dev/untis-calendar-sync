#!/usr/bin/env python3
"""
Automatischer WebUntis Data Extractor
Nutzt Selenium um sich einzuloggen und Daten zu extrahieren
"""

import json
import time
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

class UntisAutoExtractor:
    """Automatischer WebUntis Data Extractor"""
    
    def __init__(self, school_name, username, password, headless=True):
        self.school_name = school_name
        self.username = username
        self.password = password
        self.headless = headless
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome/Chromium/Firefox Driver"""
        # Versuche zuerst Chrome/Chromium
        try:
            options = Options()
            
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            
            # Versuche verschiedene Chrome/Chromium Pfade
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/usr/bin/chrome',
            ]
            
            for chrome_path in chrome_paths:
                try:
                    if os.path.exists(chrome_path):
                        options.binary_location = chrome_path
                        self.driver = webdriver.Chrome(options=options)
                        print(f"✓ Chrome gefunden: {chrome_path}")
                        return
                except Exception as e:
                    continue
            
            # Versuche ohne expliziten Pfad
            self.driver = webdriver.Chrome(options=options)
            print("✓ Chrome gefunden (default)")
            return
            
        except Exception as chrome_error:
            print(f"⚠ Chrome nicht verfügbar: {chrome_error}")
            print("Versuche Firefox...")
        
        # Fallback: Firefox
        try:
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            
            firefox_options = FirefoxOptions()
            
            if self.headless:
                firefox_options.add_argument('--headless')
            
            firefox_options.add_argument('--no-sandbox')
            
            self.driver = webdriver.Firefox(options=firefox_options)
            print("✓ Firefox gefunden")
            return
            
        except Exception as firefox_error:
            print(f"❌ Firefox nicht verfügbar: {firefox_error}")
        
        # Wenn nichts funktioniert
        print("\n" + "="*60)
        print("❌ Kein Browser gefunden!")
        print("="*60)
        print("\nInstalliere einen Browser:")
        print("\n# Option 1: Google Chrome (empfohlen)")
        print("wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -")
        print("echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list")
        print("sudo apt update")
        print("sudo apt install -y google-chrome-stable")
        print("\n# Option 2: Firefox")
        print("sudo apt install -y firefox firefox-geckodriver")
        print("\n# Option 3: Chromium (von PPA)")
        print("sudo add-apt-repository ppa:savoury1/chromium -y")
        print("sudo apt update")
        print("sudo apt install -y chromium-browser")
        print("="*60 + "\n")
        
        raise Exception("Kein Browser installiert")
    
    def login(self):
        """Login zu WebUntis"""
        print("🌐 Öffne WebUntis Login...")
        
        # URL mit + für Leerzeichen (wie WebUntis es erwartet)
        school_encoded = self.school_name.replace(' ', '+')
        
        # Die korrekte URL-Struktur
        login_url = f'https://ajax.webuntis.com/WebUntis/?school={school_encoded}#/basic/login'
        
        print(f"📍 URL: {login_url}")
        self.driver.get(login_url)
        
        # Warte bis JavaScript geladen (SPA)
        print("⏳ Warte auf App (JavaScript lädt)...")
        time.sleep(10)  # SPA braucht Zeit
        
        # Prüfe aktuelle URL
        current_url = self.driver.current_url
        print(f"📍 Aktuelle URL: {current_url}")
        
        # Debug Screenshot
        try:
            os.makedirs('debug', exist_ok=True)
            self.driver.save_screenshot('debug/1_login_page.png')
            print("📸 Screenshot: debug/1_login_page.png")
        except:
            pass
        
        # Wenn zu webuntis.com umgeleitet (school not found)
        if 'webuntis.com' in current_url and 'ajax.webuntis.com' not in current_url:
            print("❌ Wurde zu webuntis.com umgeleitet - Schule nicht gefunden!")
            print("📍 Current URL:", current_url)
            self.driver.save_screenshot('debug/error_redirect.png')
            raise Exception(f"Schule '{self.school_name}' nicht gefunden. Prüfe Schulnamen!")
        
        # Username eingeben
        print("👤 Suche Username-Feld...")
        username_selectors = [
            'input#username',
            'input[name="username"]',
            'input[data-testid*="username"]',
            'input[placeholder*="Benutzername"]',
            'input[placeholder*="Username"]',
            'input[type="text"]',
        ]
        
        username_input = None
        for selector in username_selectors:
            try:
                username_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"  ✓ Username-Feld gefunden: {selector}")
                break
            except:
                continue
        
        if not username_input:
            print("\n❌ Username-Feld nicht gefunden!")
            print("📄 Current URL:", self.driver.current_url)
            print("📄 Page Title:", self.driver.title)
            self.driver.save_screenshot('debug/error_no_username.png')
            
            # Debug: Zeige alle Input-Felder
            inputs = self.driver.find_elements(By.TAG_NAME, 'input')
            print(f"\n📋 Gefundene Input-Felder ({len(inputs)} total):")
            for idx, inp in enumerate(inputs[:10]):
                try:
                    inp_type = inp.get_attribute('type')
                    inp_name = inp.get_attribute('name')
                    inp_id = inp.get_attribute('id')
                    inp_placeholder = inp.get_attribute('placeholder')
                    print(f"  [{idx}] type={inp_type}, name={inp_name}, id={inp_id}, placeholder={inp_placeholder}")
                except:
                    pass
            
            raise Exception("Username-Feld nicht gefunden")
        
        print("✏️  Gebe Username ein...")
        username_input.clear()
        username_input.send_keys(self.username)
        time.sleep(1)
        
        # Password eingeben
        print("🔑 Suche Password-Feld...")
        password_selectors = [
            'input#password',
            'input[name="password"]',
            'input[type="password"]',
            'input[data-testid*="password"]',
        ]
        
        password_input = None
        for selector in password_selectors:
            try:
                password_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                print(f"  ✓ Password-Feld gefunden: {selector}")
                break
            except:
                continue
        
        if not password_input:
            raise Exception("Password-Feld nicht gefunden")
        
        print("✏️  Gebe Password ein...")
        password_input.clear()
        password_input.send_keys(self.password)
        time.sleep(1)
        
        self.driver.save_screenshot('debug/2_before_login.png')
        print("📸 Screenshot: debug/2_before_login.png")
        
        # Login Button klicken
        print("🔓 Suche Login-Button...")
        login_selectors = [
            'button[type="submit"]',
            'button#login',
            'button[data-testid*="login"]',
            'button[data-testid*="submit"]',
            'input[type="submit"]',
            '.login-button',
        ]
        
        login_button = None
        for selector in login_selectors:
            try:
                login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                print(f"  ✓ Login-Button gefunden: {selector}")
                break
            except:
                continue
        
        if login_button:
            print("🖱️  Klicke Login-Button...")
            login_button.click()
        else:
            # Versuche Enter im Password-Feld
            print("  ⚠️ Kein Login-Button gefunden, drücke Enter...")
            password_input.send_keys('\n')
        
        # Warte bis eingeloggt (URL ändert sich)
        print("⏳ Warte auf Login-Response...")
        time.sleep(10)
        
        self.driver.save_screenshot('debug/3_after_login.png')
        print("📸 Screenshot: debug/3_after_login.png")
        
        # Prüfe ob eingeloggt
        current_url = self.driver.current_url
        print(f"📍 Nach Login URL: {current_url}")
        
        if 'login' in current_url.lower():
            print("⚠️  Noch auf Login-Seite!")
            print("   Mögliche Gründe:")
            print("   - Falsches Password")
            print("   - Falscher Username")
            print("   - Login-Button nicht geklickt")
            print("📸 Siehe: debug/3_after_login.png")
            
            # Zeige Fehlermeldungen falls vorhanden
            try:
                error_elements = self.driver.find_elements(By.CSS_SELECTOR, '.error, .alert, [class*="error"], [class*="alert"]')
                if error_elements:
                    print("\n⚠️  Fehlermeldungen gefunden:")
                    for elem in error_elements[:3]:
                        try:
                            text = elem.text.strip()
                            if text:
                                print(f"   - {text}")
                        except:
                            pass
            except:
                pass
            
            raise Exception("Login fehlgeschlagen - noch auf Login-Seite")
        
        elif 'school_not_found' in current_url:
            raise Exception("Schule nicht gefunden nach Login")
        
        else:
            print("✅ Login erfolgreich!")
            print(f"📍 Eingeloggt auf: {current_url}")
            
        time.sleep(2)
    
    def navigate_to_week(self, week_offset=0):
        """Navigiere zu einer bestimmten Woche"""
        # Berechne das Datum des MONTAGS der Zielwoche
        # Finde zuerst den Montag der aktuellen Woche
        today = datetime.now()
        current_weekday = today.weekday()  # 0 = Montag, 6 = Sonntag
        current_monday = today - timedelta(days=current_weekday)
        
        # Addiere die Wochen-Offset
        target_monday = current_monday + timedelta(weeks=week_offset)
        date_str = target_monday.strftime('%Y-%m-%d')
        
        # Gehe direkt zur URL mit Datum (Montag der Woche)
        url = f'https://ajax.webuntis.com/timetable/my-student?date={date_str}'
        print(f"📅 Navigiere zu Woche {week_offset+1}: {date_str} (Montag)")
        self.driver.get(url)
        
        # Warte bis Stundenplan geladen (länger für dynamisches Laden)
        print("   ⏳ Warte auf Stundenplan...")
        time.sleep(8)  # Erhöht von 5 auf 8 Sekunden
        
        # Zusätzlich: Warte bis lesson-card Elemente sichtbar sind
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, 'div[class*="lesson-card"]')) > 0
            )
            print("   ✓ Stundenplan geladen")
        except:
            print("   ⚠️ Keine lesson-cards gefunden (möglicherweise leere Woche)")
        
        return date_str
    
    def extract_data(self):
        """Extrahiere Stundenplan-Daten"""
        print("🔍 Extrahiere Daten...")
        
        # JavaScript zum Extrahieren
        js_code = """
        const data = {
            localStorage: {},
            timetable: {
                url: window.location.href,
                lessons: []
            }
        };
        
        // LocalStorage
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            data.localStorage[key] = localStorage.getItem(key);
        }
        
        // Lessons
        document.querySelectorAll('div[class*="lesson"]').forEach((el, i) => {
            data.timetable.lessons.push({
                index: i,
                text: el.textContent.trim(),
                html: el.innerHTML.substring(0, 300),
                className: el.className,
                dataset: {...el.dataset}
            });
        });
        
        return data;
        """
        
        data = self.driver.execute_script(js_code)
        
        lesson_count = len(data['timetable']['lessons'])
        
        if lesson_count == 0:
            print(f"⚠️  0 Einträge gefunden - möglicherweise Ferien oder kein Stundenplan")
        else:
            print(f"✓ {lesson_count} Einträge gefunden")
        
        return data
    
    def extract_multiple_weeks(self, num_weeks=4):
        """Extrahiere mehrere Wochen"""
        print(f"\n{'='*60}")
        print(f"📊 Extrahiere {num_weeks} Wochen")
        print(f"{'='*60}\n")
        
        all_data = []
        
        for week in range(num_weeks):
            try:
                print(f"\n--- Woche {week+1}/{num_weeks} ---")
                
                # Navigiere zur Woche
                date_str = self.navigate_to_week(week)
                
                # Extrahiere Daten
                data = self.extract_data()
                
                # Speichere
                filename = f'weekly_data/week_{week+1}.json'
                os.makedirs('weekly_data', exist_ok=True)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Gespeichert: {filename}")
                all_data.append(filename)
                
                # Pause zwischen Wochen
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Fehler bei Woche {week+1}: {e}")
        
        return all_data
    
    def run(self, num_weeks=4):
        """Hauptausführung"""
        try:
            self.setup_driver()
            self.login()
            
            # Warte bis auf Stundenplan-Seite
            time.sleep(3)
            
            # Extrahiere Wochen
            files = self.extract_multiple_weeks(num_weeks)
            
            print(f"\n{'='*60}")
            print("✅ FERTIG!")
            print(f"{'='*60}")
            print(f"📁 {len(files)} Wochen extrahiert:")
            for f in files:
                print(f"   - {f}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()

def main():
    """Hauptprogramm"""
    import sys
    
    print("="*60)
    print("🤖 WebUntis Automatischer Data Extractor")
    print("="*60 + "\n")
    
    # Konfiguration (aus Umgebungsvariablen oder Config-Datei)
    school_name = os.getenv('UNTIS_SCHOOL', 'BSZ GTW')  # Ändere das!
    username = os.getenv('UNTIS_USERNAME', 'HeidriArn')  # Ändere das!
    password = os.getenv('UNTIS_PASSWORD', '')  # Aus Sicherheitsgründen leer!
    
    # Wenn kein Password als Umgebungsvariable gesetzt
    if not password:
        print("⚠️  WARNUNG: Kein Password gefunden!")
        print("\nSetze Umgebungsvariablen:")
        print("  export UNTIS_SCHOOL='Deine Schule'")
        print("  export UNTIS_USERNAME='DeinUsername'")
        print("  export UNTIS_PASSWORD='DeinPassword'")
        print("\nODER bearbeite dieses Script und setze die Werte direkt.\n")
        
        # Fehler: Kein Password gesetzt
        print("❌ FEHLER: Kein Passwort in .env gefunden!")
        print("   Bitte setze UNTIS_PASSWORD in der .env Datei")
        import sys
        sys.exit(1)
    
    # Anzahl Wochen
    num_weeks = int(os.getenv('UNTIS_WEEKS', '4'))
    
    # Headless Mode (für Server)
    headless = os.getenv('UNTIS_HEADLESS', 'true').lower() == 'true'
    
    print(f"🏫 Schule: {school_name}")
    print(f"👤 Username: {username}")
    print(f"📅 Wochen: {num_weeks}")
    print(f"🖥️  Headless: {headless}\n")
    
    # Extrahiere
    extractor = UntisAutoExtractor(school_name, username, password, headless)
    extractor.run(num_weeks)

if __name__ == "__main__":
    main()
