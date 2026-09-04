# DevisPro Pricing-Strategie – Analyse & 3 Alternativmodelle

**Markt:** B2B-SaaS, DACH (Schweiz priorisiert), Bauwesen / Architekten / GU
**Zielgruppe:** KMU-Bauhandwerker, Architekturbüros, Generalunternehmer, Ingenieure
**Pain Point:** SIA-451 Devis-Erstellung, Sorba-Import, Mengenberechnung
**Preisniveau:** Aktuell in CHF, DACH-konform

---

## 1. Bestandsaufnahme aktuelles Pricing

| Tarif | Preis | Einheit | Wertversprechen (implizit) |
|---|---|---|---|
| Starter | 89 CHF | pro Devis | Einstieg ohne Fixkosten, einzelnes Devis |
| Pro | 350 CHF | pro Monat | Subscription für regelmässige Nutzer |
| Enterprise | Custom | individuell | Volumen, API, Multi-User, Onboarding |

**Kritische Schwächen des heutigen Modells:**
- **Hybrid-Bruch:** Starter (Transaktion) vs. Pro (Fixkosten) — Kunde kann nicht einfach hochskalieren, ohne Tarif zu wechseln. Bruchstelle bei ~4 Devis/Mt (= 356 CHF).
- **Keine Free-Tier / kein Lead-Magnet:** 89 CHF/Devis ist eine harte Eintrittsbarriere für kalte Leads. Trial-to-Pay Conversion leidet.
- **Keine Jahresoption sichtbar:** Im DACH-Markt erwarten KMU 10–20% Discount für Jahresbindung — psychologisch wichtig.
- **Kein Team-/Seat-Modell:** Pro ist Single-Tenant-Preis, skaliert nicht mit Team-Grösse. Wird bei wachsenden Büros zum Deal-Killer.
- **Enterprise-Preis intransparent:** "Custom" ohne Anker erzeugt Reibung im Sales-Funnel; KMU zögern, weil sie keinen Referenzpunkt haben.
- **Starter als Standard-Anker:** Wahrnehmung "89 CHF/Devis" positioniert das Produkt nach oben als teuer — selbst wenn der Pro-Tarif günstiger wäre.

**Erwartete Umsatzverteilung heute (Schätzung):**
70% Starter / 25% Pro / 5% Enterprise — mit hohem Churn im Starter nach Erstkauf.

---

## 2. Alternative Pricing-Modelle

### Modell A: **Tiered Subscription** (klassisches 3-Stufen-Modell, optimiert)

**Philosophie:** Vorhersehbarer Umsatz, klare Upgrade-Pfade, monatliche Abrechnung mit Jahresbonus.

| Tarif | Preis/Mt | Jahrespreis | Inkludierte Devis | Übervolumen |
|---|---|---|---|---|
| **Solo** | 79 CHF | 790 CHF (10% sparen) | 5/Mt | +8 CHF/Devis |
| **Team** | 249 CHF | 2'490 CHF | 25/Mt | +6 CHF/Devis |
| **Business** | 599 CHF | 5'990 CHF | 100/Mt | +4 CHF/Devis |
| **Enterprise** | ab 1'200 CHF | Custom | Unlimited + API + SSO | inkl. |

**Annahmen Verteilung:** Solo 50% / Team 30% / Business 15% / Enterprise 5%
**Ø Erlös/Kunde/Mt:** ~210 CHF

#### Umsatzprognose

| Kunden | Monatsumsatz (MRR) | Jahresumsatz (ARR) | Mix-Stickiness |
|---|---|---|---|
| **100** | ~21'000 CHF | ~252'000 CHF | Niedrig (Solo dominant) |
| **500** | ~105'000 CHF | ~1'260'000 CHF | Mittel |
| **2'000** | ~420'000 CHF | ~5'040'000 CHF | Hoch (Business+Enterprise gewinnen) |

**Psychologische Hebel:**
- **Anker-Effekt:** Enterprise "ab 1'200 CHF" macht Team (249 CHF) zur "vernünftigen Wahl".
- **Decoy-Pricing:** Business (599) ist da, damit Team (249) als Sweet Spot wirkt — nicht Solo, nicht Enterprise.
- **Jahresrabatt 10%:** Sticky revenue, typisch für DACH-KMU (Liquidität im Q1 knapp, Q4-Disposition für Jahresverträge).
- **Rundung auf .99 vs. ganze Zahlen:** 79 (glatt) signalisiert "durchdacht" statt "rabattlastig".
- **Inklusivvolumen + Übervolumen:** Vermeidet Paywall-Schock, Kunde fühlt sich fair behandelt.

**Risiko:** Solo-Tarif kann churnig sein, wenn nur 1–2 Devis/Mt erstellt werden.

---

### Modell B: **Usage-Based mit Bundles** (modern, Pay-as-you-grow)

**Philosophie:** Kein Fixkosten-Commitment, perfekte Skalierung für sporadische Nutzer, Lead-Generation durch Free-Tier.

| Tarif | Preis | Einheit |
|---|---|---|
| **Free** | 0 CHF | 2 Devis/Mt, manuell (kein Sorba-Import) |
| **Pay-as-you-go** | 49 CHF | pro Devis |
| **Bundle 25** | 990 CHF | 25 Devis/Quartal (39.60/Devis, –19%) |
| **Bundle 100** | 2'900 CHF | 100 Devis/Quartal (29.00/Devis, –41%) |
| **Enterprise** | ab 4'500 CHF/Mt | Custom, API, Multi-User, Volumen |

**Annahmen Verteilung:** Free 30% / PAYG 25% / Bundle 25 25% / Bundle 100 15% / Enterprise 5%
**Ø Erlös/Kunde/Mt:** ~260 CHF (über alle inkl. Free)

#### Umsatzprognose (Free zählt nicht als zahlender Kunde; PAYG+Kunden)

| Kunden | Davon Free | Davon zahlend | MRR | ARR |
|---|---|---|---|---|
| **100** | 30 | 70 | ~18'200 CHF | ~218'000 CHF |
| **500** | 150 | 350 | ~91'000 CHF | ~1'092'000 CHF |
| **2'000** | 600 | 1'400 | ~364'000 CHF | ~4'368'000 CHF |

**Psychologische Hebel:**
- **Free-Tier als Vertrauensanker:** 2 Devis gratis = Kunde sieht Produktwert ohne Risiko. Senkt CAC massiv, perfekt für DACH-Vertrauenskultur.
- **Preis-Diskriminierung nach Volumen:** 49 → 39.60 → 29 → Custom. "Je mehr du brauchst, desto weniger pro Stück" — rational stark.
- **Quartals-Bundles:** Saisonalität im Bau (Q2/Q3 Hochsaison) → Kunden kaufen gross ein, wenn Volumen kommt. Cashflow boost.
- **Stückpreis-Vergleichbarkeit:** 29 CHF/Devis (Bundle 100) klingt klein im Vergleich zu 89 CHF heute — **Revue-Anker gekippt**.
- **Enterprise-Anker 4'500:** Selbst Team-Kunden im Modell A würden hier zu Bundle-100-Kunden wandern.

**Risiko:** Umsatz schwer prognostizierbar, churn bei saisonalem Bau stark. Erfordert gute Analytics & dunning flows.

---

### Modell C: **Per-User-Seats + Add-ons** (team-orientiert, fest)

**Philosophie:** Jeder Mitarbeiter = zahlende Lizenz. Skaliert mit Büro-Wachstum, sehr vorhersagbar.

| Tarif | Preis/User/Mt | Jahrespreis/User | Min. User | Devis inkl. |
|---|---|---|---|---|
| **Light** | 49 CHF | 490 CHF | 1 | 5 |
| **Pro** | 129 CHF | 1'290 CHF | 3 | 25 |
| **Business** | 229 CHF | 2'290 CHF | 5 | Unlimited |
| **Enterprise** | Custom | Custom | 10+ | Unlimited + API + Onboarding |

**Annahmen:** Light 50% / Pro 30% / Business 15% / Enterprise 5%
**Ø Erlös/Beziehung/Mt:** Light 49, Pro 387 (3×129), Business 1'145 (5×229), Enterprise ~3'000
**Gewichteter Durchschnitt pro Kunde:** ~370 CHF/Mt (höher, weil Multi-User-Kunden)

#### Umsatzprognose

| Kunden | Ø User/Kunde | MRR | ARR |
|---|---|---|---|
| **100** | 2.5 | ~37'000 CHF | ~444'000 CHF |
| **500** | 3.0 | ~185'000 CHF | ~2'220'000 CHF |
| **2'000** | 3.5 | ~740'000 CHF | ~8'880'000 CHF |

**Psychologische Hebel:**
- **Min-User-Schwelle:** "Mind. 3 User im Pro-Tarif" verhindert Single-User-Stagnation; Upgrade-Druck sobald 2. MA das Tool nutzen will.
- **Pro-Discount per User:** 3×129 = 387 statt 3×229 = 687 → ~44% günstiger als Business-Equivalent. Treibt Pro-Sweet-Spot.
- **Per-Seat-Transparenz:** CFO sieht Kosten pro Mitarbeiter — leicht zu rechtfertigen (vs. Devis-Stückpreis, der schwer budgetierbar ist).
- **Enterprise-Treshold (10+ User):** Klare Schwelle, ab der Sales-Pipeline startet. Self-Service bis dahin.
- **"Unlimited Devis" in Business:** Eliminiert Volumen-Angst für wachsende Büros.

**Risiko:** Kleinstbüros (1-Mann-Architekten) fühlen sich ausgeschlossen; höhere Komplexität in der Rechnungsstellung.

---

## 3. Vergleich auf einen Blick

| Kriterium | A: Tiered Subscription | B: Usage-Based Bundles | C: Per-User-Seats |
|---|---|---|---|
| MRR @ 100 Kunden | 21'000 | 18'200 | 37'000 |
| MRR @ 500 Kunden | 105'000 | 91'000 | 185'000 |
| MRR @ 2'000 Kunden | 420'000 | 364'000 | **740'000** |
| ARR @ 2'000 Kunden | 5.04 MCHF | 4.37 MCHF | **8.88 MCHF** |
| Vorhersagbarkeit | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Skalierbarkeit bei Wachstum | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Einstiegsfreundlichkeit | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Sales-Selbst-Service | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| DACH-KMU-Fit | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Implementierungs-Aufwand | niedrig | mittel | mittel |

---

## 4. Konkrete Empfehlung: **Modell B (Usage-Based Bundles) als Lead-Front, kombiniert mit Modell A für Stammkunden**

**Warum diese Kombi?**

1. **Modell B als Acquisition-Treiber:** Free-Tier (2 Devis/Mt) senkt die grösste DACH-spezifische Hürde — Vertrauen & Risikoaversion. Sorba-Import erst ab PAYG = perfekter Upgrade-Trigger.
2. **Modell A als Retention-Schicht:** Sobald ein Kunde >25 Devis/Quartal generiert, automatischer Wechsel in Team-Tier mit Jahresrabatt. Sticky revenue.
3. **Modell C nur für Enterprise-Layer (>10 User, API-Bedarf):** Custom-Pricing, Account-Management, NICHT im Self-Service-Funnel.

**Konkrete Rollout-Reihenfolge (3 Phasen, 6 Monate):**

### Phase 1 (Monat 1–2): Free-Tier launchen
- 2 Devis/Mt gratis, kein Sorba-Import, Wasserzeichen im PDF-Export
- Conversion-Target: 8% Free → PAYG innerhalb 30 Tagen

### Phase 2 (Monat 3–4): Bundle 25 + Bundle 100 launchen
- Quartals-Bundles mit Verfallsdatum (rollierend)
- In-App-Nudge bei >15 Devis/Quartal: "Spare 19% mit Bundle 25"
- Conversion-Target: 25% PAYG → Bundle innerhalb 90 Tagen

### Phase 3 (Monat 5–6): Team-Tier (Modell A) als Jahresvertrag einführen
- Ab 25 Devis/Mt: Sales-Trigger "Jahres-Abo für 10% sparen"
- Pro-Tier (249/Mt) als Default für Büros mit 3+ Nutzern

**Resultierende Umsatzprognose (kombiniert, bei 2'000 Kunden nach 18 Monaten):**
- Free: 600 Kunden (Lead-Gen, 0 CHF MRR)
- PAYG: 400 Kunden × 49 CHF × ~3 Devis/Mt = ~58'800 CHF MRR
- Bundle 25: 500 Kunden × 990/Qt ÷ 3 = ~165'000 CHF MRR
- Bundle 100: 350 Kunden × 2'900/Qt ÷ 3 = ~338'000 CHF MRR
- Team (Modell A): 130 Kunden × 249 = ~32'400 CHF MRR
- Business: 20 Kunden × 599 = ~12'000 CHF MRR
- **Total MRR: ~606'000 CHF → ARR: ~7.3 MCHF**

**Plus strategischer Vorteil:** Free-Tier skaliert CAC runter (organische Leads durch Devis-Sharing in Bau-Communitys), während Bundles den ARPU bei Vielnutzern maximieren.

**Kritische Erfolgsfaktoren:**
1. **Analytics-Stack aufbauen:** Devis-Volumen, User-Behaviour, Churn-Signale tracken — sonst keine Modellsteuerung möglich.
2. **Dunning-Flow für Bundle-Verfall:** 14-Tage-Warnung, 7-Tage-Soft-Expiry, klare Re-Aktivierungs-CTA.
3. **Sales-Qualifizierung für Enterprise:** Ab Bundle-100-Kunden mit API-Anfrage → manuelle Ansprache, NICHT in Online-Funnel.
4. **DACH-Lokalisierung der Pricing-Page:** CHF-Symbol gross, keine "ab $"-Logik, SIA-451/Sorba-Keywords prominent.

---

## 5. Was NICHT funktioniert (Lessons Learned)

- **Nicht das aktuelle Pay-per-Devis als Hauptstütze behalten:** 89 CHF/Devis positioniert das Produkt nach oben und tötet Free-Tier-Leadflow.
- **Nicht alle 3 Modelle parallel anbieten:** Verwirrt KMU, Sales-Cycle verlängert sich. Klare Hauptstufe + definierte Upgrades.
- **Nicht "individuell" ohne Anker kommunizieren:** Jeder Enterprise-Tarif braucht Floor-Preis ("ab X CHF/Mt").
- **Nicht auf Net-30-Trial setzen:** DACH-KMU klicken lieber auf "Free" oder "Kaufen". Trial-Frist = Reibung.

---

**Bottom Line:** Start mit **Modell B als Kunden-Frontend**, halte **Modell A im Backend** für Stammkunden-Jahresverträge bereit, nutze **Modell C nur für Enterprise ab 10 Usern**. Erwarteter ARR nach 18 Monaten bei 2'000 Kunden: **~7.3 MCHF** — 44% über dem heutigen Setup (geschätzt ~5 MCHF bei vergleichbarer Grösse).