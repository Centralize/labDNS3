labDNS 3.0
==========

Installation
- From PyPI (recommended):
  - Create a virtualenv (recommended on Debian/Ubuntu due to PEP 668):
    - `python3 -m venv .venv && source .venv/bin/activate`
  - `python -m pip install -U pip`
  - `python -m pip install labdns`
- With pipx:
  - `pipx install labdns`
- From source (development):
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `python -m pip install -U pip`
  - `python -m pip install -e .[test]`

Quick start
- Prepare a zonefile, e.g. `examples/example.zone`
- Validate single file: `labdns check examples/example.zone`
- Validate a directory: `labdns check examples/zones`
- Start with one zonefile (unprivileged port): `labdns start --zonefile examples/example.zone --port 5353 --interface 127.0.0.1`
- Start with a zones directory: `labdns start --zones-dir examples/zones --port 5353 --interface 127.0.0.1`

Daemon & logging
- Run in background: `labdns start --zones-dir examples/zones --daemon`
- PID file: `--pid-file ./labdns.pid` (default in daemon mode)
- Log file: `--log-file ./labdns.log` (default in daemon mode)
- Log level: `--log-level DEBUG|INFO|WARNING|ERROR|CRITICAL` (or `--verbose`)

Reload
- Send SIGHUP: `labdns reload --pid-file ./labdns.pid` or `--pid <PID>`
- Tip: find PID with `pgrep -f labdns` if running in foreground

Configuration
- Create a config file: `labdns config init --path ./labdns.ini`
- Edit values under `[labdns]` (zonefile/zones_dir, port, interface, daemon, pid/log paths)
- Show effective config (file + environment): `labdns config show`
- Use a specific config file globally: `labdns --config ./labdns.ini start`
- Environment overrides (examples): `LABDNS_ZONES_DIR=./zones LABDNS_PORT=5353 labdns start`

Docker
- Build image: `docker build -t labdns .`
- Run with docker-compose: `docker-compose up -d`
  - Mount your zonefiles into `./examples/zones` or adjust the volume in compose
  - The container exposes UDP 53 and runs as a non-root user; compose grants NET_BIND_SERVICE to bind port 53
- Direct docker run example:
  - `docker run -d --name labdns --cap-add=NET_BIND_SERVICE -p 53:53/udp -v $(pwd)/examples/zones:/zones:ro labdns:latest`

Supported Python versions
- Python 3.10, 3.11, 3.12

Supported record types
- A, AAAA, CNAME, MX, TXT (multi-string), SOA, NS, PTR
- SRV, CAA, DNSKEY, DS, RP, NAPTR, RRSIG, CERT, DNAME, IPSECKEY, OPENPGPKEY, SPF
- SSHFP

Features
- Multi-zone directory loading (merge all files under a directory)
- Wildcard matching (*.domain) and CNAME chaining with limits
- Authority section: NS on positive responses; SOA for NXDOMAIN/NODATA
- Hot reload on SIGHUP; `labdns reload` helper
- Daemon mode with PID/log files; configurable log level
- Config via file and environment; CLI overrides

Query examples
- A record: `dig @127.0.0.1 -p 5353 www.example.test A`
- AAAA record: `dig @127.0.0.1 -p 5353 api.example.test AAAA`
- SRV record: `dig @127.0.0.1 -p 5353 _sip._tcp.epic2.test SRV`
- CAA record: `dig @127.0.0.1 -p 5353 epic2.test CAA`

Notes
- Binding to UDP port 53 typically requires elevated privileges; use `--port 5353` for local testing.
- SIGHUP-based hot reload supported when zones change.

License
- (C) Copyright 2025 by OPNLAB Development. This work is licensed through AGPL 3.0.
- See LICENSE.md for full license details.
