# Security notes

Presidio detects and anonymizes PII; it does not encrypt data. Encryption in transit (TLS) and at rest must be supplied by the hosting/database layer. Secrets belong in Vercel environment variables or a secret manager, never in source control.

Use Synthea for the hackathon so no real patient data is needed. For real deployments, add formal access controls, data retention rules, audit review, key management, network controls and organizational/legal compliance before processing PHI.
