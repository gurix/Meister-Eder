## 1. Confirmation Email Reply-To (Email Channel)

- [ ] 1.1 Identify where the registration completion confirmation email is constructed in `src/` (email channel adapter / agent core)
- [ ] 1.2 Add `Reply-To: spielgruppen@familien-verein.ch` header to the confirmation email only (not to mid-registration conversational emails)
- [ ] 1.3 Add a unit test verifying the `Reply-To` header is present on the confirmation email
- [ ] 1.4 Add a unit test verifying mid-registration emails do NOT carry the admin `Reply-To` header

## 2. Notification Email Reply-To (Registration Notifications)

- [ ] 2.1 Identify where registration notification emails are constructed and sent
- [ ] 2.2 Set `Reply-To: <parent email>` header on all outgoing notification emails (indoor, outdoor, and both routing types)
- [ ] 2.3 Add a unit test verifying the `Reply-To` header equals the parent's email for indoor-only notification
- [ ] 2.4 Add a unit test verifying the `Reply-To` header equals the parent's email for outdoor-only notification
- [ ] 2.5 Add a unit test verifying the `Reply-To` header equals the parent's email when both leaders are notified

## 3. Verification

- [ ] 3.1 Run the full test suite and confirm all tests pass
- [ ] 3.2 Manually send a test registration through the email channel and verify reply routing behaves correctly
