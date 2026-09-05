================================================================
DEVISPRO GITHUB SECRETS — Schritt-für-Schritt Anleitung
================================================================

Du brauchst NICHTS am Mac zu installieren. Nur einen Browser.

WICHTIG: Diese Secrets muss du SELBST in GitHub setzen,
weil es deine privaten Credentials sind. Ich (der AI-Agent)
kann und darf sie nicht sehen oder eingeben — Sicherheitsregel.

================================================================
SCHRITT 1: macOS-Keychain vorbereiten (einmalig)
================================================================

Damit du das Zertifikat-Passwort später nicht eingeben musst:

1. Drücke Cmd + Leertaste → tippe "Schlüsselbund" → Enter
2. Suche nach "login" (dein Login-Schlüsselbund)
3. Doppelklick → entsperre das Schloss (du wirst nach deinem Mac-Passwort gefragt)
4. Wenn der Login-Schlüsselbund NICHT "no timeout" hat:
   - Klicke auf den Login-Schlüsselbund
   - Menü "Ablage" → "Schlüsselbund-Einstellungen"
   - Bei "Login-Schlüsselbund" auf "Info" (i)
   - Setze "Bestätigung nach" auf "Nie" ODER notiere dir das aktuelle Timeout
5. Schlüsselbund schliessen

Damit weiss dein Mac später, dass Sign-Befehle ohne Nachfrage laufen dürfen.

================================================================
SCHRITT 2: Apple Developer-ID-Zertifikat als .p2 exportieren
================================================================

Du brauchst das Zertifikat "Developer ID Application: Ferdinand
Röthlisberger (T3VS7P5X5D)" — das du schon hast (steht im sign_fix).

1. Öffne "Schlüsselbundverwaltung" (nicht -Zugriff!)
   → /Programme/Dienstprogramme/Schlüsselbundverwaltung
2. Wähle oben links: "System" (NICHT Login, Anmeldung, iCloud)
3. Wähle Kategorie "Zertifikate"
4. Suche rechts nach:
   "Developer ID Application: Ferdinand Röthlisberger (T3VS7P5X5D)"
   → Doppelklick drauf
5. Es öffnet sich ein Info-Dialog. Oben siehst du ein
   DREIEICK-Symbol: ⓘ (das ist das expand-Icon)
6. KLICKE auf das Dreieck → du siehst jetzt einen PRIVATEN SCHLÜSSEL
7. Wähle NUR das Zertifikat-Objekt (nicht den privaten Schlüssel)
   aus der Liste oben
8. Menü "Ablage" → "Objekte exportieren..."
9. Format: "Persönlicher Informationsaustausch (.p12)"
10. Speichere unter: ~/Desktop/devispro-cert.p12
11. Es fragt nach einem Passwort — kannst du LEER lassen
    (oder eines setzen — musst du dir merken)
12. Es fragt nach deinem Mac-Passwort — eingeben

Du hast jetzt eine .p12-Datei auf dem Desktop.

================================================================
SCHRITT 3: .p12-Datei base64-enkodieren
================================================================

1. Öffne "Terminal.app" (/Programme/Dienstprogramme/Terminal)
2. Kopiere diese Zeile rein:

cd ~/Desktop && base64 -i devispro-cert.p12 -o devispro-cert.p12.b64 && wc -c devispro-cert.p12.b64

3. Enter drücken
4. Es zeigt die Grösse in Bytes an
   (typischerweise zwischen 4000-6000 Bytes für ein Zertifikat)
5. Inhalt anzeigen:

cat ~/Desktop/devispro-cert.p12.b64

6. Den GANZEN Output markieren und kopieren (Cmd+A, Cmd+C)
   — der ist dein MAC_CERT_P12_BASE64 Secret

7. Optional: Aufräumen
   rm ~/Desktop/devispro-cert.p12 ~/Desktop/devispro-cert.p12.b64

================================================================
SCHRITT 4: GitHub Secrets setzen
================================================================

1. Browser öffnen
2. Gehe zu:
   https://github.com/MONTEROSSA/DevisPro/settings/secrets/actions
3. Du musst EINGELOGGT sein als MONTEROSSA-Owner
4. Klick auf "New repository secret" (grüner Button)
5. Für jeden der 7 Secrets (siehe Tabelle unten):
   - Name: exakt wie in Tabelle (Gross-/Kleinschreibung!)
   - Secret: der jeweilige Wert
   - "Add secret" klicken

TABELLE der 7 Secrets:

Name                          | Wert
------------------------------|------------------------------------------
MAC_CERT_P12_BASE64           | (Output aus Schritt 3, Schritt 6)
MAC_CERT_P12_PASSWORD         | (Passwort aus Schritt 2, Pkt 11;
. leer lassen wenn keines gesetzt)
KEYCHAIN_PASSWORD             | (dein Mac-Login-Passwort — wird zum
.                              |  Entsperren des Login-Keychain gebraucht)
APPLE_ID                      | info@monterossa.ch
APPLE_TEAM_ID                 | T3VS7P5X5D
APPLE_APP_PASSWORD            | mezr-waka-hawr-qbwb
                              | (Falls abgelaufen: neu erstellen unter
                              |  https://appleid.apple.com → App-Passwörter)
VPS_HOST                      | 187.77.79.26

Für das 7. Secret brauchst du noch den privaten VPS-SSH-Key:
(siehe Schritt 5)

================================================================
SCHRITT 5: VPS_SSH_KEY exportieren (optional aber empfohlen)
================================================================

1. Terminal.app öffnen
2. Kopiere diese Zeile:

cat ~/devis-auto/_vps_key

3. Enter drücken
4. Du siehst den Inhalt (beginnt mit
   "-----BEGIN OPENSSH PRIVATE KEY-----")
5. Den GANZEN Inhalt markieren und kopieren (Cmd+A, Cmd+C)
   — das ist dein VPS_SSH_KEY Secret
6. Falls der Key ein Passwort hat, kommt das in
   VPS_SSH_KEY_PASSWORD (8. Secret, nur falls nötig)

================================================================
SCHRITT 6: Optional — Falls APPLE_APP_PASSWORD abgelaufen
================================================================

Wenn beim Workflow-Run die Fehlermeldung kommt
"App-spezifisches Passwort abgelaufen":

1. Gehe zu https://appleid.apple.com
2. Einloggen mit info@monterossa.ch
3. Im Bereich "Anmelden & Sicherheit" →
   "App-spezifische Passwörter"
4. Neues Passwort generieren für "notarytool"
5. Das generierte Passwort (Format: xxxx-xxxx-xxxx-xxxx)
   ersetzt mezr-waka-hawr-qbwb im APPLE_APP_PASSWORD Secret

================================================================
SCHRITT 7: Workflow testen
================================================================

Sobald alle Secrets gesetzt sind, sag mir Bescheid.
Dann mache ich ich ich:

git tag v1.4.3 -m "v1.4.3 mit Secrets für CI-Build"
git push origin v1.4.3

Der GitHub-Actions-Workflow läuft dann automatisch und
erzeugt innerhalb von 5-15 Min das offizielle v1.4.3 Release
mit:
- Developer-ID-signierter Mac-App (Gatekeeper-ready!)
- Notarisiert (Apple hat es geprüft)
- GitHub-Release mit Download-ZIPs
- Automatischer Upload nach devispro.de

================================================================
BRAUCHST DU HILFE?
================================================================

Falls du bei einem Schritt nicht weiterkommst, schick mir
einen Screenshot. Ich führe dich Schritt für Schritt durch.

================================================================