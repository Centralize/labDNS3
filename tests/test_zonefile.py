from pathlib import Path

from labdns.zonefile import load_zonefile


def example_zone_path() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "example.zone"


def test_loads_a_and_aaaa_records():
    zone = load_zonefile(example_zone_path())
    assert "192.0.2.10" in zone.get("www.example.test.", "A")
    assert "2001:db8::10" in zone.get("api.example.test.", "AAAA")

