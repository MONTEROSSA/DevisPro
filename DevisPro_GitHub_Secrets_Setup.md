# DevisPro — GitHub Secrets einrichten (1×ig, danach nie wieder)

Damit der Mac-Build automatisch signiert+notarisiert+auf devispro.de deployed wird,
müssen in GitHub 7 Secrets hinterlegt werden.

## WIE

1. https://github.com/MONTEROSSA/DevisPro/settings/secrets/actions → "New repository secret"
2. Jeden der 7 Secrets anlegen (Name exakt, Wert reinkopieren)

## SECRETS (7 Stück)

### 1. `VPS_SSH_KEY`
**Inhalt:** Der private SSH-Key für den VPS (187.77.79.26).
- Öffne `~/devis-auto/_vps_key` (Finder → Doppelklick öffnet in TextEdit)
- **Alles kopieren** (inkl. `-----BEGIN OPENSSH PRIVATE KEY-----` und `-----END ...`)
- Achtung: Falls der VPS-Key tot ist, generiere einen neuen UND lege ihn auf dem VPS ab:
  ```bash
  # Auf deinem Mac:
  ssh-keygen -t ed25519 -C "devispro-deploy" -f ~/devis-auto/_vps_key_new
  # Public Key auf VPS legen (einmalig manuell via hPanel-Terminal):
  # cat ~/devis-auto/_vps_key_new.pub >> auf VPS in /root/.ssh/authorized_keys
  ```

### 2. `VPS_HOST`
**Inhalt:** `187.77.79.26`

### 3. `APPLE_ID`
**Inhalt:** `info@monterossa.ch` (Apple Developer Login, exakt wie in sign_fix.command)

### 4. `APPLE_TEAM_ID`
**Inhalt:** `T3VS7P5X5D`

### 5. `APPLE_APP_PASSWORD`
**Inhalt:** App-spezifisches Passwort für `notarytool`.
Aktuell: `mezr-waka-hawr-qbwb` (aus sign_fix.command Z.13)
Falls abgelaufen: bei https://appleid.apple.com → "App-spezifische Passwörter" → neu generieren.

### 6. `KEYCHAIN_PASSWORD`
**Inhalt:** Passwort für die Login-Keychain auf dem Mac.
GitHub Runner erstellt automatisch eine temporäre Keychain mit eigenem Passwort.
Wir nutzen den sicheren Weg: **kein Keychain nötig**, weil `xcrun notarytool` direkt
die `APPLE_APP_PASSWORD` akzeptiert — die Zertifikats-Signierung übernimmt
GitHub über das `Developer ID Application`-Zertifikat, das du noch hochladen musst.
**Lass diesen Secret leer** (oder vergib ihm einen beliebigen Wert).

### 7. `MAC_CERT_NAME`
**Inhalt:** `Developer ID Application: Ferdinand Ferdinand Röthlisberger (T3VS7P5X5D)`
(= exakt der Name aus sign_fix.command Z.11)

---

## ZUSÄTZLICH: Developer-ID-Zertifikat als p12 hochladen

Damit der GitHub-Runner signieren kann, muss das `.p12`-Zertifikat Base64-kodiert als Secret hinterlegt werden:

1. Auf deinem Mac: `Keychain Access` → Suche "Developer ID Application" → Rechtsklick → Export
2. Als `devispro.p12` speichern, Passwort setzen (z. B. `devispro2026`)
3. Base64-kodieren:
   ```bash
   base64 -i ~/Desktop/devispro.p12 | pbcopy
   ```
4. Neuer Secret:
   - Name: `MAC_CERT_P12_BASE64`
   - Wert: das Base64 aus Zwischenablage
5. Noch ein Secret:
   - Name: `MAC_CERT_P12_PASSWORD`
   - Wert: das Passwort aus Schritt 2

Der Workflow wird um die Zertifikats-Import-Logik erweitert (siehe nächste Session).

---

## TRIGGER: Wie löst man den Build aus?

```bash
cd ~/devis-auto
git tag v1.4.0
git push origin v1.4.0
```

→ GitHub Actions startet automatisch `build-deploy-mac.yml`
→ 5-10 min später liegt das notarized ZIP auf https://devispro.de/DevisPro_Mac.zip

---

## ALTERNATIV (ohne GitHub-Tag): Manuell

https://github.com/MONTEROSSA/DevisPro/actions/workflows/build-deploy-mac.yml
→ "Run workflow" → Branch: main → grüner Button.

---

## STATUS NACH SETUP

- ✅ `~/Desktop/DevisPro.app` ist bereits signiert+notarisiert (Build 2026-08-29 11:22)
- ✅ 4 Moats M1-M4 (Verbandskataloge, Marketplace, Cloud Sync, ERP) integriert
- ✅ spctl accepted
- ⏳ VPS-Deploy wartet auf Secrets
- ⏳ Web-Download (https://devispro.de/DevisPro_Mac.zip) ist aktuell der ALTE Build vom 19.8.
