"""Minimal zonefile loader for A/AAAA records using dnspython.

This covers Epic 1 needs; Epic 2 will expand support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import dns.zone
import dns.rdatatype


def _normalize_name(name: str) -> str:
    n = name.lower()
    if not n.endswith("."):
        n += "."
    return n


@dataclass
class ZoneData:
    records: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    default_ttl: int = 300

    def add_record(self, name: str, rtype: str, value: str) -> None:
        name_n = _normalize_name(name)
        rtype_u = rtype.upper()
        self.records.setdefault(name_n, {}).setdefault(rtype_u, []).append(value)

    def get(self, name: str, rtype: str) -> List[str]:
        name_n = _normalize_name(name)
        rtype_u = rtype.upper()
        return self.records.get(name_n, {}).get(rtype_u, [])


def load_zonefile(path: Path) -> ZoneData:
    zone = ZoneData()
    z = dns.zone.from_file(str(path), relativize=False, allow_include=True)
    origin = str(z.origin)
    for (name, node) in z.nodes.items():
        fqdn = str(name)
        if not fqdn.endswith("."):
            fqdn = f"{fqdn}.{origin}"
        for rdataset in node.rdatasets:
            if rdataset.rdtype in (dns.rdatatype.A, dns.rdatatype.AAAA):
                rtype = dns.rdatatype.to_text(rdataset.rdtype)
                for rdata in rdataset:
                    # A/AAAA expose .address attribute
                    zone.add_record(fqdn, rtype, rdata.address)
    return zone
