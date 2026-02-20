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
