# Security Policy

## Supported releases

Security fixes are prepared for the newest signed Skunkworks release. Pre-1.0
development builds are for evaluation and should not be treated as hardened
production software.

## Reporting a vulnerability

Report vulnerabilities privately to **ziegenbagel.gaming@gmail.com** or through
a private security-advisory channel for the release repository. Do not include an API key,
raw credential vault export, or unreviewed diagnostic bundle in a public issue.
Include the Skunkworks version, operating system, reproduction steps, expected
result, and observed result.

## Security boundaries

- Credentials belong in the operating-system vault or process environment.
- Every mutation is revalidated against live state and the selected execution
  policy; cached history is never authorization.
- Diagnostic logs apply credential redaction and bounded rotation.
- Database backups and exports may contain private game-account information and
  must be handled as sensitive local files.
- A signed package proves publisher identity and integrity; it does not make an
  operator's automation policy safe by itself.
