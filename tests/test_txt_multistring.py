from pathlib import Path

from dnslib import DNSRecord, QTYPE

from labdns.dns_handler import handle_query
from labdns.resolver import Resolver
from labdns.zonefile import load_zones_dir


def zones_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "zones"


def test_zone_loader_preserves_txt_chunks():
    zone = load_zones_dir(zones_dir())
    rrsets = zone.get("epic2.test.", "TXT")
    assert rrsets, "TXT rrset missing"
    # Find the TXT with SPF parts
    parts_rr = None
    for ttl, data in rrsets:
        if isinstance(data, list) and "v=spf1" in data:
            parts_rr = data
            break
    assert parts_rr is not None
    assert parts_rr == ["v=spf1", "-all"]


def test_dns_handler_emits_multistring_txt():
    resolver = Resolver(load_zones_dir(zones_dir()))
    req = DNSRecord.question("epic2.test.", "TXT").pack()
    resp_bytes = handle_query(req, resolver)
    resp = DNSRecord.parse(resp_bytes)
    assert resp.header.rcode == 0
    txt_rrs = [rr for rr in resp.rr if QTYPE[rr.rtype] == "TXT"]
    assert txt_rrs, "No TXT answers found"
    # Verify both parts appear in textual form
    s = str(txt_rrs[0].rdata)
    assert "v=spf1" in s and "-all" in s

