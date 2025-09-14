"""Resolver integrating zone data with query handling for A/AAAA."""

from __future__ import annotations

from .zonefile import ZoneData


class Resolver:
    def __init__(self, zone: ZoneData) -> None:
        self.zone = zone

    def resolve(self, qname: str, qtype: str):  # noqa: ANN001 - keep simple stub
        rtype = qtype.upper()
        if rtype not in {"A", "AAAA"}:
            return []
        return self.zone.get(qname, rtype)
