# Release Priorities

## Initial Release (MVP)

### Core Capabilities

| Feature | Priority | Notes |
|---------|----------|-------|
| Chat interface | Must have | Web-based, mobile-responsive |
| Email channel | Must have | Full email conversation support |
| Conversational registration | Must have | Guided data collection via AI |
| Knowledge base Q&A | Must have | Fees, schedule, policies, FAQ |
| Bilingual support | Must have | German and English |
| Registration data storage | Must have | Structured JSON format |
| Admin notifications | Must have | Routed by playgroup type |
| Email reminders | Must have | Day 3, 10, 25 for incomplete registrations |
| Data export | Must have | CSV and JSON formats |

### Data Collected

All 13 required fields:
- Child: name, DOB, special needs
- Parent: name, address, postal code, city, phone, email
- Emergency: name, phone
- Booking: playgroup type(s), days

---

## Phase 2 (Future Enhancements)

| Feature | Priority | Notes |
|---------|----------|-------|
| Telegram bot | Nice to have | Additional channel |
| WhatsApp integration | Nice to have | Additional channel |
| Google Sheets sync | Nice to have | Direct integration vs. export |
| Capacity/waitlist | Consider | Auto-check if spots available |
| Sibling batch registration | Consider | Register multiple children at once |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Payment processing | Admin handles invoicing separately |
| Calendar booking | Not needed for registration |
| Parent accounts/login | Registration is one-time flow |
| Mobile app | Web chat is mobile-responsive |

---

## Success Criteria for Initial Release

1. Parents can complete registration via chat OR email
2. Agent answers common questions from knowledge base
3. Admin receives notification with all registration details
4. Incomplete registrations receive automated reminders
5. Admin can export registration data in CSV/JSON
