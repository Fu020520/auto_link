# Auto Reconnect & Re-Auth (OpenClaw “Lobster” Robot / Captive Portal Networks)

When OpenClaw “Lobster” robots (or any always-on devices) are deployed in labs, campus networks, or other environments with captive portals, the network may drop periodically or require re-authentication. This project solves that by continuously checking connectivity and, when offline, automatically opening the portal/login page and submitting credentials.

Entry point: `link.py` (runs in a loop)

## What It Does

- Checks connectivity by sending an HTTP request to a random URL from `URLS` (HTTP 200 = online)
- Applies time-window rules to decide whether it should run
- When offline, opens `LOGIN_URL` and fills/clicks fields defined in `LOGIN_MESSAGE`
- Writes logs to both console and `app.log`

## Quick Start

1. Install dependencies

```bash
pip install -r requirements.txt
```

2. Install Playwright browser runtime (choose one)

- Use Playwright-managed Chromium (recommended):

```bash
python -m playwright install chromium
```

- Use your local Chrome/Chromium: set `BROWER_PATH` in `settings.env` to the browser executable path

3. Configure `settings.env`

Copy `settings.env.example` to `settings.env`, then edit it to match your portal page and your credentials. Keep credentials local and do not commit them to a public repository.

```bash
copy settings.env.example settings.env
```

4. Run

```bash
python link.py
```

Stop with `Ctrl + C`.

## Configuration (settings.env)

The script loads and parses `settings.env` using `python-dotenv`.

- `URLS`
  - Purpose: a list of URLs used for connectivity checks (one is chosen randomly).
  - Example: `["https://www.google.com", "https://www.cloudflare.com"]`
- `LOGIN_URL`
  - Purpose: the portal/login page URL (Playwright navigates to it).
  - Tip: include the scheme, e.g. `http://192.168.254.25/` or `https://...` (an IP without scheme may fail).
- `NUMBER`
  - Purpose: username/account value.
- `PASSWORD`
  - Purpose: password value.
- `TIME_QUANTUMS`
  - Purpose: allow/deny time ranges.
  - Format: `[{"start":"HH:MM","end":"HH:MM","allow":1 or 0}, ...]`
  - Rule: if the current time falls into a range with `allow:0`, the script skips checks/login until allowed.
- `FREQUENCY`
  - Purpose: loop interval in minutes.
- `LOGIN_MESSAGE`
  - Purpose: selectors for the username input, password input, and login button.
  - Format: `{"number_input":"...","password_input":"...","login_button":"..."}`
  - Note: Playwright supports CSS selectors; XPath can be used via `xpath=...`.
- `BROWER_PATH`
  - Purpose: optional browser executable path.
  - Note: the key name is `BROWER_PATH` to match the current code.
  - Windows path examples:
    - `C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe`
    - `C:/Program Files/Google/Chrome/Application/chrome.exe`

## Troubleshooting

- Connectivity checks always fail: make sure URLs in `URLS` are reachable in your environment (proxy/firewall/DNS).
- Login page does not open: ensure `LOGIN_URL` includes the correct scheme and path.
- Selector errors: verify `LOGIN_MESSAGE` matches the actual portal page elements.
- Still considered offline after login: replace/add `URLS` with stable sites that are accessible on your network.
