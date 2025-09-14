"""DNS packet parsing and response generation for A/AAAA."""

from __future__ import annotations

import logging
from typing import Optional

from dnslib import A, AAAA, CNAME, DNSHeader, DNSLabel, DNSRecord, MX, NS, PTR, QTYPE, RR, SOA, TXT

from .resolver import ResolveResult, Resolver

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

    # Handle only the first question
    qname = str(request.q.qname).lower()
    qtype = QTYPE[request.q.qtype]

    result: ResolveResult = resolver.resolve(qname, qtype)

    def add_answer(name: str, rtype: str, rttl: int, data: object) -> None:
        if rtype == 'A':
            reply.add_answer(RR(name, QTYPE.A, rdata=A(str(data)), ttl=rttl))
        elif rtype == 'AAAA':
            reply.add_answer(RR(name, QTYPE.AAAA, rdata=AAAA(str(data)), ttl=rttl))
        elif rtype == 'CNAME':
            reply.add_answer(RR(name, QTYPE.CNAME, rdata=CNAME(DNSLabel(str(data))), ttl=rttl))
        elif rtype == 'NS':
            reply.add_answer(RR(name, QTYPE.NS, rdata=NS(DNSLabel(str(data))), ttl=rttl))
        elif rtype == 'MX':
            pref = int(data['preference'])
            exch = DNSLabel(str(data['exchange']))
            reply.add_answer(RR(name, QTYPE.MX, rdata=MX(pref, exch), ttl=rttl))
        elif rtype == 'TXT':
            # Support multi-string TXT (list/tuple of strings)
            try:
                if isinstance(data, (list, tuple)):
                    rdata = TXT(*[str(x) for x in data])
                else:
                    rdata = TXT(str(data))
            except TypeError:
                # Fallback for dnslib variants expecting list
                if isinstance(data, (list, tuple)):
                    rdata = TXT([str(x) for x in data])
                else:
                    rdata = TXT(str(data))
            reply.add_answer(RR(name, QTYPE.TXT, rdata=rdata, ttl=rttl))
        elif rtype == 'PTR':
            reply.add_answer(RR(name, QTYPE.PTR, rdata=PTR(DNSLabel(str(data))), ttl=rttl))
        elif rtype == 'SOA':
            soa = data
            mname = DNSLabel(soa['mname'])
            rname = DNSLabel(soa['rname'])
            times = (soa['serial'], soa['refresh'], soa['retry'], soa['expire'], soa['minimum'])
            reply.add_answer(RR(name, QTYPE.SOA, rdata=SOA(mname, rname, times), ttl=rttl))

    # Add CNAME chain answers first
    for name, cttl, target in result.cnames:
        add_answer(name, 'CNAME', cttl, target)

    # Add final answers
    for rtype, rttl, data in result.answers:
        add_answer(qname, rtype, rttl, data)

    # Authority section
    if result.rcode == 3:
        reply.header.rcode = 3
        # NXDOMAIN should include SOA of the closest zone
        if result.apex and hasattr(resolver.zone, 'soas') and result.apex in resolver.zone.soas:
            soa_ttl, soa_data = resolver.zone.soas[result.apex]
            mname = DNSLabel(soa_data['mname'])
            rname = DNSLabel(soa_data['rname'])
            times = (soa_data['serial'], soa_data['refresh'], soa_data['retry'], soa_data['expire'], soa_data['minimum'])
            reply.add_auth(RR(result.apex, QTYPE.SOA, rdata=SOA(mname, rname, times), ttl=soa_ttl))
    else:
        # Positive or NODATA: include NS rrset for apex if present
        if result.apex and hasattr(resolver.zone, 'nss') and result.apex in resolver.zone.nss:
            for ns_ttl, ns_name in resolver.zone.nss[result.apex]:
                reply.add_auth(RR(result.apex, QTYPE.NS, rdata=NS(DNSLabel(ns_name)), ttl=ns_ttl))
        # NODATA: include SOA as well
        if result.nodata and result.apex and result.apex in resolver.zone.soas:
            soa_ttl, soa_data = resolver.zone.soas[result.apex]
            mname = DNSLabel(soa_data['mname'])
            rname = DNSLabel(soa_data['rname'])
            times = (soa_data['serial'], soa_data['refresh'], soa_data['retry'], soa_data['expire'], soa_data['minimum'])
            reply.add_auth(RR(result.apex, QTYPE.SOA, rdata=SOA(mname, rname, times), ttl=soa_ttl))

    return reply.pack()
