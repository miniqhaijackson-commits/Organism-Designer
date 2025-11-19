# J.A.R.V.I.S. — Legal & Ethical Constraints

This document records the high-level legal and ethical constraints for the J.A.R.V.I.S. prototype. The project follows a privacy-by-default and safety-first posture: any feature that could enable harm, illegal activity, or privacy invasion is explicitly refused or requires opt-in plus human review.

Core refusal rules
- No code or features will be implemented that enable illegal activity, including but not limited to:
  - Instructions for bypassing paywalls, DRM, or tamper-resistance.
  - Hacking, unauthorized access, or exploitation of systems.
  - Creation or operational instructions for biological manipulation that enable real-world genetic editing, lab protocols, or wet-lab procedures.
  - Advice or tools for manufacturing weapons or facilitating violent wrongdoing.

- No unauthorized surveillance or privacy-invading features:
  - No hidden or background audio/video surveillance features without explicit, informed consent from all affected parties.
  - No covert data collection: all data collection is declared, local-first, and opt-in.

- Voice cloning and identity-sensitive features:
  - Disallow or require explicit consent and clear legal review for voice cloning of an identified person.

Data handling and storage
- Default: all sensitive data is stored locally on the user's device (`data/`), not sent to external services.
- Optional cloud sync must be explicit, encrypted, and opt-in.
- Audit logs are append-only and stored locally for traceability: `data/jarvis_settings.log`.

User-facing refusal behavior
- When a user requests a refused action, the system must:
  1. Decline the request with a clear explanation why.
  2. Offer safe, legal alternatives where possible (e.g., simulated outputs, high-level conceptual summaries without step-by-step actionable instructions).

Developer guidelines
- All new features touching safety-critical domains require a short risk assessment entry in `docs/ETHICS.md` before implementation.
- Changes to refusal rules require maintainer review and an explicit change-log entry.

Contact & review
- For questions about these constraints, create an issue and tag `security` and `ethics` labels.
