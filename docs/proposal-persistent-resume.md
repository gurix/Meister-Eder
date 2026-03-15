# Proposal: Persistente Anmeldungen mit niederschwelliger Identifikation

## Kontext

Der Email-Kanal hat bereits Persistenz: `ConversationStore` speichert den Gesprächsstand pro Email-Adresse auf Disk, und der Email-Loop erkennt bekannte Absender automatisch wieder.

Der Chat-Kanal (Chainlit) nutzt nur `cl.user_session` — In-Memory, verloren beim Tab-Schliessen.

Ziel: Chat-Kanal erhält dieselbe Persistenz, ohne Passwörter oder Registrierung.

---

## Empfohlener Ansatz: E-Mail als primärer Identifikator + Kind-Name als Soft-Confirmation

### Prinzip

Wie ein Anruf beim Sekretariat:
> "Hallo, ich bin die Mutter von Lena Müller. Ich hatte letzte Woche angefangen, mich anzumelden..."

Das Sekretariat fragt: "Für welche E-Mail-Adresse habe ich die Anmeldung gespeichert?" — und kann dann nachschauen.

### Warum E-Mail?

- **Bereits natürlicher Schlüssel im System**: `ConversationStore` ist schon nach normalisierter Email-Adresse indiziert (`_email_to_filename`)
- **Früh im Flow verfügbar**: Wir erheben die E-Mail der Eltern ohnehin (Schritt `parent_contact`), lediglich früher im Flow
- **Kein Passwort nötig**: Eltern kennen ihre E-Mail-Adresse — das ist der tiefste mögliche Schwellenwert
- **Bestätigung via Kind-Name**: Als Soft-Confirmation bestätigt der Elternteil den Namen des Kindes → natürlich, nicht-invasiv, keine Codes

### Warum kein Magic Link / OTP?

Für eine kleine Spielgruppe überengineered:
- Zusätzlicher Round-Trip (E-Mail öffnen → Code kopieren → zurück zum Chat)
- SMTP-Infra ist bereits für Bestätigungen da, nicht für Auth-Flows
- Eltern, die per E-Mail interagieren können, können auch direkt den Email-Kanal nutzen

### Warum kein Kurzcode?

- Eltern müssen ihn aufbewahren → hohe Vergessrate
- Besser als optionaler Zusatz ("Ihr Anmelde-Code: XK7T2P") in der Bestätigungs-E-Mail

---

## Technisches Design

### 1. E-Mail früher im Flow erheben

Neuer Step `email_first` nach `greeting` (für Chat-Kanal). Der Agent fragt früh nach der E-Mail, damit ein Lookup möglich ist.

```
greeting → email_first → [lookup] → resume_or_new | continue_new
```

### 2. Lookup und Resume-Logik in `chat_app.py`

Sobald der Agent eine E-Mail aus der Antwort des Elternteils extrahiert:

```python
# Nach E-Mail-Extraktion im on_message Handler
existing = _store.find_by_email(email)

if existing and not existing.completed:
    # Angebotenen Resume
    # Soft-Confirmation: Kind-Name bestätigen
    state = existing
    cl.user_session.set("state", state.to_dict())

elif existing and existing.completed:
    # Status anzeigen, Bestätigung erneut senden anbieten

else:
    # Neue Anmeldung starten, E-Mail bereits vorausfüllen
    state.registration.parent_guardian.email = email
```

### 3. Persistenz nach jedem Schritt

In `on_message`, nach jedem LLM-Response: `_store.save(state)`.

Aktuell wird nur bei Abschluss gespeichert. Mit dieser Änderung wird der Zwischenstand nach jedem Turn auf Disk geschrieben — dasselbe was der Email-Kanal schon tut.

Schlüssel für Chat-Sessions: die E-Mail-Adresse (sobald bekannt), davor die `conversation_id` (UUID).

### 4. Status-Abfragen und Bestätigungs-E-Mail

Der Agent erhält neue Intent-Erkennung:
- `intent: "status_query"` → Agent antwortet mit aktuellem Stand aus `state`
- `intent: "resend_confirmation"` → `_notifier.notify_parent()` erneut aufrufen

Das ist eine reine Prompt/Response-Parser-Änderung, kein neuer Storage-Code nötig.

### 5. Cross-Channel Resume (Phase 2, nicht in diesem PR)

Weil beide Kanäle denselben `ConversationStore` nutzen und E-Mail der gemeinsame Schlüssel ist, wäre Cross-Channel-Resume später einfach ergänzbar. Explizit aus Scope herausgenommen um den ersten PR schlank zu halten.

---

## Dateien die sich ändern

| Datei | Änderung |
|-------|----------|
| `chat_app.py` | E-Mail aus Conversation-State extrahieren, `_store.save()` nach jedem Turn, Resume-Logik |
| `src/agent/prompts.py` | Neuer Step `email_first`, `resume_or_new`; Hinweis auf Status-/Resend-Intents |
| `src/agent/response_parser.py` | `intent: "status_query"` und `"resend_confirmation"` handeln |
| `src/models/conversation.py` | Optional: `resume_token` Feld (6-Zeichen Kurzcode für Bestätigungs-E-Mail) |
| `tests/` | Tests für Resume-Flow, Status-Query, Resend |

### Keine neuen Dependencies

Kein neues Storage-Backend, keine Auth-Library. Alles auf bestehendem Code aufgebaut.

---

## Trade-offs und Risiken

| Aspekt | Einschätzung |
|--------|--------------|
| Datenschutz | E-Mail ist bereits im System; kein neues PII erhoben |
| Sicherheit | Soft-Confirmation (Kind-Name) reicht für diesen Kontext; keine sensiblen Daten |
| Fehlbedienung | Eltern könnten die E-Mail falsch eingeben → neue Anmeldung statt Resume; akzeptabel |
| Edge Cases | Mehrere Kinder pro E-Mail → spätere Phase; aktuell eine Anmeldung pro E-Mail |

---

## Offene Fragen für Review

1. Soll die E-Mail im Chat-Kanal zwingend als erster Schritt erhoben werden, oder erst wenn Eltern explizit resumieren möchten?
2. Soll ein Kurzcode in die Bestätigungs-E-Mail aufgenommen werden (als Fallback für Eltern die E-Mail-Adresse wechseln)?
3. Cross-Channel Resume (Email ↔ Chat): In diesem PR oder separate Story?
