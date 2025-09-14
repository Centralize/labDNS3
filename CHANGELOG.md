# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to
Semantic Versioning.

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

