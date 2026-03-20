# 自动联网 (auto_link)

Auto reconnect & re-auth for captive-portal networks (e.g. campus/LAN portals) using Playwright.

## What It Does

- Periodically checks connectivity by requesting a random URL from `URLS` (HTTP 200 = online)
- Applies time-window rules from `TIME_QUANTUMS`
- When offline, opens `LOGIN_URL` and fills/clicks elements defined by `LOGIN_MESSAGE`
- Writes logs to `app.log`

## Run (Recommended)

Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Prepare config:

```bash
copy settings.env.example settings.env
```

Start GUI (default):

```bash
python main.py
```

Run CLI loop (no GUI):

```bash
python main.py --cli
```

You can also run the modules directly:

```bash
python gui.py
python link.py
```

## Notes About the GUI

- The UI inputs do not require quotes; the GUI writes `settings.env` in the correct format automatically.
- The right-side output follows the contents written to `app.log` during this run.

## Configuration (settings.env)

The script loads `settings.env` using `python-dotenv`. Values are stored as Python literals.

- `URLS`: `["https://www.baidu.com", "https://www.jd.com"]`
- `LOGIN_URL`: `"http://192.168.254.25/"`
- `LOGIN_SUCCESS_URL`: `"http://192.168.254.25/"` (or the URL you expect after login)
- `NUMBER`: `"your_account"`
- `PASSWORD`: `"your_password"`
- `TIME_QUANTUMS`: `[{"start":"00:00","end":"23:59","allow":1}]`
- `FREQUENCY`: `10` (minutes)
- `LOGIN_MESSAGE`: `{"number_input":"...","password_input":"...","login_button":"..."}`
- `BROWER_PATH`: browser executable path (the key name matches the code)

## Package to Windows EXE (PyInstaller)

Use `main.py` as the packaging entry:

```bash
pyinstaller -F -w -i linkURL.ico --name 自动联网 main.py
```

Then copy `settings.env.example` next to the generated exe and rename it to `settings.env`.

## Troubleshooting

- Connectivity checks always fail: replace/add URLs in `URLS` that are reachable in your environment.
- Login page does not open: ensure `LOGIN_URL` contains the scheme (`http://` or `https://`).
- Selector errors: verify `LOGIN_MESSAGE` matches the actual portal page elements.
