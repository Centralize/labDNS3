from pathlib import Path

from dnslib import DNSRecord, QTYPE

from labdns.dns_handler import handle_query
from labdns.resolver import Resolver
from labdns.zonefile import load_zonefile


def example_zone_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "example.zone"


def make_query(name: str, qtype: str) -> bytes:
    return DNSRecord.question(name, qtype).pack()


def test_a_query_returns_answer():
    zone = load_zonefile(example_zone_path())
    resolver = Resolver(zone)
    req = make_query("www.example.test.", "A")
    resp_bytes = handle_query(req, resolver)
    assert resp_bytes is not None
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 0
    assert len(resp.rr) == 1
    rr = resp.rr[0]
    assert QTYPE[rr.rtype] == "A"
    assert str(rr.rdata) == "192.0.2.10"


def test_aaaa_query_returns_answer():
    zone = load_zonefile(example_zone_path())
    resolver = Resolver(zone)
    req = make_query("api.example.test.", "AAAA")
    resp_bytes = handle_query(req, resolver)
    assert resp_bytes is not None
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 0
    assert len(resp.rr) == 1
    rr = resp.rr[0]
    assert QTYPE[rr.rtype] == "AAAA"
    assert str(rr.rdata) == "2001:db8::10"


def test_nxdomain_on_missing_name():
    zone = load_zonefile(example_zone_path())
    resolver = Resolver(zone)
    req = make_query("nope.example.test.", "A")
    resp_bytes = handle_query(req, resolver)
    assert resp_bytes is not None
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 3  # NXDOMAIN
    assert len(resp.rr) == 0

