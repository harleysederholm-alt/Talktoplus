"""TALK TO+ BDaaS backend regression tests."""
import os, requests, pytest, uuid

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://sovereign-edge-1.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "admin@talktoplus.io", "password": "Admin!2026"}

@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

@pytest.fixture(scope="session")
def H(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

# --- Auth ---
def test_login_admin():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["user"]["email"] == "admin@talktoplus.io"
    assert d["user"]["role"] == "super_admin"
    assert d["access_token"]

def test_login_invalid():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": "x@x.io", "password": "bad"}, timeout=30)
    assert r.status_code == 401

def test_register_new(H):
    email = f"test_{uuid.uuid4().hex[:8]}@test.io"
    r = requests.post(f"{BASE}/api/auth/register", json={"email": email, "password": "Test!2026", "full_name": "Test User"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == email

def test_me(H):
    r = requests.get(f"{BASE}/api/auth/me", headers=H, timeout=30)
    assert r.status_code == 200
    assert r.json()["email"] == "admin@talktoplus.io"

# --- Analytics ---
def test_heatmap(H):
    r = requests.get(f"{BASE}/api/analytics/heatmap", headers=H, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ["resources", "capabilities", "engagement"]:
        assert k in d and "score" in d[k] and "level" in d[k]

def test_gri(H):
    r = requests.get(f"{BASE}/api/analytics/global-risk-index", headers=H, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ["value", "trend", "active", "total"]:
        assert k in d

def test_risk_trend(H):
    r = requests.get(f"{BASE}/api/analytics/risk-trend?days=7", headers=H, timeout=30)
    assert r.status_code == 200
    assert len(r.json()) == 7

def test_distribution(H):
    r = requests.get(f"{BASE}/api/analytics/distribution", headers=H, timeout=30)
    assert r.status_code == 200
    assert len(r.json()) == 4

# --- Oracle / Swarm ---
def test_oracle(H):
    r = requests.get(f"{BASE}/api/oracle/alerts", headers=H, timeout=30)
    assert r.status_code == 200
    for a in r.json():
        for k in ["velocity", "z_score", "confidence"]:
            assert k in a

def test_bottlenecks(H):
    r = requests.get(f"{BASE}/api/swarm/bottlenecks", headers=H, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_fragments_count(H):
    r = requests.get(f"{BASE}/api/swarm/fragments/count", headers=H, timeout=30)
    assert r.status_code == 200
    assert r.json()["count"] > 0

# --- Signals ---
def test_signals_list_has_pending(H):
    r = requests.get(f"{BASE}/api/signals", headers=H, timeout=30)
    assert r.status_code == 200
    sigs = r.json()
    # Tenant-scoped: 4 default-tenant validated + 1 pending = 5
    assert len(sigs) >= 5
    assert any(s["status"] == "pending" for s in sigs)

def test_create_signal_auto_analyzes(H):
    r = requests.post(f"{BASE}/api/signals", headers=H,
        json={"content": "TEST_ critical resurssipula blocker", "business_unit": "QA"}, timeout=120)
    assert r.status_code == 200
    s = r.json()
    assert s["status"] == "pending"
    assert s["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert s["category"] in ["resources", "capabilities", "engagement", "process"]

def _make_pending(H):
    r = requests.post(f"{BASE}/api/signals", headers=H,
        json={"content": f"TEST_ pending {uuid.uuid4().hex[:6]} concern issue", "business_unit": "QA"}, timeout=120)
    return r.json()["id"]

def test_validate_decision(H):
    sid = _make_pending(H)
    r = requests.post(f"{BASE}/api/signals/{sid}/validate", headers=H, json={"decision": "validate", "note": "ok"}, timeout=120)
    assert r.status_code == 200
    s = r.json()
    assert s["status"] == "validated"
    assert s["action_card_id"] and s["swarm_fragment_id"]

def test_validate_override(H):
    sid = _make_pending(H)
    r = requests.post(f"{BASE}/api/signals/{sid}/validate", headers=H,
        json={"decision": "override", "override_risk_level": "CRITICAL"}, timeout=120)
    assert r.status_code == 200
    assert r.json()["status"] == "overridden"
    assert r.json()["override_risk_level"] == "CRITICAL"

def test_validate_dismiss(H):
    sid = _make_pending(H)
    r = requests.post(f"{BASE}/api/signals/{sid}/validate", headers=H, json={"decision": "dismiss"}, timeout=60)
    assert r.status_code == 200
    assert r.json()["status"] == "dismissed"

# --- Action Cards ---
def test_action_cards_list_and_score(H):
    r = requests.get(f"{BASE}/api/action-cards", headers=H, timeout=30)
    assert r.status_code == 200
    cards = r.json()
    assert len(cards) > 0
    cid = cards[0]["id"]
    r2 = requests.post(f"{BASE}/api/action-cards/{cid}/impact?score=4", headers=H, timeout=30)
    assert r2.status_code == 200
    assert r2.json()["impact_score"] == 4

# --- Strategy RAG ---
def test_strategy_crud(H):
    r = requests.post(f"{BASE}/api/strategy-docs", headers=H,
        json={"title": "TEST_doc", "content": "Test strategy content for testing"}, timeout=30)
    assert r.status_code == 200
    did = r.json()["id"]
    r2 = requests.get(f"{BASE}/api/strategy-docs", headers=H, timeout=30)
    assert any(d["id"] == did for d in r2.json())
    r3 = requests.delete(f"{BASE}/api/strategy-docs/{did}", headers=H, timeout=30)
    assert r3.status_code == 200

# --- Tenants ---
def test_tenants_list_and_create(H):
    r = requests.get(f"{BASE}/api/tenants", headers=H, timeout=30)
    assert r.status_code == 200
    assert len(r.json()) >= 3
    r2 = requests.post(f"{BASE}/api/tenants", headers=H,
        json={"name": f"TEST_{uuid.uuid4().hex[:6]}", "sector": "TestSector"}, timeout=30)
    assert r2.status_code == 200

# --- System Health ---
def test_system_health():
    r = requests.get(f"{BASE}/api/system/health", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert len(d["services"]) == 4
    for k in ["local_ai", "database", "vector_db", "mothership"]:
        assert k in d["services"]

# --- Webhook ---
def test_webhook_ingests():
    r = requests.post(f"{BASE}/api/webhook/default-tenant",
        json={"content": "TEST_ webhook signal", "business_unit": "Hooks", "author": "Bot"},
        headers={"X-Source": "howspace"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["accepted"] is True


# --- Reports ---
def test_executive_summary_pdf(H):
    r = requests.get(f"{BASE}/api/reports/executive-summary.pdf?days=30", headers=H, timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert len(r.content) > 5000  # real PDF, not stub
    assert r.content[:4] == b"%PDF"
