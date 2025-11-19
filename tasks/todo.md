# J.A.R.V.I.S Project - Prioritized Task List (Offline-first, Python-focused)

This file is the canonical prioritized list of work. We'll execute from top (most important) to bottom.

High-level goals
- Offline-first Python implementation.
- Privacy-by-default; local data storage with optional encrypted cloud sync later.
- Phase work so the user can test and confirm after each milestone.

Priority (Most → Least important)

1. Finalize Legal & Ethical Constraints
- Confirm removal/refusal of illegal features (bypass paywalls/DRM, unauthorized surveillance, unauthorized voice cloning, instructions enabling real-world genetic modification, hacking, etc.).
- Define explicit refusal protocols and user-defined ethical rules.
- Implement consent/permission flows for every sensitive capability.

2. Define MVP Feature Set (Offline-first)
- Voice assistant core: on-device wake-word, offline STT, offline TTS (prototype quality), simple command handling.
- Local project library (SQLite + file store) with autosave and versioning.
- Command interpreter with strict security policy enforcement.

3. Create `tasks/todo.md` (this file)

4. Scaffold Python backend (FastAPI)
- Provide local REST API for UI and other local clients.
- Serve static dashboard for local device control.

5. Local data store & project library
- SQLite DB schema for users, projects, organisms, devices, and logs.
- File store for images, audio, and media (organized per-project).

6. Implement Resource Manager, Resilience & Config
- Integrate `ResourceManager`, `resilience` (retry & circuit breaker), and `ConfigManager`.
- Add hot-reload and safe defaults.

7. On-device wake-word + offline STT/TTS prototype
- STT: VOSK or similar (local models) for speech-to-text.
- Wake word: VAD + lightweight keyword detection (porcupine/porcupine alternatives) or model-based detection.
- TTS: `pyttsx3` or local TTS models (coqui TTS / espeak-ng for prototype).

8. Command interpreter & security policy enforcement
- Use `EnterpriseSecurity` rules and an allowlist approach for critical commands.
- All device-control commands require confirmation & explicit pairing consent.

9. Organism simulator (safe, simulation-only)
- Implement trait-system, plausibility checks, and visual placeholder generator (images via local heuristics).
- No wet-lab instructions or real genetic-editing workflow.

10. Camera scanner prototype (OpenCV + local models)
- Local object detection/classification using lightweight models (MobileNet, TFLite).
- Barcode/QR scanning and basic material inference.

11. Measurement estimation & AR preview (prototype)
- Camera-based dimension estimation using monocular cues + reference object.
- AR preview via simple overlay in the web UI.

12. Local web UI (Flask/Lightweight) for dashboard and voice control
- Simple, responsive UI served locally for desktop use and remote device control via LAN.

13. Autosave & versioning
- Save projects automatically every 30–60s (configurable) with rollback support.

14. Testing suite & CI for core modules
- Unit tests for `jarvis` modules; integration tests for backend APIs.

15. Packaging: desktop extension / background service
- Provide a Python package, CLI, and platform service (systemd for Linux, launchd for macOS, Windows service) to run J in background.

16. Device sync scaffold (local beacon, mDNS/UDP)
- Local discovery and secure pairing (QR or proximity token for 5–10 min pairing).
- Encrypted state sync over LAN; USB/serial fallback for unconnected devices.

17. Local TTS voice tuning and human-like voices
- Improve voice quality while respecting licenses; allow per-user voice configuration.

18. Security hardening: encryption & permissions
- Encrypt sensitive data at rest using OS key stores where possible.
- Implement role & permission checks per-device and per-action.

19. Cloud sync adapter (deferred)
- Optional encrypted cloud backup; only enabled after user confirmation.

20. Documentation: `dev.md`, README, user guides
- Explain how to run, test, and extend the system. Add `dev.md` later with production removal notes.

21. Performance optimization and battery savings
- Background mode optimizations and CPU usage tuning.

22. Accessibility, localization, multi-language support

23. Novel-to-animation and video pipeline (deferred)
- Major multi-media system; research and prototype after core features exist.

24. Advanced features & safety review (home defense, printers, DNA mixing)
- Any feature that touches safety-critical domains undergoes safety/legal review; DNA mixing remains simulation-only with clear disclaimers.

25. Beta testing plan and phased rollout
- Create beta program, feedback collection, and telemetry (opt-in only).

Milestones & estimates (rough):
- Phase A (Weeks 0–6): items 1–8 (legal, MVP, backend scaffold, local DB, resource + resilience, STT/TTS prototype)
- Phase B (Weeks 7–14): items 9–15 (simulator, scanner, measurement, UI, autosave, tests, packaging)
- Phase C (Weeks 15–26): items 16–25 (device sync, voice tuning, security hardening, cloud adapter, docs, optimizations)

Next steps (after you confirm this plan):
1. I will create a minimal FastAPI scaffold and `tasks/todo.md` is now in the repo. (done)
2. Ask you to confirm the plan and the top 3 MVP features to focus on first.
3. After your confirmation I will implement the first coding task (scaffold backend + local data store) and run unit tests.

Notes & constraints
- I will only implement legal features and will explicitly refuse to implement illegal or harmful features.
- The system is Python-first; small amounts of non-Python (HTML/CSS for UI served by Python) will be used when necessary.
- All heavy ML models will be local, lightweight, and respect licensing; large models or cloud-based LLM features will be added later with opt-in.

Please review and confirm or request edits to priorities before I begin implementing the first technical task.
