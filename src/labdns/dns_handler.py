"""DNS packet parsing and response generation for A/AAAA."""

from __future__ import annotations

import logging
from typing import Optional

from dnslib import A, AAAA, DNSHeader, DNSLabel, DNSRecord, QTYPE, RR

from .resolver import Resolver

log = logging.getLogger(__name__)


def handle_query(packet_bytes: bytes, resolver: Resolver, ttl: int = 300) -> Optional[bytes]:
    """Parse an incoming DNS packet and return a response packet.

    Returns None if the request is malformed and should be dropped.
    """
    try:
        request = DNSRecord.parse(packet_bytes)
    except Exception as exc:  # noqa: BLE001 - broad for malformed packets
        log.debug("Failed to parse DNS packet: %s", exc)
        return None

    reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=0), q=request.q)

    # Handle only the first question per RFC simplification here
    qname = str(request.q.qname).lower()
    qtype = QTYPE[request.q.qtype]

    answers = resolver.resolve(qname, qtype)
    if answers:
        for addr in answers:
            if qtype == "A":
                reply.add_answer(RR(qname, QTYPE.A, rdata=A(addr), ttl=ttl))
            elif qtype == "AAAA":
                reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(addr), ttl=ttl))
    else:
        # Name exists for other types? For Epic 1, treat as NXDOMAIN on miss
        reply.header.rcode = 3  # NXDOMAIN

    return reply.pack()
