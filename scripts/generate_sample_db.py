#!/usr/bin/env python3
"""
Generate a sample Home Assistant Recorder database for testing HAAS.

This creates a SQLite database with realistic sample data mimicking
the Home Assistant Recorder schema, useful for development and testing.
"""

import sqlite3
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
import json

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "test_data"
DB_PATH = OUTPUT_DIR / "home-assistant_v2.db"
DAYS_OF_DATA = 30
HOURS_PER_DAY = 24

# Sample entities to create
ENTITIES = {
    "temperature_sensors": [
        ("sensor.living_room_temperature", "°C", "Living Room Temperature"),
        ("sensor.bedroom_temperature", "°C", "Bedroom Temperature"),
        ("sensor.kitchen_temperature", "°C", "Kitchen Temperature"),
        ("sensor.outdoor_temperature", "°C", "Outdoor Temperature"),
        ("sensor.bathroom_temperature", "°C", "Bathroom Temperature"),
    ],
    "humidity_sensors": [
        ("sensor.living_room_humidity", "%", "Living Room Humidity"),
        ("sensor.bedroom_humidity", "%", "Bedroom Humidity"),
        ("sensor.bathroom_humidity", "%", "Bathroom Humidity"),
        ("sensor.outdoor_humidity", "%", "Outdoor Humidity"),
    ],
    "energy_sensors": [
        ("sensor.total_energy", "kWh", "Total Energy Consumption"),
        ("sensor.hvac_energy", "kWh", "HVAC Energy"),
        ("sensor.lighting_energy", "kWh", "Lighting Energy"),
    ],
    "binary_sensors": [
        ("binary_sensor.front_door", None, "Front Door"),
        ("binary_sensor.back_door", None, "Back Door"),
        ("binary_sensor.living_room_motion", None, "Living Room Motion"),
        ("binary_sensor.kitchen_motion", None, "Kitchen Motion"),
        ("binary_sensor.garage_door", None, "Garage Door"),
    ],
    "climate_entities": [
        ("climate.thermostat", None, "Main Thermostat"),
    ],
    "system_sensors": [
        ("sensor.processor_use", "%", "Processor Use"),
        ("sensor.memory_use_percent", "%", "Memory Use"),
        ("sensor.disk_use_percent", "%", "Disk Use"),
    ],
}


def create_schema(conn: sqlite3.Connection) -> None:
    """Create the Home Assistant Recorder database schema."""
    cursor = conn.cursor()

    # States metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS states_meta (
            metadata_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id VARCHAR(255) NOT NULL UNIQUE
        )
    """)

    # States table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS states (
            state_id INTEGER PRIMARY KEY AUTOINCREMENT,
            metadata_id INTEGER,
            state VARCHAR(255),
            attributes_id INTEGER,
            last_changed_ts REAL,
            last_updated_ts REAL,
            old_state_id INTEGER,
            FOREIGN KEY (metadata_id) REFERENCES states_meta(metadata_id)
        )
    """)

    # State attributes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS state_attributes (
            attributes_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash INTEGER,
            shared_attrs TEXT
        )
    """)

    # Statistics metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistics_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            statistic_id VARCHAR(255) NOT NULL UNIQUE,
            source VARCHAR(32),
            unit_of_measurement VARCHAR(255),
            has_mean INTEGER DEFAULT 0,
            has_sum INTEGER DEFAULT 0,
            name VARCHAR(255)
        )
    """)

    # Statistics table (hourly aggregates)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metadata_id INTEGER,
            start_ts REAL,
            mean REAL,
            min REAL,
            max REAL,
            sum REAL,
            state REAL,
            FOREIGN KEY (metadata_id) REFERENCES statistics_meta(id)
        )
    """)

    # Statistics short term (5-minute aggregates)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistics_short_term (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metadata_id INTEGER,
            start_ts REAL,
            mean REAL,
            min REAL,
            max REAL,
            sum REAL,
            state REAL,
            FOREIGN KEY (metadata_id) REFERENCES statistics_meta(id)
        )
    """)

    # Event types table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_types (
            event_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type VARCHAR(64) NOT NULL UNIQUE
        )
    """)

    # Event data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_data (
            data_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash INTEGER,
            shared_data TEXT
        )
    """)

    # Events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type_id INTEGER,
            data_id INTEGER,
            time_fired_ts REAL,
            FOREIGN KEY (event_type_id) REFERENCES event_types(event_type_id),
            FOREIGN KEY (data_id) REFERENCES event_data(data_id)
        )
    """)

    # Recorder runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recorder_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start DATETIME,
            end DATETIME,
            closed_incorrect INTEGER DEFAULT 0,
            created DATETIME
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_states_metadata_id ON states(metadata_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_states_last_updated_ts ON states(last_updated_ts)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_statistics_metadata_id ON statistics(metadata_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_statistics_start_ts ON statistics(start_ts)")

    conn.commit()


def generate_temperature(hour: int, base: float = 20.0, is_outdoor: bool = False) -> float:
    """Generate realistic temperature value based on time of day."""
    # Daily variation: cooler at night, warmer midday
    daily_variation = 3 * math.sin((hour - 6) * math.pi / 12)

    if is_outdoor:
        # Outdoor has larger swings
        daily_variation *= 2.5
        base = 15.0

    # Add some random noise
    noise = random.gauss(0, 0.5)

    return round(base + daily_variation + noise, 1)


def generate_humidity(hour: int, base: float = 50.0, is_outdoor: bool = False) -> float:
    """Generate realistic humidity value."""
    # Inverse of temperature pattern (higher humidity at night)
    daily_variation = -10 * math.sin((hour - 6) * math.pi / 12)

    if is_outdoor:
        daily_variation *= 1.5
        base = 60.0

    noise = random.gauss(0, 3)

    return max(20, min(95, round(base + daily_variation + noise, 1)))


def generate_energy_increment(hour: int) -> float:
    """Generate realistic energy consumption increment (kWh per hour)."""
    # Base load
    base = 0.3

    # Higher during waking hours
    if 7 <= hour <= 22:
        base += 0.5

    # Peak during morning and evening
    if 7 <= hour <= 9 or 17 <= hour <= 21:
        base += 0.8

    # Random variation
    noise = random.gauss(0, 0.1)

    return max(0.1, round(base + noise, 3))


def generate_system_metric(base: float = 30.0) -> float:
    """Generate realistic system metric (CPU/memory/disk usage)."""
    # Random walk with mean reversion
    variation = random.gauss(0, 5)
    return max(5, min(95, round(base + variation, 1)))


def populate_data(conn: sqlite3.Connection) -> None:
    """Populate the database with sample data."""
    cursor = conn.cursor()
    now = datetime.now()
    start_date = now - timedelta(days=DAYS_OF_DATA)

    print("Creating metadata entries...")

    # Create states_meta entries
    states_meta_ids = {}
    for category, entities in ENTITIES.items():
        for entity_id, unit, name in entities:
            cursor.execute(
                "INSERT INTO states_meta (entity_id) VALUES (?)",
                (entity_id,)
            )
            states_meta_ids[entity_id] = cursor.lastrowid

    # Create statistics_meta entries
    stats_meta_ids = {}
    numeric_entities = ["temperature_sensors", "humidity_sensors", "energy_sensors", "system_sensors"]
    for category in numeric_entities:
        for entity_id, unit, name in ENTITIES[category]:
            has_sum = 1 if category == "energy_sensors" else 0
            has_mean = 1 if category != "energy_sensors" else 0
            cursor.execute(
                """INSERT INTO statistics_meta
                   (statistic_id, source, unit_of_measurement, has_mean, has_sum, name)
                   VALUES (?, 'recorder', ?, ?, ?, ?)""",
                (entity_id, unit, has_mean, has_sum, name)
            )
            stats_meta_ids[entity_id] = cursor.lastrowid

    # Create event types
    event_types = [
        "homeassistant_start",
        "homeassistant_stop",
        "automation_triggered",
        "script_started",
        "service_called",
        "state_changed",
    ]
    event_type_ids = {}
    for event_type in event_types:
        cursor.execute(
            "INSERT INTO event_types (event_type) VALUES (?)",
            (event_type,)
        )
        event_type_ids[event_type] = cursor.lastrowid

    conn.commit()

    print("Generating statistics data...")

    # Generate hourly statistics
    energy_totals = {entity_id: 0.0 for entity_id, _, _ in ENTITIES["energy_sensors"]}

    for day in range(DAYS_OF_DATA):
        current_date = start_date + timedelta(days=day)

        for hour in range(HOURS_PER_DAY):
            ts = (current_date + timedelta(hours=hour)).timestamp()

            # Temperature sensors
            for entity_id, unit, name in ENTITIES["temperature_sensors"]:
                is_outdoor = "outdoor" in entity_id.lower()
                temp = generate_temperature(hour, is_outdoor=is_outdoor)
                cursor.execute(
                    """INSERT INTO statistics
                       (metadata_id, start_ts, mean, min, max, state)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (stats_meta_ids[entity_id], ts, temp, temp - 0.3, temp + 0.3, temp)
                )

            # Humidity sensors
            for entity_id, unit, name in ENTITIES["humidity_sensors"]:
                is_outdoor = "outdoor" in entity_id.lower()
                humidity = generate_humidity(hour, is_outdoor=is_outdoor)
                cursor.execute(
                    """INSERT INTO statistics
                       (metadata_id, start_ts, mean, min, max, state)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (stats_meta_ids[entity_id], ts, humidity, humidity - 2, humidity + 2, humidity)
                )

            # Energy sensors (cumulative)
            for entity_id, unit, name in ENTITIES["energy_sensors"]:
                increment = generate_energy_increment(hour)
                if "hvac" in entity_id:
                    increment *= 0.4
                elif "lighting" in entity_id:
                    increment *= 0.2
                energy_totals[entity_id] += increment
                cursor.execute(
                    """INSERT INTO statistics
                       (metadata_id, start_ts, sum, state)
                       VALUES (?, ?, ?, ?)""",
                    (stats_meta_ids[entity_id], ts, energy_totals[entity_id], increment)
                )

            # System sensors
            for entity_id, unit, name in ENTITIES["system_sensors"]:
                base = 30 if "processor" in entity_id else 45 if "memory" in entity_id else 55
                value = generate_system_metric(base)
                cursor.execute(
                    """INSERT INTO statistics
                       (metadata_id, start_ts, mean, min, max, state)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (stats_meta_ids[entity_id], ts, value, value - 5, value + 5, value)
                )

        # Commit each day
        if day % 5 == 0:
            conn.commit()
            print(f"  Generated day {day + 1}/{DAYS_OF_DATA}")

    print("Generating states data (last 10 days)...")

    # Generate states (only last 10 days, simulating purge_keep_days)
    states_start = now - timedelta(days=10)
    state_id = 0

    for day in range(10):
        current_date = states_start + timedelta(days=day)

        # Binary sensor events (random triggers throughout the day)
        for entity_id, _, name in ENTITIES["binary_sensors"]:
            # Generate 5-20 events per day per sensor
            num_events = random.randint(5, 20)
            if "motion" in entity_id:
                num_events = random.randint(20, 50)

            for _ in range(num_events):
                hour = random.randint(6, 23)  # More activity during waking hours
                minute = random.randint(0, 59)
                ts = (current_date + timedelta(hours=hour, minutes=minute)).timestamp()

                # Insert "on" state
                cursor.execute(
                    """INSERT INTO states
                       (metadata_id, state, last_changed_ts, last_updated_ts)
                       VALUES (?, 'on', ?, ?)""",
                    (states_meta_ids[entity_id], ts, ts)
                )

                # Insert "off" state shortly after
                ts_off = ts + random.randint(1, 300)  # 1 second to 5 minutes later
                cursor.execute(
                    """INSERT INTO states
                       (metadata_id, state, last_changed_ts, last_updated_ts)
                       VALUES (?, 'off', ?, ?)""",
                    (states_meta_ids[entity_id], ts_off, ts_off)
                )

        # Climate entity states
        climate_entity = ENTITIES["climate_entities"][0][0]
        climate_states = ["heat", "cool", "idle", "off"]
        for hour in range(24):
            ts = (current_date + timedelta(hours=hour)).timestamp()
            state = random.choice(climate_states)
            if 23 <= hour or hour <= 6:
                state = random.choice(["heat", "off"])
            cursor.execute(
                """INSERT INTO states
                   (metadata_id, state, last_changed_ts, last_updated_ts)
                   VALUES (?, ?, ?, ?)""",
                (states_meta_ids[climate_entity], state, ts, ts)
            )

    conn.commit()

    print("Generating events data...")

    # Generate events
    # Home Assistant starts (simulating restarts)
    num_restarts = random.randint(2, 5)
    for i in range(num_restarts):
        restart_day = random.randint(0, DAYS_OF_DATA - 1)
        restart_time = start_date + timedelta(days=restart_day, hours=random.randint(0, 23))
        ts = restart_time.timestamp()

        cursor.execute(
            "INSERT INTO event_data (shared_data) VALUES (?)",
            (json.dumps({}),)
        )
        data_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO events (event_type_id, data_id, time_fired_ts)
               VALUES (?, ?, ?)""",
            (event_type_ids["homeassistant_start"], data_id, ts)
        )

    # Automation triggers
    automations = [
        "automation.morning_lights",
        "automation.evening_routine",
        "automation.motion_lights",
        "automation.thermostat_schedule",
        "automation.door_notification",
    ]

    for day in range(DAYS_OF_DATA):
        current_date = start_date + timedelta(days=day)

        for automation in automations:
            # Each automation triggers 1-5 times per day
            num_triggers = random.randint(1, 5)
            if "motion" in automation:
                num_triggers = random.randint(10, 30)

            for _ in range(num_triggers):
                hour = random.randint(6, 23)
                minute = random.randint(0, 59)
                ts = (current_date + timedelta(hours=hour, minutes=minute)).timestamp()

                cursor.execute(
                    "INSERT INTO event_data (shared_data) VALUES (?)",
                    (json.dumps({"entity_id": automation, "name": automation.split(".")[-1].replace("_", " ").title()}),)
                )
                data_id = cursor.lastrowid

                cursor.execute(
                    """INSERT INTO events (event_type_id, data_id, time_fired_ts)
                       VALUES (?, ?, ?)""",
                    (event_type_ids["automation_triggered"], data_id, ts)
                )

    # Add a recorder run entry
    cursor.execute(
        """INSERT INTO recorder_runs (start, created)
           VALUES (?, ?)""",
        (now.isoformat(), now.isoformat())
    )

    conn.commit()
    print("Data generation complete!")


def main():
    """Main entry point."""
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")

    print(f"Creating sample database: {DB_PATH}")

    # Create and populate database
    conn = sqlite3.connect(DB_PATH)

    try:
        create_schema(conn)
        populate_data(conn)

        # Print summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM statistics")
        stats_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM states")
        states_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events")
        events_count = cursor.fetchone()[0]

        print("\n" + "=" * 50)
        print("Sample Database Summary")
        print("=" * 50)
        print(f"Location: {DB_PATH}")
        print(f"Statistics records: {stats_count:,}")
        print(f"States records: {states_count:,}")
        print(f"Events records: {events_count:,}")
        print(f"Time range: {DAYS_OF_DATA} days")
        print("=" * 50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
