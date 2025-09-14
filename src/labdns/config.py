from __future__ import annotations

# (C) Copyright 2025 by OPNLAB Development.
# This work is licensed through AGPL 3.0.
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import configparser


@dataclass
class AppConfig:
    zonefile: Optional[Path] = None
    zones_dir: Optional[Path] = None
    port: Optional[int] = None
    interface: Optional[str] = None
    daemon: Optional[bool] = None
    write_pid: Optional[bool] = None
    pid_file: Optional[Path] = None
    log_file: Optional[Path] = None
    log_level: Optional[str] = None
    verbose: Optional[bool] = None


def _parse_bool(val: str | None) -> Optional[bool]:
    if val is None:
        return None
    v = val.strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off"}:
        return False
    return None


def _read_ini(path: Path) -> AppConfig:
    cfg = configparser.ConfigParser()
    cfg.read(path)
    section = cfg["labdns"] if cfg.has_section("labdns") else cfg[configparser.DEFAULTSECT]

    def p(k: str) -> Optional[str]:
        return section.get(k)

    ac = AppConfig()
    if p("zonefile"):
        ac.zonefile = Path(p("zonefile")).expanduser()
    if p("zones_dir"):
        ac.zones_dir = Path(p("zones_dir")).expanduser()
    if p("port"):
        try:
            ac.port = int(p("port"))
        except Exception:
            pass
    ac.interface = p("interface") or None
    b = _parse_bool(p("daemon"))
    if b is not None:
        ac.daemon = b
    b = _parse_bool(p("write_pid"))
    if b is not None:
        ac.write_pid = b
    if p("pid_file"):
        ac.pid_file = Path(p("pid_file")).expanduser()
    if p("log_file"):
        ac.log_file = Path(p("log_file")).expanduser()
    if p("log_level"):
        ac.log_level = p("log_level")
    b = _parse_bool(p("verbose"))
    if b is not None:
        ac.verbose = b
    return ac


def _read_env() -> AppConfig:
    g = os.getenv
    ac = AppConfig()
    if g("LABDNS_ZONEFILE"):
        ac.zonefile = Path(g("LABDNS_ZONEFILE")).expanduser()
    if g("LABDNS_ZONES_DIR"):
        ac.zones_dir = Path(g("LABDNS_ZONES_DIR")).expanduser()
    if g("LABDNS_PORT"):
        try:
            ac.port = int(g("LABDNS_PORT"))
        except Exception:
            pass
    if g("LABDNS_INTERFACE"):
        ac.interface = g("LABDNS_INTERFACE")
    b = _parse_bool(g("LABDNS_DAEMON"))
    if b is not None:
        ac.daemon = b
    b = _parse_bool(g("LABDNS_WRITE_PID"))
    if b is not None:
        ac.write_pid = b
    if g("LABDNS_PID_FILE"):
        ac.pid_file = Path(g("LABDNS_PID_FILE")).expanduser()
    if g("LABDNS_LOG_FILE"):
        ac.log_file = Path(g("LABDNS_LOG_FILE")).expanduser()
    if g("LABDNS_LOG_LEVEL"):
        ac.log_level = g("LABDNS_LOG_LEVEL")
    b = _parse_bool(g("LABDNS_VERBOSE"))
    if b is not None:
        ac.verbose = b
    return ac


def load_config(explicit_path: Path | None = None) -> AppConfig:
    # order: explicit file -> ~/.config/labdns/labdns.ini -> ./labdns.ini -> /etc/labdns/labdns.ini
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(explicit_path)
    else:
        home = Path.home()
        candidates.extend(
            [
                home / ".config" / "labdns" / "labdns.ini",
                Path.cwd() / "labdns.ini",
                Path("/etc/labdns/labdns.ini"),
            ]
        )

    file_cfg = AppConfig()
    for p in candidates:
        if p.exists() and p.is_file():
            file_cfg = _read_ini(p)
            break

    env_cfg = _read_env()

    # Merge: env overrides file
    def pick(a: Optional[object], b: Optional[object]):
        return b if b is not None else a

    merged = AppConfig(
        zonefile=pick(file_cfg.zonefile, env_cfg.zonefile),
        zones_dir=pick(file_cfg.zones_dir, env_cfg.zones_dir),
        port=pick(file_cfg.port, env_cfg.port),
        interface=pick(file_cfg.interface, env_cfg.interface),
        daemon=pick(file_cfg.daemon, env_cfg.daemon),
        write_pid=pick(file_cfg.write_pid, env_cfg.write_pid),
        pid_file=pick(file_cfg.pid_file, env_cfg.pid_file),
        log_file=pick(file_cfg.log_file, env_cfg.log_file),
        log_level=pick(file_cfg.log_level, env_cfg.log_level),
        verbose=pick(file_cfg.verbose, env_cfg.verbose),
    )
    return merged


def to_dict(cfg: AppConfig) -> dict:
    return {
        "zonefile": str(cfg.zonefile) if cfg.zonefile else None,
        "zones_dir": str(cfg.zones_dir) if cfg.zones_dir else None,
        "port": cfg.port,
        "interface": cfg.interface,
        "daemon": cfg.daemon,
        "write_pid": cfg.write_pid,
        "pid_file": str(cfg.pid_file) if cfg.pid_file else None,
        "log_file": str(cfg.log_file) if cfg.log_file else None,
        "log_level": cfg.log_level,
        "verbose": cfg.verbose,
    }


TEMPLATE = """[labdns]
# Single zone file (path) or zones_dir (directory of multiple zone files)
# zonefile = ./examples/example.zone
# zones_dir = ./zones

# Network
# interface = 0.0.0.0
# port = 53

# Daemon and PID
# daemon = false
# write_pid = true
# pid_file = ./labdns.pid

# Logging
# log_file = ./labdns.log
# log_level = INFO
# verbose = false
"""


def write_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE, encoding="utf-8")
