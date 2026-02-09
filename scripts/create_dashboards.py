#!/usr/bin/env python3
"""
Create default dashboards for HAAS.

This script connects to a running Superset instance and programmatically
creates datasets, charts, and dashboards for Home Assistant data visualization.

Usage:
    1. Start Superset locally with the sample database mounted
    2. Run this script to create the default dashboards
    3. Export the dashboards using export_dashboards.py
"""

import os
import requests
import json
import time
from typing import Optional
import sys

# Configuration (can be overridden with environment variables)
SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088")
USERNAME = os.environ.get("SUPERSET_USER", "admin")
PASSWORD = os.environ.get("SUPERSET_PASSWORD", "admin")

# Dataset SQL definitions
DATASETS = {
    "temperature_history": {
        "name": "Temperature History",
        "sql": """
SELECT
    sm.statistic_id as entity_id,
    sm.name as sensor_name,
    datetime(s.start_ts, 'unixepoch', 'localtime') as time,
    s.mean as temperature,
    sm.unit_of_measurement as unit
FROM statistics s
JOIN statistics_meta sm ON s.metadata_id = sm.id
WHERE sm.unit_of_measurement IN ('°C', '°F')
ORDER BY s.start_ts DESC
""",
    },
    "humidity_history": {
        "name": "Humidity History",
        "sql": """
SELECT
    sm.statistic_id as entity_id,
    sm.name as sensor_name,
    datetime(s.start_ts, 'unixepoch', 'localtime') as time,
    s.mean as humidity,
    sm.unit_of_measurement as unit
FROM statistics s
JOIN statistics_meta sm ON s.metadata_id = sm.id
WHERE sm.unit_of_measurement = '%'
  AND sm.statistic_id LIKE '%humidity%'
ORDER BY s.start_ts DESC
""",
    },
    "energy_consumption": {
        "name": "Energy Consumption",
        "sql": """
SELECT
    sm.statistic_id as entity_id,
    sm.name as sensor_name,
    datetime(s.start_ts, 'unixepoch', 'localtime') as time,
    s.sum as total_kwh,
    s.state as hourly_kwh
FROM statistics s
JOIN statistics_meta sm ON s.metadata_id = sm.id
WHERE sm.unit_of_measurement IN ('kWh', 'Wh')
ORDER BY s.start_ts DESC
""",
    },
    "binary_sensor_events": {
        "name": "Binary Sensor Events",
        "sql": """
SELECT
    sm.entity_id,
    s.state,
    datetime(s.last_changed_ts, 'unixepoch', 'localtime') as changed_at,
    CASE
        WHEN sm.entity_id LIKE '%motion%' THEN 'Motion'
        WHEN sm.entity_id LIKE '%door%' THEN 'Door'
        WHEN sm.entity_id LIKE '%window%' THEN 'Window'
        ELSE 'Other'
    END as sensor_type
FROM states s
JOIN states_meta sm ON s.metadata_id = sm.metadata_id
WHERE sm.entity_id LIKE 'binary_sensor.%'
ORDER BY s.last_changed_ts DESC
LIMIT 10000
""",
    },
    "system_metrics": {
        "name": "System Metrics",
        "sql": """
SELECT
    sm.statistic_id as entity_id,
    sm.name as metric_name,
    datetime(s.start_ts, 'unixepoch', 'localtime') as time,
    s.mean as value,
    sm.unit_of_measurement as unit
FROM statistics s
JOIN statistics_meta sm ON s.metadata_id = sm.id
WHERE sm.statistic_id LIKE 'sensor.processor%'
   OR sm.statistic_id LIKE 'sensor.memory%'
   OR sm.statistic_id LIKE 'sensor.disk%'
ORDER BY s.start_ts DESC
""",
    },
    "automation_events": {
        "name": "Automation Events",
        "sql": """
SELECT
    json_extract(ed.shared_data, '$.entity_id') as automation_id,
    json_extract(ed.shared_data, '$.name') as automation_name,
    datetime(e.time_fired_ts, 'unixepoch', 'localtime') as triggered_at
FROM events e
JOIN event_types et ON e.event_type_id = et.event_type_id
JOIN event_data ed ON e.data_id = ed.data_id
WHERE et.event_type = 'automation_triggered'
ORDER BY e.time_fired_ts DESC
LIMIT 1000
""",
    },
    "climate_states": {
        "name": "Climate States",
        "sql": """
SELECT
    sm.entity_id,
    s.state as mode,
    datetime(s.last_changed_ts, 'unixepoch', 'localtime') as changed_at
FROM states s
JOIN states_meta sm ON s.metadata_id = sm.metadata_id
WHERE sm.entity_id LIKE 'climate.%'
ORDER BY s.last_changed_ts DESC
LIMIT 5000
""",
    },
    "entity_domains": {
        "name": "Entity Domains",
        "sql": """
SELECT
    SUBSTR(entity_id, 1, INSTR(entity_id, '.') - 1) as domain,
    COUNT(*) as entity_count
FROM states_meta
GROUP BY domain
ORDER BY entity_count DESC
""",
    },
}


class SupersetClient:
    """Client for interacting with Superset API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.csrf_token: Optional[str] = None
        self._login(username, password)

    def _login(self, username: str, password: str) -> None:
        """Authenticate with Superset using session-based auth."""
        # Login via web form to get session cookie
        login_url = f"{self.base_url}/login/"
        response = self.session.get(login_url)

        # POST login
        response = self.session.post(
            login_url,
            data={
                "username": username,
                "password": password,
            },
            allow_redirects=True,
        )

        if response.status_code != 200:
            raise Exception(f"Login failed: {response.status_code}")

        # Get CSRF token for API calls
        csrf_response = self.session.get(f"{self.base_url}/api/v1/security/csrf_token/")
        if csrf_response.status_code == 200:
            self.csrf_token = csrf_response.json().get("result")
            self.session.headers["X-CSRFToken"] = self.csrf_token

        print(f"Logged in to Superset as {username}")

    def get_database_id(self, name: str = "Home Assistant") -> Optional[int]:
        """Get the database ID by name."""
        response = self.session.get(f"{self.base_url}/api/v1/database/")
        if response.status_code == 200:
            databases = response.json().get("result", [])
            for db in databases:
                if db["database_name"] == name:
                    return db["id"]
        return None

    def create_dataset(self, database_id: int, name: str, sql: str) -> Optional[int]:
        """Create a virtual dataset from SQL."""
        # Check if dataset already exists
        response = self.session.get(
            f"{self.base_url}/api/v1/dataset/",
            params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": name}]})},
        )
        if response.status_code == 200:
            existing = response.json().get("result", [])
            if existing:
                print(f"  Dataset '{name}' already exists (ID: {existing[0]['id']})")
                return existing[0]["id"]

        # Create new virtual dataset from SQL
        response = self.session.post(
            f"{self.base_url}/api/v1/dataset/",
            json={
                "database": database_id,
                "table_name": name,
                "sql": sql,
            },
        )

        if response.status_code in (200, 201):
            dataset_id = response.json().get("id")
            print(f"  Created dataset '{name}' (ID: {dataset_id})")
            return dataset_id
        else:
            print(f"  Failed to create dataset '{name}': {response.text}")
            return None

    def create_chart(
        self,
        name: str,
        dataset_id: int,
        viz_type: str,
        params: dict,
    ) -> Optional[int]:
        """Create a chart."""
        # Check if chart already exists
        response = self.session.get(
            f"{self.base_url}/api/v1/chart/",
            params={"q": json.dumps({"filters": [{"col": "slice_name", "opr": "eq", "value": name}]})},
        )
        if response.status_code == 200:
            existing = response.json().get("result", [])
            if existing:
                print(f"  Chart '{name}' already exists (ID: {existing[0]['id']})")
                return existing[0]["id"]

        # Create new chart
        response = self.session.post(
            f"{self.base_url}/api/v1/chart/",
            json={
                "slice_name": name,
                "datasource_id": dataset_id,
                "datasource_type": "table",
                "viz_type": viz_type,
                "params": json.dumps(params),
            },
        )

        if response.status_code in (200, 201):
            chart_id = response.json().get("id")
            print(f"  Created chart '{name}' (ID: {chart_id})")
            return chart_id
        else:
            print(f"  Failed to create chart '{name}': {response.text}")
            return None

    def create_dashboard(self, name: str, slug: str, chart_ids: list) -> Optional[int]:
        """Create a dashboard with the given charts."""
        # Check if dashboard already exists
        response = self.session.get(
            f"{self.base_url}/api/v1/dashboard/",
            params={"q": json.dumps({"filters": [{"col": "dashboard_title", "opr": "eq", "value": name}]})},
        )
        if response.status_code == 200:
            existing = response.json().get("result", [])
            if existing:
                print(f"  Dashboard '{name}' already exists (ID: {existing[0]['id']})")
                return existing[0]["id"]

        # Create dashboard layout
        # Simple grid layout - 2 columns
        position_json = {}
        row = 0
        col = 0
        for i, chart_id in enumerate(chart_ids):
            chart_key = f"CHART-{chart_id}"
            position_json[chart_key] = {
                "type": "CHART",
                "id": chart_key,
                "children": [],
                "meta": {
                    "chartId": chart_id,
                    "width": 6,  # Half width (12 columns total)
                    "height": 50,
                },
            }
            col += 1
            if col >= 2:
                col = 0
                row += 1

        # Create dashboard
        response = self.session.post(
            f"{self.base_url}/api/v1/dashboard/",
            json={
                "dashboard_title": name,
                "slug": slug,
                "published": True,
            },
        )

        if response.status_code in (200, 201):
            dashboard_id = response.json().get("id")
            print(f"  Created dashboard '{name}' (ID: {dashboard_id})")

            # Add charts to dashboard
            for chart_id in chart_ids:
                self.session.post(
                    f"{self.base_url}/api/v1/dashboard/{dashboard_id}/charts",
                    json={"chart_id": chart_id},
                )

            return dashboard_id
        else:
            print(f"  Failed to create dashboard '{name}': {response.text}")
            return None


def create_all_dashboards(client: SupersetClient, database_id: int) -> None:
    """Create all default dashboards."""

    print("\nCreating datasets...")
    dataset_ids = {}
    for key, config in DATASETS.items():
        dataset_id = client.create_dataset(database_id, config["name"], config["sql"])
        if dataset_id:
            dataset_ids[key] = dataset_id
        time.sleep(0.5)  # Rate limiting

    print("\nCreating charts...")

    # Temperature chart
    temp_chart = client.create_chart(
        "Temperature Timeline",
        dataset_ids["temperature_history"],
        "echarts_timeseries_line",
        {
            "x_axis": "time",
            "metrics": ["temperature"],
            "groupby": ["entity_id"],
            "row_limit": 10000,
        },
    )

    # Humidity chart
    humidity_chart = client.create_chart(
        "Humidity Timeline",
        dataset_ids["humidity_history"],
        "echarts_timeseries_line",
        {
            "x_axis": "time",
            "metrics": ["humidity"],
            "groupby": ["entity_id"],
            "row_limit": 10000,
        },
    )

    # Energy chart
    energy_chart = client.create_chart(
        "Energy Consumption",
        dataset_ids["energy_consumption"],
        "echarts_timeseries_line",
        {
            "x_axis": "time",
            "metrics": ["total_kwh"],
            "groupby": ["entity_id"],
            "row_limit": 10000,
        },
    )

    # Binary sensor activity
    binary_chart = client.create_chart(
        "Binary Sensor Activity",
        dataset_ids["binary_sensor_events"],
        "echarts_timeseries_bar",
        {
            "x_axis": "changed_at",
            "metrics": [{"expressionType": "SIMPLE", "aggregate": "COUNT", "column": {"column_name": "state"}}],
            "groupby": ["sensor_type"],
            "time_grain_sqla": "P1D",
        },
    )

    # Entity domains pie chart
    domain_chart = client.create_chart(
        "Entities by Domain",
        dataset_ids["entity_domains"],
        "pie",
        {
            "groupby": ["domain"],
            "metrics": ["entity_count"],
        },
    )

    # System metrics
    system_chart = client.create_chart(
        "System Metrics",
        dataset_ids["system_metrics"],
        "echarts_timeseries_line",
        {
            "x_axis": "time",
            "metrics": ["value"],
            "groupby": ["entity_id"],
            "row_limit": 10000,
        },
    )

    # Automation events table
    automation_chart = client.create_chart(
        "Automation Events",
        dataset_ids["automation_events"],
        "table",
        {
            "all_columns": ["automation_name", "triggered_at"],
            "row_limit": 100,
        },
    )

    # Climate states
    climate_chart = client.create_chart(
        "Climate Activity",
        dataset_ids["climate_states"],
        "echarts_timeseries_bar",
        {
            "x_axis": "changed_at",
            "metrics": [{"expressionType": "SIMPLE", "aggregate": "COUNT", "column": {"column_name": "mode"}}],
            "groupby": ["mode"],
            "time_grain_sqla": "PT1H",
        },
    )

    print("\nCreating dashboards...")

    # Home Overview Dashboard
    home_charts = [c for c in [temp_chart, humidity_chart, binary_chart, domain_chart] if c]
    if home_charts:
        client.create_dashboard("Home Overview", "home-overview", home_charts)

    # Energy Dashboard
    energy_charts = [c for c in [energy_chart] if c]
    if energy_charts:
        client.create_dashboard("Energy & Utilities", "energy", energy_charts)

    # Climate Dashboard
    climate_charts = [c for c in [temp_chart, humidity_chart, climate_chart] if c]
    if climate_charts:
        client.create_dashboard("Climate & Environment", "climate", climate_charts)

    # System Dashboard
    system_charts = [c for c in [system_chart, automation_chart] if c]
    if system_charts:
        client.create_dashboard("System & Performance", "system", system_charts)


def main():
    """Main entry point."""
    print("=" * 50)
    print("HAAS Dashboard Creator")
    print("=" * 50)

    try:
        client = SupersetClient(SUPERSET_URL, USERNAME, PASSWORD)
    except Exception as e:
        print(f"Failed to connect to Superset: {e}")
        print(f"\nMake sure Superset is running at {SUPERSET_URL}")
        sys.exit(1)

    # Get Home Assistant database
    db_id = client.get_database_id("Home Assistant")
    if not db_id:
        print("\nHome Assistant database not found!")
        print("Please ensure the database connection is configured in Superset.")
        sys.exit(1)

    print(f"\nUsing database ID: {db_id}")

    # Create all dashboards
    create_all_dashboards(client, db_id)

    print("\n" + "=" * 50)
    print("Dashboard creation complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
