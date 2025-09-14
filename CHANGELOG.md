# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to
Semantic Versioning.

## [0.3.3] - 2025-09-14
### Added
- Expanded record types: SRV, CAA, DNSKEY, DS, RP, NAPTR, RRSIG, CERT, DNAME, IPSECKEY, OPENPGPKEY, SPF, SSHFP.
- SIGHUP reload workflow: `labdns reload` CLI and server-side reload callback.
- Daemon mode: PID file creation/cleanup, optional log file, configurable `--log-level`/`--verbose`.
- Configuration: INI file support, LABDNS_* environment overrides, `--config` option, `config init` and `config show` commands.
- Multi-zone loader: merge all files in a zones directory.
- GUI wrapper (`labdns-gui.sh`): start/check/reload/logs/stop/settings; create new zone; add/remove records; prompt to reload after changes.
- Docker/Compose: container image with non-root user, NET_BIND_SERVICE, healthcheck.

### Changed
- README updated with installation, configuration, Docker, GUI, and supported types.

### Fixed
- Minor robustness improvements in logging and PID handling.

## [0.1.0] - 2025-09-14
### Added
- Core UDP DNS server with non-blocking loop and graceful shutdown (SIGINT/SIGTERM).
- DNS query handling using dnslib with support for A and AAAA records.
- Minimal zonefile loader (dnspython) and in-memory resolver for A/AAAA.
- CLI with `start`, `check`, `version` commands.
- Multi-zone directory loading and merge; default `./zones` support.
- Resolver and handler extended to support CNAME, MX, TXT (multi-string), SOA, NS, PTR.
- Basic wildcard matching and CNAME chaining; authority section logic (NS/SOA).
- SIGHUP-based hot reload; `labdns reload` helper.
- Daemon mode with PID file creation/cleanup; optional log file and log level.
- Configuration file and environment variable support; `config init` and `config show`.
- Dockerfile and docker-compose for containerized deployment.

### Changed
- README expanded with installation, usage, configuration, and Docker instructions.

### Fixed
- N/A (initial release)
