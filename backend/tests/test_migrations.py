from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_initial_migration_sql(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-only-not-a-production-secret")
    output = StringIO()
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"), output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE hotels" in sql
    assert "CREATE TABLE devices" in sql
    assert "FOREIGN KEY(hotel_id) REFERENCES hotels (id)" in sql
    assert "INSERT INTO hotels" not in sql
    assert "INSERT INTO devices" not in sql

    assert "CREATE TABLE users" in sql
    assert "CREATE TABLE login_sessions" in sql
    assert "CREATE TABLE maintenance_schedules" in sql
    assert "uq_schedule_device_month" in sql
    assert "ck_schedule_month" in sql
    assert "DROP TABLE" not in sql
    assert "INSERT INTO users" not in sql
    assert "CREATE TABLE visits" in sql
    assert "FOREIGN KEY(schedule_id) REFERENCES maintenance_schedules (id)" in sql
    assert "UNIQUE (schedule_id)" in sql
    assert "ck_visit_coordinates" in sql
    assert "INSERT INTO visits" not in sql

    assert "CREATE TABLE checklist_templates" in sql
    assert "CREATE TABLE checklist_items" in sql
    assert "CREATE TABLE checklist_results" in sql
    assert "uq_checklist_visit_item" in sql
    assert "ADD CONSTRAINT ck_visit_checkout" in sql
    assert "'submitted'" in sql
    assert "INSERT INTO checklist" not in sql

    assert "CREATE TABLE visit_events" in sql
    assert "uq_visit_event_version" in sql
    assert "ck_visit_event_action" in sql
    assert "'revision_requested'" in sql
    assert "'approved'" in sql
    assert "INSERT INTO visit_events" not in sql

    assert "ADD COLUMN brand" in sql
    assert "ADD COLUMN model" in sql
    assert "ADD COLUMN ip_address" in sql
    assert "ADD COLUMN mac_address" in sql

    assert "CREATE TABLE hotel_visits" in sql
    assert "CREATE TABLE hotel_visit_devices" in sql
    assert "CREATE TABLE device_photos" in sql
    assert "CREATE TABLE hotel_visit_events" in sql
    assert "uq_hotel_visit_device" in sql
    assert "INSERT INTO hotel_visits" not in sql

    assert "CREATE TABLE network_speedtests" in sql
    assert "ck_speedtest_band" in sql
    assert "INSERT INTO network_speedtests" not in sql

    assert "ADD COLUMN customer_name" in sql
    assert "ADD COLUMN maintenance_profile" in sql
