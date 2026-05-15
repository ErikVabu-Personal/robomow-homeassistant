"""Constants for the Robomow3 integration."""

DOMAIN = "robomow3"
MANUFACTURER = "Robomow"

# ── Auth server (myrobomow.robomow.com) ──────────────────────────────
AUTH_SUBDOMAIN = "myrobomow"
AUTH_BASE_URL = f"https://{AUTH_SUBDOMAIN}.robomow.com/api"
AUTH_ENDPOINT = f"{AUTH_BASE_URL}/v2/mobile/authenticate"

# ── IoT API Gateway (AWS) ──────────────────────────────────────
IOT_BASE_URL = "https://lvxp2hg7h7.execute-api.eu-central-1.amazonaws.com/Prod"
API_BRAND = "robomow"

# ── Dashboard top-level state ──────────────────────────────────
# Empirically confirmed:
#   state=2  → mower docked in base, battery full (probe: 2026-05-02)
#   state=3  → mower physically mowing (observed: 2026-05-11)
STATE_MAP = {
    0: "idle",
    1: "charging",
    2: "in_base",       # docked / standby
    3: "going_home",    # confirmed via testing 2026-05-15
    4: "mowing",        # confirmed via testing 2026-05-15
    5: "edge",
    6: "error",
    7: "paused",
}

# ── Battery state ──────────────────────────────────────────────
BATTERY_STATE_MAP = {
    0: "unknown",
    1: "low",
    2: "ok",
    3: "full",
    4: "charging",
}

# ── Polling interval ───────────────────────────────────────────
DEFAULT_SCAN_INTERVAL = 60  # seconds
