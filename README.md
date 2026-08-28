# GAME4ALL MANAGER PRO

Royal Gold Streamlit desk for listing stock, sales copy, marketplace fees, and monthly profit.

This app manages **listings only**. Do not import email:password lines or account-login secrets.

## Run

```bash
python -m pip install -r requirements.txt
copy .env.example .env
python -m streamlit run app.py
```

Open `http://127.0.0.1:8501`.

## Project files

| File | Role |
| --- | --- |
| `app.py` | UI, Royal Gold / Cyberpunk / Dark themes, audio toggles, license gate, four desk tabs |
| `database.py` | SQLite inventory, sales, settings, license table |
| `license.py` | Key format, expiry, activation, CLI generator |
| `pricing.py` | Marketplace fees and estimated selling prices |
| `parser.py` | Pack importer (CSV / TXT) and sales-copy builder |
| `alerts.py` | Discord / Telegram sale webhooks |
| `i18n.py` | English / French / Arabic |
| `static/theme.css` | Theme tokens and 3D gold controls |
| `requirements.txt` | Python dependencies |

Data is stored in `data/game4all_manager.db` (created on first launch).

## License gate

The dashboard stays locked until a valid key is activated. Activation is saved in SQLite `settings`, so the key is not asked again on every Streamlit rerun. Expired or revoked keys are cleared and return to the activation screen.

Key format:

```text
GAME4ALL-PRO-2026-LIFE-XXXX   lifetime (no expiry)
GAME4ALL-PRO-2026-YR-XXXX     annual (365 days)
GAME4ALL-PRO-2026-MO-XXXX     monthly (30 days)
```

Starter keys (seeded once into an empty `licenses` table):

```text
GAME4ALL-PRO-2026-LIFE-K7M2
GAME4ALL-PRO-2026-YR-N4QP
GAME4ALL-PRO-2026-MO-T8RX
```

## Generate and manage keys

Hidden operator vault:

1. On the activation screen (or in the sidebar after unlock), open **Operator vault**.
2. Enter `LICENSE_ADMIN_PIN` from `.env` (default: `g4a-royal-admin`).
3. Choose lifetime / annual / monthly, add an internal note, generate the key, then copy it.
4. Revoke a key from the same table. A revoked key immediately locks any workstation using it.

Shortcut URL: `http://127.0.0.1:8501/?admin=1`

Command line (from the project folder):

```bash
python -m license generate lifetime --note "shop-pc"
python -m license generate annual --note "reseller-a"
python -m license generate monthly --note "trial"
python -m license list
```

Direct SQL (optional):

```sql
INSERT INTO licenses (license_key, key_hash, plan, status, note, issued_at, expires_at, activated_at)
VALUES (
  'GAME4ALL-PRO-2026-LIFE-ABCD',
  '',
  'lifetime',
  'active',
  'manual insert',
  datetime('now'),
  NULL,
  ''
);
```

Prefer `python -m license generate` so the hash and expiry dates stay consistent.

## Alerts

Copy `.env.example` to `.env` and set Discord / Telegram webhooks if you want a ping when a sale is logged.
