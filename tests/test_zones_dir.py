from pathlib import Path

from labdns.zonefile import load_zones_dir


def zones_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "zones"


def test_loads_multiple_zonefiles():
    zone = load_zones_dir(zones_dir())
    assert "192.0.2.10" in zone.get("www.example.test.", "A")
    assert "2001:db8::20" in zone.get("api.second.test.", "AAAA")

