"""UDP server for labDNS (Epic 1)."""

from __future__ import annotations

import logging
import select
import signal
import socket
import sys
from dataclasses import dataclass
from typing import Callable, Optional

from .dns_handler import handle_query
from .resolver import Resolver


@dataclass
class ServerConfig:
    interface: str = "0.0.0.0"
    port: int = 53
    zonefile: str | None = None
    pid_file: str | None = None


class DNSServer:
    def __init__(self, config: ServerConfig, resolver: Resolver) -> None:
        self.config = config
        self.resolver = resolver
        self._stop = False
        self._reload_cb: Optional[Callable[[], Resolver]] = None

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
        
        def _handle_hup(signum, _frame):
            if self._reload_cb is None:
                log.info("SIGHUP received but reload is not configured")
                return
            log.info("Received SIGHUP, attempting zone reload")
            try:
                new_resolver = self._reload_cb()
            except Exception as exc:  # noqa: BLE001
                log.error("Zone reload failed: %s", exc)
                return
            self.resolver = new_resolver
            log.info("Zone reload successful")

        signal.signal(signal.SIGHUP, _handle_hup)

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
            # Cleanup PID file if we created one
            if self.config.pid_file:
                try:
                    import os

                    if os.path.exists(self.config.pid_file):
                        # Only remove if it points to us
                        try:
                            content = open(self.config.pid_file, "r", encoding="utf-8").read().strip()
                            if content and int(content) == os.getpid():
                                os.remove(self.config.pid_file)
                        except Exception:
                            # Best-effort cleanup
                            os.remove(self.config.pid_file)
                except Exception:
                    pass

    def set_reload_callback(self, cb: Callable[[], Resolver]) -> None:
        self._reload_cb = cb
