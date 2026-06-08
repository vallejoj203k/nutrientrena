"""Tests for events and event-type endpoints."""
import pytest


@pytest.fixture(scope="module")
def event_type_id(client, admin_headers):
    r = client.post("/api/type-events", json={"name": "Test Type", "color": "#FF0000"},
                    headers=admin_headers)
    assert r.status_code == 200
    return r.json()["data"]["id"]


class TestTypeEvents:
    def test_create_type(self, client, admin_headers):
        r = client.post("/api/type-events", json={"name": "Coaching", "color": "#5B2D8E"},
                        headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "Coaching"

    def test_list_types(self, client, admin_headers):
        r = client.get("/api/type-events/find-all", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)

    def test_create_type_unauthenticated(self, client):
        r = client.post("/api/type-events", json={"name": "No auth"})
        assert r.status_code == 403

    def test_update_type(self, client, admin_headers, event_type_id):
        r = client.post(f"/api/type-events/update/{event_type_id}",
                        json={"color": "#00FF00"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["data"]["color"] == "#00FF00"


class TestSingleEvents:
    def test_create_event(self, client, admin_headers, event_type_id):
        r = client.post("/api/events", json={
            "title": "Test Event",
            "start_date": "2026-07-01T10:00:00",
            "end_date": "2026-07-01T11:00:00",
            "type_event_id": event_type_id,
            "recurrence": "none",
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["title"] == "Test Event"
        assert data["recurrence"] == "none"
        return data["id"]

    def test_search_events(self, client, admin_headers):
        r = client.get("/api/events/search?start=2026-07-01T00:00:00&end=2026-07-31T23:59:59",
                       headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)
        assert len(r.json()["data"]) >= 1

    def test_create_event_missing_title(self, client, admin_headers):
        r = client.post("/api/events", json={
            "start_date": "2026-07-01T10:00:00",
            "recurrence": "none",
        }, headers=admin_headers)
        assert r.status_code == 422


class TestRecurringEvents:
    def test_create_weekly_recurring(self, client, admin_headers, event_type_id):
        r = client.post("/api/events", json={
            "title": "Weekly Meeting",
            "start_date": "2026-07-07T09:00:00",
            "recurrence": "weekly",
            "recurrence_end_date": "2026-07-28",
            "type_event_id": event_type_id,
        }, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        # Must create 4 occurrences: July 7, 14, 21, 28
        assert data["count"] == 4
        assert data["group_id"] is not None

    def test_recurring_occurrences_are_searchable(self, client, admin_headers):
        r = client.get("/api/events/search?start=2026-07-01T00:00:00&end=2026-07-31T23:59:59",
                       headers=admin_headers)
        assert r.status_code == 200
        weekly = [e for e in r.json()["data"] if e["recurrence"] == "weekly"]
        assert len(weekly) >= 4

    def test_create_daily_recurring(self, client, admin_headers):
        r = client.post("/api/events", json={
            "title": "Daily Standup",
            "start_date": "2026-08-01T08:00:00",
            "recurrence": "daily",
            "recurrence_end_date": "2026-08-05",
        }, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["data"]["count"] == 5  # Aug 1-5

    def test_delete_group(self, client, admin_headers, event_type_id):
        # Create a series to delete
        r = client.post("/api/events", json={
            "title": "To Delete",
            "start_date": "2026-09-01T09:00:00",
            "recurrence": "weekly",
            "recurrence_end_date": "2026-09-15",
        }, headers=admin_headers)
        assert r.status_code == 200
        group_id = r.json()["data"]["group_id"]

        # Delete the whole group
        r2 = client.delete(f"/api/events/delete-group/{group_id}", headers=admin_headers)
        assert r2.status_code == 200
        assert r2.json()["data"]["deleted"] == 3  # Sep 1, 8, 15
