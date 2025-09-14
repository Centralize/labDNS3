from pathlib import Path

from dnslib import DNSRecord, QTYPE

from labdns.dns_handler import handle_query
from labdns.resolver import Resolver
from labdns.zonefile import load_zones_dir


def zones_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "zones"


def make_query(name: str, qtype: str) -> bytes:
    return DNSRecord.question(name, qtype).pack()


def setup_resolver() -> Resolver:
    return Resolver(load_zones_dir(zones_dir()))


def test_cname_chain_returns_cname_and_a():
    resolver = setup_resolver()
    req = make_query("www.epic2.test.", "A")
    resp_bytes = handle_query(req, resolver)
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 0
    # Expect two CNAMEs + one A
    cnames = [rr for rr in resp.rr if QTYPE[rr.rtype] == "CNAME"]
    answers_a = [rr for rr in resp.rr if QTYPE[rr.rtype] == "A"]
    assert len(cnames) == 2
    assert len(answers_a) == 1
    assert str(answers_a[0].rdata) == "192.0.2.61"


def test_wildcard_match():
    resolver = setup_resolver()
    req = make_query("foo.wild.epic2.test.", "A")
    resp_bytes = handle_query(req, resolver)
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 0
    answers_a = [rr for rr in resp.rr if QTYPE[rr.rtype] == "A"]
    assert len(answers_a) == 1
    assert str(answers_a[0].rdata) == "192.0.2.99"


def test_nodata_includes_soa_in_authority():
    resolver = setup_resolver()
    req = make_query("mail.epic2.test.", "AAAA")
    resp_bytes = handle_query(req, resolver)
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 0  # NOERROR
    assert len(resp.rr) == 0  # No answers
    auth_soa = [rr for rr in resp.auth if QTYPE[rr.rtype] == "SOA"]
    assert len(auth_soa) == 1


def test_nxdomain_includes_soa_in_authority():
    resolver = setup_resolver()
    req = make_query("nope.epic2.test.", "A")
    resp_bytes = handle_query(req, resolver)
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 3  # NXDOMAIN
    auth_soa = [rr for rr in resp.auth if QTYPE[rr.rtype] == "SOA"]
    assert len(auth_soa) == 1
