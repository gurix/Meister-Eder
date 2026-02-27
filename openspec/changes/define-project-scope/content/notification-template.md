# Admin Notification Email Template

## Subject Line

```
New Registration: [Child Name] for [Playgroup Type]
```

Examples:
- `New Registration: Emma Müller for Indoor Playgroup`
- `New Registration: Luca Weber for Indoor + Outdoor Playgroup`

## Email Body

```
===============================================
NEW PLAYGROUP REGISTRATION
===============================================

Submitted: [Date] at [Time]
Channel: [Email / Chat]

-----------------------------------------------
CHILD INFORMATION
-----------------------------------------------
Name:           [Child's Full Name]
Date of Birth:  [DOB] (Age: [calculated age])
Special Needs:  [Details or "None"]

-----------------------------------------------
PLAYGROUP SELECTION
-----------------------------------------------
Type:           [Indoor / Outdoor / Both]
Days:           [Monday, Wednesday, Thursday]

Monthly Fee:    CHF [amount]
(Plus CHF 80 registration fee if first enrollment)

-----------------------------------------------
PARENT/GUARDIAN
-----------------------------------------------
Name:           [Parent Name]
Address:        [Street Address]
                [Postal Code] [City]
Phone:          [Phone Number]
Email:          [Email Address]

-----------------------------------------------
EMERGENCY CONTACT
-----------------------------------------------
Name:           [Emergency Contact Name]
Phone:          [Emergency Contact Phone]

===============================================

This registration was submitted via the automated
registration assistant.

[View full registration record →]

```

## HTML Version (Optional)

For better formatting in email clients, an HTML version can include:
- Playgroup logo in header
- Color-coded sections
- Clickable phone/email links
- Button to view full record

## Notification Settings

**Send timing:** Immediately upon registration completion

**Reply-to:** Set to parent's email so admin can reply directly

### Routing by Playgroup Type

| Registration Type | Send Notification To |
|-------------------|---------------------|
| Indoor only | Andrea Sigrist (andrea.sigrist@gmx.net) |
| Outdoor only | Barbara Gross (baba.laeubli@gmail.com) |
| Both Indoor + Outdoor | Both Andrea AND Barbara |
| All registrations (CC) | Administration: Markus Graf (spielgruppen@familien-verein.ch) |

*Note: When a child registers for both playgroups, both leaders receive the full notification. The administration is CC'd on all registrations.*

---

## Fields Included in Notification

### Always Included (Required Fields)

| Field | Source | Format |
|-------|--------|--------|
| Child's Full Name | registration.child.fullName | As entered |
| Date of Birth | registration.child.dateOfBirth | DD.MM.YYYY |
| Calculated Age | Computed from DOB | "X years, Y months" |
| Special Needs | registration.child.specialNeeds | As entered |
| Playgroup Type(s) | registration.booking.playgroupTypes | "Indoor" / "Outdoor" / "Indoor + Outdoor" |
| Selected Days | registration.booking.selectedDays | Comma-separated list |
| Monthly Fee | Computed from selection | "CHF X.-" |
| Parent Name | registration.parentGuardian.fullName | As entered |
| Parent Address | registration.parentGuardian.streetAddress | As entered |
| Parent Postal Code | registration.parentGuardian.postalCode | As entered |
| Parent City | registration.parentGuardian.city | As entered |
| Parent Phone | registration.parentGuardian.phone | As entered |
| Parent Email | registration.parentGuardian.email | As entered |
| Emergency Contact Name | registration.emergencyContact.fullName | As entered |
| Emergency Contact Phone | registration.emergencyContact.phone | As entered |
| Submission Timestamp | registration.metadata.submittedAt | DD.MM.YYYY HH:MM |
| Channel | registration.metadata.channel | "Email" / "Chat" |

### Computed Fields

| Field | Calculation |
|-------|-------------|
| Age | Current date - DOB, formatted as years and months |
| Monthly Fee | Indoor: 130, Outdoor: 250, Both: 380 (before sibling discount) |

### Not Included in Notification

- Conversation ID (internal tracking only)
- Full conversation history
- Previous registration attempts

---

# Parent Confirmation Email Template

Sent to the parent's email address immediately after a registration is completed.

## Subject Line

```
Anmeldung bestätigt: [Child Name] / Registration confirmed: [Child Name]
```

## Email Body (Bilingual: German first, English below)

```
===============================================
ANMELDEBESTÄTIGUNG — SPIELGRUPPE PUMUCKL
REGISTRATION CONFIRMATION — SPIELGRUPPE PUMUCKL
===============================================

Hallo [Parent Name] / Hi [Parent Name],

Wir haben die Anmeldung von [Child Name] erhalten.
We have received the registration for [Child Name].

-----------------------------------------------
ZUSAMMENFASSUNG / SUMMARY
-----------------------------------------------
Kind / Child:       [Child's Full Name]
Geburtsdatum / DOB: [DOB]
Spielgruppe / Type: [Indoor / Outdoor / Both]
Tage / Days:        [Selected days]
Monatsbeitrag /
Monthly fee:        CHF [amount]
Einschreibegebühr /
Registration fee:   CHF 80 (einmalig / one-time)

-----------------------------------------------
KONTAKT / CONTACT
-----------------------------------------------
[IF indoor or both:]
Indoor Spielgruppe:
Andrea Sigrist
Tel: 079 674 99 92
E-Mail: andrea.sigrist@gmx.net

[IF outdoor or both:]
Waldspielgruppe:
Barbara Gross
Tel: 078 761 19 64
E-Mail: baba.laeubli@gmail.com

Administration:
Markus Graf
Tel: 079 261 16 37
E-Mail: spielgruppen@familien-verein.ch

-----------------------------------------------

Bei Fragen kannst du dich direkt an die
zuständige Spielgruppenleiterin wenden.
For questions, contact the relevant playgroup
leader directly using the details above.

Wir freuen uns auf [Child Name]!
We look forward to welcoming [Child Name]!

Spielgruppe Pumuckl
Familienverein Fällanden
Sunnetalstrasse 4, 8117 Fällanden

===============================================
```

## Routing of Contact Details

The CONTACT section is conditionally rendered based on the registration:

| Registration type | Show contact for |
|-------------------|-----------------|
| Indoor only | Andrea Sigrist + Administration |
| Outdoor only | Barbara Gross + Administration |
| Both | Andrea Sigrist + Barbara Gross + Administration |

## HTML Version (Optional)

For better formatting in email clients, an HTML version can include:
- Playgroup logo in header
- Clickable `mailto:` and `tel:` links for each contact
- Color-coded summary table
- "Add to contacts" buttons for leader emails
