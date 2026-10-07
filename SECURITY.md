# Security

## Private data

The installer stores authentication settings in `config/settings.json` and camera definitions in `data/cameras.json` inside the selected installation folder. Network-camera credentials may be present in `data/cameras.json`. Both folders are excluded by `.gitignore`; never commit, attach, or publish them. The installer restricts their filesystem permissions to the installing user where the platform permits it.

The API never returns saved usernames, passwords, embedded URL credentials, or URL query values. Editing a network camera with blank credential fields preserves its existing private values.

## Network use

All viewer and management endpoints require a signed-in session. State-changing requests also require a per-session CSRF token. The health endpoint contains only the application name, version, and status.

The built-in server uses HTTP. Authentication prevents casual unauthorized access, but HTTP itself does not encrypt traffic. Use it only on a trusted LAN or over an already-connected Tailscale network. For untrusted networks, place the viewer behind a correctly configured HTTPS reverse proxy. Do not expose its port directly to the public internet.

## Reporting a vulnerability

Open a GitHub security advisory for this repository rather than placing credentials, private stream URLs, or exploit details in a public issue.
