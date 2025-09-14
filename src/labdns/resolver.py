"""Resolver integrating zone data with query handling.

Supports A, AAAA, CNAME, MX, TXT, SOA, NS, PTR.
Handles wildcard matching and CNAME chaining (basic).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .zonefile import ZoneData


@dataclass
class ResolveResult:
    rcode: int  # 0=NOERROR, 3=NXDOMAIN
    answers: List[Tuple[str, int, object]]
    cnames: List[Tuple[str, int, str]]  # (name, ttl, target)
    apex: Optional[str]
    nodata: bool = False


class Resolver:
    def __init__(self, zone: ZoneData) -> None:
        self.zone = zone

    def _exact_or_wildcard(self, qname: str, rtype: str):
        # Exact
        rr = self.zone.get(qname, rtype)
        if rr:
            return rr, False
        # Wildcard one-label
        name = qname
        parts = name.rstrip('.').split('.')
        if len(parts) > 1:
            wildcard = '*.' + '.'.join(parts[1:]) + '.'
            rr = self.zone.get(wildcard, rtype)
            if rr:
                return rr, True
        return [], False

    def resolve(self, qname: str, qtype: str) -> ResolveResult:  # noqa: ANN001 - keep simple stub
        qname = qname.lower()
        rtype = qtype.upper()
        apex = self.zone.find_apex_for(qname)

        # Helper to create result
        def res(rcode: int, answers=None, cnames=None, nodata=False) -> ResolveResult:
            return ResolveResult(rcode=rcode, answers=answers or [], cnames=cnames or [], apex=apex, nodata=nodata)

        # If QTYPE is CNAME, just return CNAME rrset
        if rtype == 'CNAME':
            rr, _ = self._exact_or_wildcard(qname, 'CNAME')
            if rr:
                return res(0, answers=[('CNAME', ttl, target) for ttl, target in rr])
            # If no CNAME but other types exist, it's NODATA
            if self.zone.has_any(qname):
                return res(0, answers=[], nodata=True)
            return res(3)  # NXDOMAIN

        # Resolve with possible CNAME chaining
        chain = []
        current = qname
        seen = set()
        for _ in range(8):
            if current in seen:
                break  # loop
            seen.add(current)

            # Check target type at current
            rr, used_wildcard = self._exact_or_wildcard(current, rtype)
            if rr:
                return res(0, answers=[(rtype, ttl, data) for ttl, data in rr], cnames=chain)

            # Try CNAME at current
            cname_rr, used_wildcard_c = self._exact_or_wildcard(current, 'CNAME')
            if cname_rr:
                # Use the first CNAME in rrset (multiple uncommon)
                ttl, target = cname_rr[0]
                chain.append((current, ttl, target))
                current = target
                continue

            # No answers and no cname
            # If the original qname exists with some other type, NODATA
            if current == qname and (self.zone.has_any(current) or used_wildcard):
                return res(0, answers=[], cnames=chain, nodata=True)
            # Else NXDOMAIN
            return res(3)

        # Chain too long or loop
        return res(0, answers=[], cnames=chain, nodata=True)
