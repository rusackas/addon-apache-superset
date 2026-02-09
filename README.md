# Apache Superset Add-on for Home Assistant

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Powerful data visualization for your Home Assistant data.**

This add-on brings Apache Superset to Home Assistant, pre-configured to visualize your Recorder database with beautiful default dashboards.

## Features

- **Zero Configuration**: Works out of the box with your existing Home Assistant Recorder database
- **Pre-built Dashboards**: Includes dashboards for temperature, energy, system metrics, and more
- **Multiple Database Support**: Works with SQLite (default), MariaDB, and PostgreSQL
- **Native Integration**: Uses Home Assistant's ingress for seamless authentication
- **Long-term Statistics**: Leverages HA's statistics tables for efficient historical analysis

## Installation

### Add Repository to Home Assistant

1. Navigate to **Settings** > **Add-ons** > **Add-on Store**
2. Click the three dots in the top right corner
3. Select **Repositories**
4. Add this repository URL: `https://github.com/rusackas/addon-apache-superset`
5. Click **Add**

### Install the Add-on

1. Find "Apache Superset" in the add-on store
2. Click **Install**
3. Wait for the installation to complete
4. Click **Start**
5. Click **Open Web UI** to access Superset

## Configuration

For most users, no configuration is needed. The add-on automatically connects to your Home Assistant Recorder database.

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `database_type` | Database backend: `sqlite`, `mysql`, or `postgresql` | `sqlite` |
| `database_host` | Database host (MySQL/PostgreSQL only) | - |
| `database_port` | Database port | `3306` |
| `database_name` | Database name | `homeassistant` |
| `database_user` | Database username | - |
| `database_password` | Database password | - |

### MariaDB Example

If you're using the MariaDB add-on:

```yaml
database_type: mysql
database_host: core-mariadb
database_port: 3306
database_name: homeassistant
database_user: homeassistant
database_password: your_password
```

## Default Dashboards

This add-on ships with four pre-configured dashboards:

1. **Home Overview**: Temperature, humidity, binary sensor activity, entity statistics
2. **Energy & Utilities**: Power consumption, daily/weekly/monthly trends
3. **Climate & Environment**: Indoor vs outdoor temps, thermostat activity
4. **System & Performance**: CPU, memory, disk usage, automation logs

## Architecture Support

- amd64 (Intel/AMD 64-bit)
- aarch64 (ARM 64-bit, e.g., Raspberry Pi 4)

> **Note**: Minimum 2GB RAM recommended. Raspberry Pi 4 with 4GB+ works well.

## Documentation

See [DOCS.md](superset/DOCS.md) for detailed documentation.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Apache Superset is also licensed under Apache 2.0.
