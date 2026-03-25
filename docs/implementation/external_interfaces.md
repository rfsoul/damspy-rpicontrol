# External Interfaces

## Content

This document describes how external repositories and AI agents should communicate with the `damspy-rpicontrol` service.

### Base URL

`http://<pi-ip>:8000`

Typical_base_ip = 10.0.1.195
Note that currently the base ip is usually the address up above.

- Replace `<pi-ip>` with the Raspberry Pi host IP on your LAN.
- FastAPI machine-readable contract endpoints:
  - Swagger UI: `http://<pi-ip>:8000/docs`
  - OpenAPI JSON: `http://<pi-ip>:8000/openapi.json`

Use `/openapi.json` as the canonical machine-readable contract, and use this Markdown document as the human quickstart.

### Endpoint Table

| Method | Path | Body schema | Success response | Common errors |
|---|---|---|---|---|
| GET | `/health` | None | `200` JSON: `{"status":"ok","service":"damspy-rpicontrol","hid_backend":"<backend-or-unavailable>","device":"RODE RXCC","vendor_id":"0x19F7","product_id":"0x008C"}` | `500` unexpected server error |
| POST | `/api/rf/start` | JSON object: `{"antenna":"main"\|"secondary","channel":0..80,"power":0..10}` | `200` JSON: `{"operation":"start_rf","status":"ok","detail":"...","reports_sent":<int>}` | `422` validation error; `503` device unavailable; `502` communication failure |
| POST | `/api/rf/start/ch0` | None | `200` JSON: `{"operation":"start_rf_ch0","status":"ok","detail":"...","reports_sent":<int>}` | `503` device unavailable; `502` communication failure |
| POST | `/api/rf/start/ch80` | None | `200` JSON: `{"operation":"start_rf_ch80","status":"ok","detail":"...","reports_sent":<int>}` | `503` device unavailable; `502` communication failure |
| POST | `/api/rf/stop` | None | `200` JSON: `{"operation":"stop_rf","status":"ok","detail":"Sent RF stop command.","reports_sent":<int>}` | `503` device unavailable; `502` communication failure |

### Important behavior notes

- RF control endpoints are POST-only.
- Device unavailable => `503`, communication failure => `502`.
- For `/api/rf/start`, request validation is strict:
  - `antenna` must be `main` or `secondary`
  - `channel` must be integer 0–80
  - `power` must be integer 0–10
  - unknown JSON fields are rejected (`422`)

### Copy-paste examples

#### curl (Linux/macOS)

```bash
PI=http://10.0.1.195:8000

curl -sS "$PI/health"

curl -sS -X POST "$PI/api/rf/start" \
  -H "Content-Type: application/json" \
  -d '{"antenna":"main","channel":0,"power":10}'

curl -sS -X POST "$PI/api/rf/start/ch0"
curl -sS -X POST "$PI/api/rf/start/ch80"
curl -sS -X POST "$PI/api/rf/stop"
```

#### PowerShell

```powershell
$Base = "http://10.0.1.195:8000"

Invoke-RestMethod -Uri "$Base/health" -Method GET

Invoke-RestMethod -Uri "$Base/api/rf/start" -Method POST -ContentType "application/json" -Body (@{
  antenna = "main"
  channel = 0
  power   = 10
} | ConvertTo-Json)

Invoke-RestMethod -Uri "$Base/api/rf/start/ch0" -Method POST
Invoke-RestMethod -Uri "$Base/api/rf/start/ch80" -Method POST
Invoke-RestMethod -Uri "$Base/api/rf/stop" -Method POST
```

#### Python (`requests`)

```python
import requests
import time

base = "http://10.0.1.195:8000"
timeout = 5

health = requests.get(f"{base}/health", timeout=timeout)
health.raise_for_status()

start = requests.post(
    f"{base}/api/rf/start",
    json={"antenna": "main", "channel": 0, "power": 10},
    timeout=timeout,
)
start.raise_for_status()

time.sleep(1.0)  # optional dwell time

stop = requests.post(f"{base}/api/rf/stop", timeout=timeout)
stop.raise_for_status()
```

### Integration sequence

Recommended control flow for automation:

1. `GET /health` (service reachability and backend visibility)
2. `POST /api/rf/start` (or fixed variants `/api/rf/start/ch0`, `/api/rf/start/ch80`)
3. Optional wait/dwell interval for the RF operation window
4. `POST /api/rf/stop`

### Retry and timeout guidance

- Use short request timeouts (for example 3–5 seconds) and fail fast.
- Retry policy suggestion:
  - Retry `502` and network timeouts with exponential backoff (for example 250ms, 500ms, 1s).
  - Do not blind-retry `503`; first poll `/health` until available.
  - Do not retry `422`; fix request payload.
- Keep retries bounded (for example max 3 attempts) to avoid duplicate control operations.

### Versioning / compatibility

- Contract version: `v1 (2026-03-25)`.
- Backward-compatible evolution should be additive when possible (new optional fields/endpoints).
- Breaking changes should bump the contract version and be reflected in both `/openapi.json` and this document.

---


## Editing Guidelines (Do Not Modify Below This Line)

This document describes **how the system interacts with external systems**.

Its purpose is to provide a clear overview of the **system boundary**.

Document any **interfaces between this system and external systems**.

Examples may include:

• APIs exposed by the system
• external APIs used by the system
• webhooks
• message queues
• scheduled triggers
• email integrations
• file imports or exports

For each interface, describe:

• the external system
• how communication occurs
• what events or data are exchanged

Example sections:

### External API

Describe any API endpoints exposed by the system.

### Webhooks / Event Triggers

Describe events that trigger processing in the system.

### Third-Party Services

Describe external services or platforms used by the system.

Use this document to describe:

• APIs
• event sources
• integrations
• external data flows

Avoid including:

• internal component communication
• implementation details
• engineering tasks

Internal system structure belongs in `architecture.md`.

Only edit the **Content section above** unless the documentation system itself is being changed.
