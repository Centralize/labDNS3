# (C) Copyright 2025 by OPNLAB Development.
# This work is licensed through AGPL 3.0.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Minimal zonefile loader for A/AAAA records using dnspython.

This covers Epic 1 needs; Epic 2 will expand support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import dns.zone
import dns.rdatatype


def _normalize_name(name: str) -> str:
    n = name.lower()
    if not n.endswith("."):
        n += "."
    return n


@dataclass
class ZoneData:
    records: Dict[str, Dict[str, List[Tuple[int, object]]]] = field(default_factory=dict)
    default_ttl: int = 300
    # Map apex (zone origin) -> SOA data and NS rrsets
    soas: Dict[str, Tuple[int, dict]] = field(default_factory=dict)  # name -> (ttl, data)
    nss: Dict[str, List[Tuple[int, str]]] = field(default_factory=dict)  # name -> [(ttl, nsname)]

    def add_record(self, name: str, rtype: str, value: object, ttl: Optional[int] = None) -> None:
        name_n = _normalize_name(name)
        rtype_u = rtype.upper()
        ttl_v = int(ttl) if ttl is not None else self.default_ttl
        self.records.setdefault(name_n, {}).setdefault(rtype_u, []).append((ttl_v, value))

    def get(self, name: str, rtype: str) -> List[Tuple[int, object]]:
        name_n = _normalize_name(name)
        rtype_u = rtype.upper()
        return self.records.get(name_n, {}).get(rtype_u, [])

    def has_any(self, name: str) -> bool:
        name_n = _normalize_name(name)
        return name_n in self.records and bool(self.records[name_n])

    def find_apex_for(self, qname: str) -> Optional[str]:
        # Walk labels upwards to find nearest SOA
        name = _normalize_name(qname).rstrip('.')
        labels = name.split('.')
        for i in range(len(labels)):
            candidate = '.'.join(labels[i:]) + '.'
            if candidate in self.soas:
                return candidate
        return None


def load_zonefile(path: Path) -> ZoneData:
    zone = ZoneData()
    z = dns.zone.from_file(str(path), relativize=False, allow_include=True)
    origin = str(z.origin)
    for (name, node) in z.nodes.items():
        fqdn = str(name)
        if not fqdn.endswith('.'):
            fqdn = f"{fqdn}.{origin}"
        for rdataset in node.rdatasets:
            rtype = dns.rdatatype.to_text(rdataset.rdtype)
            ttl = getattr(rdataset, 'ttl', None)
            for rdata in rdataset:
                if rdataset.rdtype == dns.rdatatype.A:
                    zone.add_record(fqdn, 'A', rdata.address, ttl)
                elif rdataset.rdtype == dns.rdatatype.AAAA:
                    zone.add_record(fqdn, 'AAAA', rdata.address, ttl)
                elif rdataset.rdtype == dns.rdatatype.CNAME:
                    zone.add_record(fqdn, 'CNAME', str(rdata.target), ttl)
                elif rdataset.rdtype == dns.rdatatype.NS:
                    zone.add_record(fqdn, 'NS', str(rdata.target), ttl)
                elif rdataset.rdtype == dns.rdatatype.MX:
                    zone.add_record(fqdn, 'MX', {'preference': int(rdata.preference), 'exchange': str(rdata.exchange)}, ttl)
                elif rdataset.rdtype == dns.rdatatype.TXT:
                    try:
                        parts = [s.decode('utf-8', errors='replace') for s in rdata.strings]  # type: ignore[attr-defined]
                        if not parts:
                            parts = [str(rdata).strip('"')]
                    except Exception:
                        parts = [str(rdata).strip('"')]
                    zone.add_record(fqdn, 'TXT', parts, ttl)
                elif rdataset.rdtype == dns.rdatatype.PTR:
                    zone.add_record(fqdn, 'PTR', str(rdata.target), ttl)
                elif rdataset.rdtype == dns.rdatatype.SOA:
                    soa = {
                        'mname': str(rdata.mname),
                        'rname': str(rdata.rname),
                        'serial': int(rdata.serial),
                        'refresh': int(rdata.refresh),
                        'retry': int(rdata.retry),
                        'expire': int(rdata.expire),
                        'minimum': int(rdata.minimum),
                    }
                    zone.soas[_normalize_name(fqdn)] = (int(ttl) if ttl is not None else zone.default_ttl, soa)
                elif rdataset.rdtype == dns.rdatatype.SRV:
                    zone.add_record(
                        fqdn,
                        'SRV',
                        {
                            'priority': int(rdata.priority),
                            'weight': int(rdata.weight),
                            'port': int(rdata.port),
                            'target': str(rdata.target),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.CAA:
                    zone.add_record(
                        fqdn,
                        'CAA',
                        {
                            'flags': int(rdata.flags),
                            'tag': str(rdata.tag),
                            'value': str(rdata.value),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.DNSKEY:
                    zone.add_record(
                        fqdn,
                        'DNSKEY',
                        {
                            'flags': int(rdata.flags),
                            'protocol': int(rdata.protocol),
                            'algorithm': int(rdata.algorithm),
                            'key': str(rdata.key),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.DS:
                    zone.add_record(
                        fqdn,
                        'DS',
                        {
                            'key_tag': int(rdata.key_tag),
                            'algorithm': int(rdata.algorithm),
                            'digest_type': int(rdata.digest_type),
                            'digest': rdata.digest.hex() if hasattr(rdata.digest, 'hex') else str(rdata.digest),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.RP:
                    zone.add_record(
                        fqdn,
                        'RP',
                        {
                            'mbox': str(rdata.mbox),
                            'txt': str(rdata.txt),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.NAPTR:
                    zone.add_record(
                        fqdn,
                        'NAPTR',
                        {
                            'order': int(rdata.order),
                            'preference': int(rdata.preference),
                            'flags': str(rdata.flags),
                            'service': str(rdata.service),
                            'regexp': str(rdata.regexp),
                            'replacement': str(rdata.replacement),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.RRSIG:
                    zone.add_record(
                        fqdn,
                        'RRSIG',
                        {
                            'type_covered': str(rdata.type_covered),
                            'algorithm': int(rdata.algorithm),
                            'labels': int(rdata.labels),
                            'original_ttl': int(rdata.original_ttl),
                            'expiration': int(rdata.expiration),
                            'inception': int(rdata.inception),
                            'key_tag': int(rdata.key_tag),
                            'signer': str(rdata.signer),
                            'signature': getattr(rdata, 'signature', b''),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.CERT:
                    zone.add_record(
                        fqdn,
                        'CERT',
                        {
                            'cert_type': int(rdata.certificate_type),
                            'key_tag': int(rdata.key_tag),
                            'algorithm': int(rdata.algorithm),
                            'certificate': getattr(rdata, 'certificate', b''),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == dns.rdatatype.DNAME:
                    zone.add_record(
                        fqdn,
                        'DNAME',
                        {
                            'target': str(rdata.target),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif getattr(dns.rdatatype, 'SSHFP', None) and rdataset.rdtype == dns.rdatatype.SSHFP:
                    zone.add_record(
                        fqdn,
                        'SSHFP',
                        {
                            'algorithm': int(getattr(rdata, 'algorithm', 0)),
                            'fp_type': int(getattr(rdata, 'fp_type', getattr(rdata, 'fingerprint_type', 0))),
                            'fingerprint': str(getattr(rdata, 'fingerprint', '')),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif getattr(dns.rdatatype, 'IPSECKEY', None) and rdataset.rdtype == dns.rdatatype.IPSECKEY:
                    zone.add_record(
                        fqdn,
                        'IPSECKEY',
                        {
                            'precedence': int(rdata.precedence),
                            'gateway_type': int(rdata.gateway_type),
                            'algorithm': int(rdata.algorithm),
                            'gateway': str(getattr(rdata, 'gateway', '')),
                            'public_key': str(getattr(rdata, 'public_key', '')),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif getattr(dns.rdatatype, 'OPENPGPKEY', None) and rdataset.rdtype == dns.rdatatype.OPENPGPKEY:
                    zone.add_record(
                        fqdn,
                        'OPENPGPKEY',
                        {
                            'public_key': str(getattr(rdata, 'public_key', '')),
                            'raw': rdata.to_text(),
                        },
                        ttl,
                    )
                elif rdataset.rdtype == getattr(dns.rdatatype, 'SPF', 99):
                    # Store SPF like TXT and also map to TXT for compatibility
                    try:
                        parts = [s.decode('utf-8', errors='replace') for s in rdata.strings]  # type: ignore[attr-defined]
                        if not parts:
                            parts = [str(rdata).strip('"')]
                    except Exception:
                        parts = [str(rdata).strip('"')]
                    zone.add_record(fqdn, 'SPF', parts, ttl)
                    zone.add_record(fqdn, 'TXT', parts, ttl)
                else:
                    # Ignore other types for now
                    pass

    # Collect NS for apexes
    for apex in list(zone.soas.keys()):
        ns_rrs = zone.get(apex, 'NS')
        if ns_rrs:
            zone.nss[apex] = ns_rrs
    return zone


def merge_zones(zones: Iterable[ZoneData]) -> ZoneData:
    merged = ZoneData()
    for z in zones:
        for name, rmap in z.records.items():
            for rtype, values in rmap.items():
                for v in values:
                    merged.add_record(name, rtype, v)
    return merged


def load_zones_dir(dir_path: Path) -> ZoneData:
    if not dir_path.exists() or not dir_path.is_dir():
        raise FileNotFoundError(f"Zones directory not found: {dir_path}")
    zonefiles = sorted(p for p in dir_path.iterdir() if p.is_file())
    if not zonefiles:
        raise FileNotFoundError(f"No zonefiles in directory: {dir_path}")
    zones = []
    for zf in zonefiles:
        zones.append(load_zonefile(zf))
    return merge_zones(zones)
