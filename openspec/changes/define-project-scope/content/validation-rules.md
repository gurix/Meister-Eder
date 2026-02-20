# Validation Rules

## Child Information

| Field | Validation Rules |
|-------|------------------|
| Child's Full Name | Required, minimum 2 characters, letters and spaces only |
| Date of Birth | Required, valid date format, must be in the past, child should be appropriate age for playgroup |
| Special Needs / Medical Conditions | Required, free text (parents can enter "None" if not applicable) |

## Parent/Guardian Information

| Field | Validation Rules |
|-------|------------------|
| Parent/Guardian Name | Required, minimum 2 characters, letters and spaces only |
| Street Address | Required, minimum 5 characters |
| Postal Code | Required, exactly 4 digits (Swiss format) |
| City | Required, minimum 2 characters |
| Phone Number | Required, valid phone number format |
| Email Address | Required, valid email format |

## Emergency Contact

| Field | Validation Rules |
|-------|------------------|
| Emergency Contact Name | Required, minimum 2 characters, letters and spaces only |
| Emergency Contact Phone | Required, valid phone number format |

## Booking Selection

| Field | Validation Rules |
|-------|------------------|
| Playgroup Type(s) | Required, at least one type must be selected (Indoor and/or Outdoor) |
| Booking Days | Required, at least one day must be selected, days must match selected playgroup type(s) |

### Booking Day Constraints

- If **Indoor** selected: Can choose from Monday, Wednesday, Thursday
- If **Outdoor (Forest)** selected: Must include Monday
- If **Both** selected: Can choose any combination of Mon, Wed, Thu (with Monday available in either/both programs)

## Notes

- The agent should guide parents through validation naturally (e.g., "Could you spell that again?" rather than "Invalid format")
- **Age validation**: Children must be between 2-5 years old at time of registration
