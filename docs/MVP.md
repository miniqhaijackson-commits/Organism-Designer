# MVP Feature Set and Top-3 Priorities

This document summarizes the minimum viable product (MVP) features for the J.A.R.V.I.S. prototype and the top-3 features to focus on first.

Full MVP (short):
- Voice assistant core: local wake-word, offline STT (VOSK), offline TTS (pyttsx3 or similar), simple command handling.
- Local project library: SQLite + file store with autosave and snapshots.
- Command interpreter with enforced security policy and pairing for device control.

Top-3 priorities (Phase A):
1. Local data store & projects: reliable SQLite schema, file store, autosave + snapshots.
2. Offline STT/TTS prototype: a simple end-to-end path from audio input -> text -> TTS output to validate offline UX.
3. Secure command interpreter and admin controls: `EnterpriseSecurity` rules, short-lived admin sessions, RBAC, and audit logs.

Phase A will be implemented incrementally; the repository already includes an initial FastAPI scaffold, admin session management, RBAC, audit log, and autosave skeleton. Next focus is to harden the above and add the on-device STT/TTS prototype.
