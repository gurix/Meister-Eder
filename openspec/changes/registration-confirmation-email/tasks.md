## 1. Add `qrbill` Dependency

- [ ] 1.1 Add `qrbill` to `[project.dependencies]` in `pyproject.toml`
- [ ] 1.2 Run `uv lock` to update the lockfile
- [ ] 1.3 Verify `qrbill` imports successfully in a smoke test or REPL

## 2. Persist Language in Registration Record

- [ ] 2.1 Update `ConversationStore._build_record()` in `src/storage/json_store.py` to include `language` from `state.language` in the `metadata` dict
- [ ] 2.2 Update `ConversationStore.save_registration()` and `save_registration_version()` signatures to accept/forward `state` (already does — confirm `_build_record` receives the full state)
- [ ] 2.3 Add a test in `tests/test_storage.py` asserting that the saved record's `metadata.language` matches `state.language`

## 3. Add `notify_parent()` to `AdminNotifier`

- [ ] 3.1 Add a `_generate_qr_bill_png()` static/class method to `AdminNotifier` using `qrbill` with fixed payment data:
  - IBAN: `CH14 0900 0000 4930 8018 8`
  - Payee: Familienverein Fällanden Spielgruppen, Huebwisstrase 5, 8117 Fällanden
  - Amount: `80.00`, Currency: `CHF`, Reference type: NON
  - Returns raw PNG `bytes`
- [ ] 3.2 Add bilingual string template dicts `_STRINGS_DE` and `_STRINGS_EN` (module-level constants) covering all user-visible strings in the confirmation email (subject, section headers, fee labels, payment instructions text, closing)
- [ ] 3.3 Add `_build_parent_html()` method: renders full HTML confirmation email body using the appropriate string dict, embedding the QR image via `cid:qrbill`; includes registration summary and both monthly fee (informational) and CHF 80 registration fee (with IBAN text + QR reference)
- [ ] 3.4 Add `_build_parent_text()` method: renders the plain-text fallback, including all summary fields and IBAN/payee details in plain text (no image)
- [ ] 3.5 Add `notify_parent()` public method:
  - Parameters: `registration: RegistrationData`, `language: str = "de"`
  - Select string dict based on `language`; fall back to `"de"` for unknown values
  - Call `_generate_qr_bill_png()` to get PNG bytes
  - Build MIME structure: `multipart/mixed` > `multipart/alternative` > plain text part + `multipart/related` > HTML part + inline PNG (`Content-Disposition: inline`, `Content-ID: <qrbill>`)
  - Call `_send()` with `to=[registration.parent_guardian.email]`, empty `cc`, localised subject, the assembled MIME message
  - If `_smtp_host` is empty (dev mode), log and skip as with `notify_admin`

## 4. Wire `notify_parent()` into Completion Events

- [ ] 4.1 In `src/agent/core.py` `_handle_registration()`: after the existing `notify_admin()` try/except block, add a parallel try/except block calling `self._notifier.notify_parent(registration=state.registration, language=state.language)`
- [ ] 4.2 In `chat_app.py` `on_message()`: after the existing `notify_admin()` call inside the completion block, add a parallel try/except block calling `_notifier.notify_parent(registration=state.registration, language=state.language)`
- [ ] 4.3 Verify both call sites log a warning (not an exception) on failure, and the registration completion path continues normally

## 5. Tests

- [ ] 5.1 Add `tests/test_notifier.py` tests for `notify_parent()`:
  - `test_notify_parent_calls_send`: mock `_send` and assert it is called with `to=[parent_email]`
  - `test_notify_parent_german_subject`: assert subject contains German text when `language="de"`
  - `test_notify_parent_english_subject`: assert subject contains English text when `language="en"`
  - `test_notify_parent_unknown_language_falls_back_to_de`: assert `language="fr"` produces German subject
  - `test_notify_parent_no_smtp_skips_send`: when `smtp_host=""`, `_send` is NOT called
- [ ] 5.2 Add a test asserting that the plain-text body contains the IBAN string `CH14` when `smtp_host` is empty (inspecting log or body build directly)
- [ ] 5.3 Add a test for `_generate_qr_bill_png()` asserting it returns `bytes` with non-zero length (requires `qrbill` installed)

## 6. Manual Smoke Test

- [ ] 6.1 Run `chainlit run chat_app.py` locally (or the email poller), complete a registration end-to-end, and verify the parent confirmation email arrives with the inline QR image rendered correctly
- [ ] 6.2 Verify the admin notification still arrives unchanged alongside the parent confirmation
- [ ] 6.3 Verify the saved `current.json` for the registration includes `metadata.language`
