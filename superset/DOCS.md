# HAAS - Home Assistant Apache Superset

HAAS brings the power of Apache Superset to your Home Assistant installation, providing advanced data visualization and dashboarding capabilities for your smart home data.

## Overview

HAAS automatically connects to your Home Assistant Recorder database and provides pre-configured dashboards for common smart home data:

- **Temperature & Humidity**: Long-term trends from your climate sensors
- **Energy Usage**: Power consumption over time with daily/weekly aggregations
- **System Performance**: CPU, memory, and disk usage monitoring
- **Automation Activity**: Track when automations run and their patterns

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the HAAS add-on
3. Start the add-on
4. Click "Open Web UI" to access Superset

## Configuration

### Basic Setup (SQLite - Default)

If you're using Home Assistant's default SQLite database, no configuration is needed. HAAS automatically connects to `/config/home-assistant_v2.db`.

### MariaDB Setup

If you're using the MariaDB add-on for your Recorder:

```yaml
database_type: mysql
database_host: core-mariadb
database_port: 3306
database_name: homeassistant
database_user: homeassistant
database_password: your_password_here
```

### PostgreSQL Setup

For PostgreSQL databases:

```yaml
database_type: postgresql
database_host: your_postgres_host
database_port: 5432
database_name: homeassistant
database_user: homeassistant
database_password: your_password_here
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `database_type` | list | `sqlite` | Database type: `sqlite`, `mysql`, or `postgresql` |
| `database_host` | string | (empty) | Database hostname (for MySQL/PostgreSQL) |
| `database_port` | port | `3306` | Database port number |
| `database_name` | string | `homeassistant` | Database name |
| `database_user` | string | (empty) | Database username |
| `database_password` | password | (empty) | Database password |
| `superset_secret_key` | password | (auto) | Superset secret key (auto-generated if empty) |
| `admin_password` | password | (auto) | Admin user password (auto-generated if empty) |

## Accessing Superset

### Via Home Assistant Ingress (Recommended)

Click the "Open Web UI" button in the add-on panel. Authentication is handled by Home Assistant.

### Direct Access

If needed, you can access Superset directly at `http://your-ha-ip:8088`. Use the admin credentials shown in the add-on logs on first startup.

## Default Dashboards

HAAS includes pre-configured dashboards that work out of the box:

### Home Overview
- Temperature timeline from all temperature sensors
- Humidity trends
- Binary sensor activity (motion, doors, etc.)
- Entity count by domain

### Energy & Utilities
- Power consumption over time
- Daily/weekly/monthly energy totals
- Cumulative usage tracking

### Climate & Environment
- Indoor vs outdoor temperature comparison
- Thermostat activity and mode changes
- Air quality metrics (if available)

### System & Performance
- Home Assistant system metrics
- Database performance indicators
- Automation execution log

## Creating Custom Dashboards

1. Navigate to **Charts** in the Superset menu
2. Click **+ Chart** to create a new visualization
3. Select the "Home Assistant" database
4. Write a SQL query or use the visual query builder
5. Save and add to a new or existing dashboard

### Useful SQL Patterns

**Temperature data from long-term statistics:**
```sql
SELECT
    sm.statistic_id as entity_id,
    datetime(s.start_ts, 'unixepoch') as time,
    s.mean as temperature
FROM statistics s
JOIN statistics_meta sm ON s.metadata_id = sm.id
WHERE sm.unit_of_measurement IN ('°C', '°F')
ORDER BY s.start_ts DESC
LIMIT 10000
```

**Binary sensor events:**
```sql
SELECT
    sm.entity_id,
    s.state,
    datetime(s.last_changed_ts, 'unixepoch') as changed_at
FROM states s
JOIN states_meta sm ON s.metadata_id = sm.metadata_id
WHERE sm.entity_id LIKE 'binary_sensor.%'
ORDER BY s.last_changed_ts DESC
LIMIT 1000
```

**Energy consumption:**
```sql
SELECT
    sm.statistic_id as entity_id,
    datetime(s.start_ts, 'unixepoch') as time,
    s.sum as total_kwh
FROM statistics s
JOIN statistics_meta sm ON s.metadata_id = sm.id
WHERE sm.unit_of_measurement IN ('kWh', 'Wh')
ORDER BY s.start_ts
```

## Troubleshooting

### Add-on won't start
- Check the add-on logs for error messages
- Ensure you have at least 2GB RAM available
- Verify database connection settings if using MySQL/PostgreSQL

### No data in dashboards
- Verify your Recorder integration is working in Home Assistant
- Check that the database file exists at the expected location
- For SQLite: Ensure `/config/home-assistant_v2.db` is accessible

### Slow performance
- Consider using MariaDB instead of SQLite for large databases
- Reduce the time range in your queries
- Use the long-term statistics tables for historical data

### Database connection errors
- Verify hostname, port, username, and password
- For MariaDB add-on, use `core-mariadb` as the hostname
- Check network connectivity between containers

## Resource Requirements

- **Minimum RAM**: 1GB (2GB+ recommended)
- **CPU**: Any modern 64-bit processor
- **Disk**: 500MB for Superset metadata + your usage
- **Architectures**: amd64, aarch64 (ARM64)

## Support

For issues and feature requests, please visit:
https://github.com/rusackas/haas-addon/issues

## License

This add-on is licensed under the Apache License 2.0.
Apache Superset is also licensed under Apache 2.0.
