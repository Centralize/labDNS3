labDNS 3.0 (work-in-progress)
==============================

Quick start
- Install in editable mode: `pip install -e .`
- Prepare a zonefile, e.g. `examples/example.zone`
- Validate: `labdns check examples/example.zone`
- Start (unprivileged port): `labdns start --zonefile examples/example.zone --port 5353 --interface 127.0.0.1`
- Test with dig: `dig @127.0.0.1 -p 5353 www.example.test A`

Notes
- Binding to UDP port 53 typically requires elevated privileges.
- Current implementation handles A/AAAA from the provided zonefile.
