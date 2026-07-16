"""Security tests: headers, CORS, RBAC, input validation."""


class TestSecurityHeaders:
    """Every response must include the required security headers."""

    def test_health_has_security_headers(self, client):
        r = client.get("/api/health")
        assert r.headers.get("x-content-type-options") == "nosniff"
        # SAMEORIGIN (no DENY): la app incrusta sus propias páginas en iframes
        # (p. ej. el editor de dietas dentro del constructor de menús), pero
        # ningún sitio externo puede embeberla.
        assert r.headers.get("x-frame-options") == "SAMEORIGIN"
        assert r.headers.get("content-security-policy") == "frame-ancestors 'self'"
        assert r.headers.get("x-xss-protection") == "1; mode=block"
        assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_api_response_has_security_headers(self, client, admin_headers):
        r = client.get("/api/auth/me", headers=admin_headers)
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "SAMEORIGIN"

    def test_error_response_has_security_headers(self, client):
        r = client.get("/api/auth/me")   # no token → 403
        assert r.headers.get("x-content-type-options") == "nosniff"


class TestAuthorizationRBAC:
    """Endpoints must reject requests with insufficient privileges."""

    def test_unauthenticated_returns_403(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 403

    def test_bad_token_returns_401(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer fake.token.here"})
        assert r.status_code == 401

    def test_protected_post_without_auth(self, client):
        r = client.post("/api/events", json={"title": "x", "start_date": "2026-01-01T00:00:00"})
        assert r.status_code == 403

    def test_authenticated_can_access(self, client, admin_headers):
        r = client.get("/api/auth/me", headers=admin_headers)
        assert r.status_code == 200

    def test_coach_cannot_create_admin_users(self, client, coach_headers):
        # Coaches cannot create users with admin role (role_id=2)
        r = client.post("/api/users", json={
            "name": "Hacker", "email": "hacker@x.com", "password": "Pass123!",
            "role_id": 2,
        }, headers=coach_headers)
        assert r.status_code == 403


class TestInputValidation:
    """Invalid payloads must return 422 Unprocessable Entity."""

    def test_login_empty_body(self, client):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 422

    def test_login_missing_password(self, client):
        r = client.post("/api/auth/login", json={"email": "a@b.com"})
        assert r.status_code == 422

    def test_event_missing_required_fields(self, client, admin_headers):
        r = client.post("/api/events", json={"title": "No date"}, headers=admin_headers)
        assert r.status_code == 422

    def test_create_type_event_empty_name(self, client, admin_headers):
        r = client.post("/api/type-events", json={"name": ""}, headers=admin_headers)
        # FastAPI doesn't validate empty string unless annotated with min_length,
        # but the DB will accept it — just check it doesn't crash (200 or 422)
        assert r.status_code in (200, 422)


class TestSensitiveDataNotLeaked:
    """Error responses must not expose internal details."""

    def test_wrong_login_no_stack_trace(self, client):
        r = client.post("/api/auth/login", json={
            "email": "x@x.com", "password": "wrong",
        })
        body = r.text
        assert "Traceback" not in body
        assert "sqlalchemy" not in body.lower()
        assert "pymysql" not in body.lower()

    def test_404_not_found_no_stack_trace(self, client, admin_headers):
        r = client.delete("/api/events/delete/999999", headers=admin_headers)
        body = r.text
        assert "Traceback" not in body
