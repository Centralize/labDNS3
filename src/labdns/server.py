"""UDP server for labDNS (Epic 1)."""

from __future__ import annotations

import logging
import select
import signal
import socket
import sys
from dataclasses import dataclass
from typing import Optional

from .dns_handler import handle_query
from .resolver import Resolver


@dataclass
class ServerConfig:
    interface: str = "0.0.0.0"
    port: int = 53
    zonefile: str | None = None


class DNSServer:
    def __init__(self, config: ServerConfig, resolver: Resolver) -> None:
        self.config = config
        self.resolver = resolver
        self._stop = False

    def run(self) -> None:
        log = logging.getLogger(__name__)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.config.interface, self.config.port))
        except PermissionError:
            log.error("Permission denied binding UDP %s:%d (try sudo or a higher port)", self.config.interface, self.config.port)
            sys.exit(1)
        except OSError as exc:
            log.error("Failed to bind UDP %s:%d: %s", self.config.interface, self.config.port, exc)
            sys.exit(1)

        log.info("labDNS listening on %s:%d", self.config.interface, self.config.port)

        def _handle_signal(signum, _frame):
            log.info("Received signal %s, shutting down", signum)
            self._stop = True

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        sock.setblocking(False)
        try:
            while not self._stop:
                rlist, _, _ = select.select([sock], [], [], 0.5)
                if not rlist:
                    continue
                try:
                    data, addr = sock.recvfrom(4096)
                except BlockingIOError:
                    continue
                except OSError as exc:
                    log.debug("recvfrom error: %s", exc)
                    continue

                resp = handle_query(data, self.resolver)
                if resp is None:
                    continue
                try:
                    sock.sendto(resp, addr)
                except OSError as exc:
                    log.debug("sendto error: %s", exc)
                    continue
        finally:
            sock.close()
            log.info("Server stopped")
