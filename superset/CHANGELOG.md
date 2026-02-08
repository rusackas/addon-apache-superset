# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-08

### Added
- Initial release of HAAS (Home Assistant Apache Superset)
- Apache Superset 4.1.1 as the base
- Automatic connection to Home Assistant Recorder database
- Support for SQLite, MariaDB, and PostgreSQL backends
- Home Assistant ingress integration
- Pre-configured default dashboards:
  - Home Overview (temperature, humidity, binary sensors)
  - Energy & Utilities (power consumption)
  - Climate & Environment (thermostat, air quality)
  - System & Performance (HA system metrics)
- Auto-generated admin credentials on first run
- Optimized for low memory usage (works on 2GB systems)
- Multi-architecture support (amd64, aarch64)

### Security
- WTF CSRF disabled (Home Assistant ingress handles authentication)
- Database connections are read-only by default
- Secret key auto-generation and persistence
