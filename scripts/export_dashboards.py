#!/usr/bin/env python3
"""
Export HAAS dashboards from Superset.

This script exports all dashboards from a running Superset instance
to a ZIP file that can be bundled with the add-on.

Usage:
    1. Create dashboards using create_dashboards.py
    2. Run this script to export them
    3. Copy the output to superset/rootfs/etc/superset/dashboards/
"""

import requests
import json
import sys
from pathlib import Path
from typing import Optional

# Configuration
SUPERSET_URL = "http://localhost:8088"
USERNAME = "admin"
PASSWORD = "admin"
OUTPUT_DIR = Path(__file__).parent.parent / "superset" / "rootfs" / "etc" / "superset" / "dashboards"


class SupersetClient:
    """Client for interacting with Superset API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.csrf_token: Optional[str] = None
        self._login(username, password)

    def _login(self, username: str, password: str) -> None:
        """Authenticate with Superset."""
        # Get CSRF token
        response = self.session.get(f"{self.base_url}/api/v1/security/csrf_token/")
        if response.status_code == 200:
            self.csrf_token = response.json().get("result")
            self.session.headers["X-CSRFToken"] = self.csrf_token

        # Login
        response = self.session.post(
            f"{self.base_url}/api/v1/security/login",
            json={
                "username": username,
                "password": password,
                "provider": "db",
            },
        )

        if response.status_code != 200:
            raise Exception(f"Login failed: {response.text}")

        data = response.json()
        self.access_token = data.get("access_token")
        self.session.headers["Authorization"] = f"Bearer {self.access_token}"

        print(f"Logged in to Superset as {username}")

    def get_all_dashboards(self) -> list:
        """Get all dashboard IDs."""
        response = self.session.get(f"{self.base_url}/api/v1/dashboard/")
        if response.status_code == 200:
            return response.json().get("result", [])
        return []

    def export_dashboards(self, dashboard_ids: list) -> bytes:
        """Export dashboards as a ZIP file."""
        response = self.session.get(
            f"{self.base_url}/api/v1/dashboard/export/",
            params={"q": json.dumps(dashboard_ids)},
        )

        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Export failed: {response.text}")


def main():
    """Main entry point."""
    print("=" * 50)
    print("HAAS Dashboard Exporter")
    print("=" * 50)

    try:
        client = SupersetClient(SUPERSET_URL, USERNAME, PASSWORD)
    except Exception as e:
        print(f"Failed to connect to Superset: {e}")
        print(f"\nMake sure Superset is running at {SUPERSET_URL}")
        sys.exit(1)

    # Get all dashboards
    dashboards = client.get_all_dashboards()
    if not dashboards:
        print("\nNo dashboards found to export!")
        sys.exit(1)

    print(f"\nFound {len(dashboards)} dashboard(s):")
    dashboard_ids = []
    for dash in dashboards:
        print(f"  - {dash['dashboard_title']} (ID: {dash['id']})")
        dashboard_ids.append(dash["id"])

    # Export dashboards
    print("\nExporting dashboards...")
    zip_content = client.export_dashboards(dashboard_ids)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write ZIP file
    output_path = OUTPUT_DIR / "ha_defaults.zip"
    with open(output_path, "wb") as f:
        f.write(zip_content)

    print(f"\nExported to: {output_path}")
    print(f"File size: {len(zip_content):,} bytes")

    print("\n" + "=" * 50)
    print("Export complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
