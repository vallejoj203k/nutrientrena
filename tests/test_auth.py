"""Tests for authentication endpoints."""


class TestLogin:
    def test_login_success(self, client, seed):
        r = client.post("/api/auth/login", json={
            "email": seed["admin_email"],
            "password": seed["admin_password"],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "Bearer"

    def test_login_wrong_password(self, client, seed):
        r = client.post("/api/auth/login", json={
            "email": seed["admin_email"],
            "password": "wrong-password",
        })
        assert r.status_code == 401
        assert r.json()["success"] is False

    def test_login_unknown_email(self, client):
        r = client.post("/api/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "whatever",
        })
        assert r.status_code == 401

    def test_login_missing_fields(self, client):
        r = client.post("/api/auth/login", json={"email": "x@x.com"})
        assert r.status_code == 422


class TestProtectedEndpoints:
    def test_me_without_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 403   # HTTPBearer raises 403 when no credentials

    def test_me_invalid_token(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer bad-token"})
        assert r.status_code == 401

    def test_me_with_valid_token(self, client, admin_headers):
        r = client.get("/api/auth/me", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["data"]["email"] == "admin@test.com"


class TestRefreshToken:
    def test_refresh_valid(self, client, seed):
        login = client.post("/api/auth/login", json={
            "email": seed["admin_email"],
            "password": seed["admin_password"],
        })
        refresh_token = login.json()["data"]["refresh_token"]
        r = client.put("/api/auth/refresh-token", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        assert "token" in r.json()["data"]

    def test_refresh_invalid_token(self, client):
        r = client.put("/api/auth/refresh-token", json={"refresh_token": "not-a-token"})
        assert r.status_code == 401


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
