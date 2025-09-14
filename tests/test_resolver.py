from pathlib import Path

from labdns.resolver import Resolver
from labdns.zonefile import load_zonefile


def example_zone_path() -> Path:
    return Path(__file__).resolve().parents[1] / "zones" / "example.zone"


def test_resolver_returns_records():
    zone = load_zonefile(example_zone_path())
    r = Resolver(zone)
    assert r.resolve("www.example.test.", "A") == ["192.0.2.10"]
    assert r.resolve("api.example.test.", "AAAA") == ["2001:db8::10"]


def test_resolver_unknown_type_returns_empty():
    zone = load_zonefile(example_zone_path())
    r = Resolver(zone)
    assert r.resolve("www.example.test.", "TXT") == []
