# Data Export Formats

## CSV Export

### Filename Format
```
registrations_[YYYY-MM-DD].csv
registrations_[YYYY-MM-DD]_indoor.csv
registrations_[YYYY-MM-DD]_outdoor.csv
```

### Column Structure

| Column | Description | Example |
|--------|-------------|---------|
| registration_id | Unique identifier | REG-2024-001 |
| submitted_at | Submission date/time | 2024-09-15 14:30:00 |
| channel | Registration channel | email / chat |
| child_name | Child's full name | Emma Müller |
| child_dob | Date of birth | 2021-03-15 |
| child_age_years | Age in years | 3 |
| child_age_months | Additional months | 6 |
| special_needs | Special needs/medical | Peanut allergy |
| playgroup_types | Selected types | indoor,outdoor |
| selected_days | Booked days | monday,wednesday |
| monthly_fee | Calculated fee | 130 |
| parent_name | Parent/guardian name | Maria Müller |
| parent_address | Street address | Sunnetalstrasse 12 |
| parent_postal_code | Postal code | 8117 |
| parent_city | City | Fällanden |
| parent_phone | Phone number | +41 79 123 45 67 |
| parent_email | Email address | maria@example.com |
| emergency_name | Emergency contact name | Hans Müller |
| emergency_phone | Emergency contact phone | +41 79 987 65 43 |

### CSV Formatting Rules
- UTF-8 encoding (for German characters: ä, ö, ü, etc.)
- Comma-separated values
- Values with commas wrapped in quotes
- Header row included
- Date format: YYYY-MM-DD
- DateTime format: YYYY-MM-DD HH:MM:SS

---

## JSON Export

### Single Registration
```json
{
  "registrationId": "REG-2024-001",
  "child": {
    "fullName": "Emma Müller",
    "dateOfBirth": "2021-03-15",
    "specialNeeds": "Peanut allergy"
  },
  "parentGuardian": {
    "fullName": "Maria Müller",
    "phone": "+41 79 123 45 67",
    "email": "maria@example.com"
  },
  "emergencyContact": {
    "fullName": "Hans Müller",
    "phone": "+41 79 987 65 43"
  },
  "booking": {
    "playgroupTypes": ["indoor"],
    "selectedDays": [
      {"day": "monday", "type": "indoor"},
      {"day": "wednesday", "type": "indoor"}
    ]
  },
  "metadata": {
    "submittedAt": "2024-09-15T14:30:00Z",
    "channel": "chat",
    "conversationId": "conv-abc123"
  }
}
```

### Bulk Export (Array)
```json
{
  "exportedAt": "2024-09-20T10:00:00Z",
  "totalRecords": 25,
  "filters": {
    "dateFrom": "2024-09-01",
    "dateTo": "2024-09-30",
    "playgroupType": null
  },
  "registrations": [
    { ... },
    { ... }
  ]
}
```

---

## Export Use Cases

| Use Case | Recommended Format |
|----------|-------------------|
| Import to Google Sheets | CSV |
| Backup/archive | JSON |
| Integration with other systems | JSON |
| Quick overview/printing | CSV |
| Data analysis | Either (CSV for Excel, JSON for scripts) |

---

## Admin Workflow Integration

### Current Workflow (Google Forms)
1. Parent fills Google Form
2. Data appears in Google Sheet automatically
3. Admin receives email notification
4. Admin reviews in spreadsheet

### New Workflow (AI Registration)
1. Parent converses with AI agent
2. Completed registration stored in system
3. Admin receives email notification (same as before)
4. Admin can:
   - View individual registrations in admin interface
   - Export to CSV for Google Sheets compatibility
   - Export to JSON for archival/backup

### Maintaining Google Sheets Compatibility

For admins who prefer working in Google Sheets:

**Option A: Manual Import**
1. Export CSV from the system
2. Import into Google Sheets (File → Import)
3. Work with data as before

**Option B: Direct Google Sheets Integration (Future)**
- Automatic sync to a designated Google Sheet
- Requires Google API setup
- *Note: This is a potential future enhancement, not initial release*

### Export Triggers

| Trigger | Action |
|---------|--------|
| Admin clicks "Export" | Generate CSV/JSON download |
| Scheduled (optional) | Auto-generate weekly export |
| API request (optional) | Return JSON for integrations |

### Data Consistency

- Exports always reflect current stored data
- Registration IDs are consistent across exports
- Timestamps are consistent (UTC internally, local time in exports)

---

## Filtering and Query Requirements

### Export Filters

When exporting data, the admin should be able to filter by:

| Filter | Options | Use Case |
|--------|---------|----------|
| Date range | From/To dates | "Show September registrations" |
| Playgroup type | Indoor / Outdoor / Both | "Export only forest playgroup kids" |
| Booking day | Monday / Wednesday / Thursday | "Who's coming on Wednesdays?" |
| Channel | Email / Chat | "How many registered via chat?" |

### Query Examples

**All registrations this month:**
```
dateFrom: 2024-09-01
dateTo: 2024-09-30
```

**Forest playgroup registrations:**
```
playgroupType: outdoor
```

**Monday attendees (both playgroups):**
```
bookingDay: monday
```

**Recent registrations via chat:**
```
dateFrom: 2024-09-15
channel: chat
```

### Combination Filters

Filters can be combined:
- "All outdoor registrations in September"
- "Monday indoor kids registered via email"

### Sort Options

| Sort by | Direction |
|---------|-----------|
| Submission date | Newest first (default) / Oldest first |
| Child name | A-Z / Z-A |
| Playgroup type | Indoor first / Outdoor first |

### Default Export Behavior

If no filters specified:
- All registrations
- Sorted by submission date (newest first)
- All fields included
