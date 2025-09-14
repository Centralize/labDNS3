# (C) Copyright 2025 by OPNLAB Development.
# This work is licensed through AGPL 3.0.
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import sys
from pathlib import Path

import click

from . import __version__
from .resolver import Resolver
from .server import DNSServer, ServerConfig
from .zonefile import load_zonefile
from .config import AppConfig, load_config, to_dict, write_template


def _configure_logging(verbose: bool, log_level: str | None = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    if log_level:
        try:
            level = getattr(logging, log_level.upper())
        except AttributeError:
            level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _enable_file_logging(path: Path) -> None:
    """Attach a file handler to the root logger using existing level/format."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    logger = logging.getLogger()
    # Reuse formatter like basicConfig
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setLevel(logger.level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


@click.group(help="labDNS – lightweight DNS server")
@click.version_option(__version__, prog_name="labdns")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False), help="Override log level")
@click.option("--config", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Path to labdns.ini")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, log_level: str | None, config: Path | None) -> None:
    _configure_logging(verbose, log_level)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command(help="Validate a BIND-style zonefile or all files in a directory")
@click.argument("path", required=False, type=click.Path(exists=True, dir_okay=True, path_type=Path))
@click.pass_context
def check(ctx: click.Context, path: Path | None) -> None:
    try:
        if path is None:
            from .config import load_config

            appcfg = load_config(ctx.obj.get("config_path"))
            if appcfg.zones_dir:
                from .zonefile import load_zones_dir

                load_zones_dir(appcfg.zones_dir)
                path = appcfg.zones_dir
            elif appcfg.zonefile:
                load_zonefile(appcfg.zonefile)
                path = appcfg.zonefile
            else:
                logging.error("No path provided and no zonefile/zones_dir in config")
                sys.exit(2)
        else:
            if path.is_dir():
                from .zonefile import load_zones_dir  # local import to avoid cycles

                load_zones_dir(path)
            else:
                load_zonefile(path)
    except Exception as exc:  # noqa: BLE001
        logging.error("Validation failed for %s: %s", path, exc)
        sys.exit(2)
    click.echo(f"OK: {path}")


@cli.command(help="Start DNS server")
@click.option("--zonefile", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Single zonefile to load")
@click.option("--zones-dir", type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path), help="Directory containing multiple zonefiles")
@click.option("--port", type=int)
@click.option("--interface")
@click.option("--daemon/--no-daemon", default=False, show_default=True, help="Run in background")
@click.option("--write-pid/--no-write-pid", default=True, show_default=True, help="Write PID file for reload/management")
@click.option(
    "--pid-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="PID file path",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Log file path (defaults to ./labdns.log in daemon mode)",
)
@click.pass_context
def start(ctx: click.Context, zonefile: Path | None, zones_dir: Path | None, port: int | None, interface: str | None, daemon: bool, write_pid: bool, pid_file: Path | None, log_file: Path | None) -> None:
    zone = None
    try:
        # Load config values if not explicitly provided
        if zones_dir is None and zonefile is None:
            from .config import load_config

            appcfg = load_config(ctx.obj.get("config_path"))
            zonefile = zonefile or appcfg.zonefile
            zones_dir = zones_dir or appcfg.zones_dir
            port = port if port is not None else appcfg.port
            interface = interface or appcfg.interface
            if pid_file is None:
                pid_file = appcfg.pid_file
            if log_file is None:
                log_file = appcfg.log_file

        if zones_dir is not None:
            from .zonefile import load_zones_dir  # local import to avoid cycles

            zone = load_zones_dir(zones_dir)
        elif zonefile is not None:
            zone = load_zonefile(zonefile)
        else:
            # Default to ./zones if present
            default_dir = Path("zones")
            if default_dir.exists() and default_dir.is_dir():
                from .zonefile import load_zones_dir

                zones_dir = default_dir
                zone = load_zones_dir(zones_dir)
            else:
                logging.error("Provide --zonefile or --zones-dir (or create ./zones)")
                sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to load zones: %s", exc)
        sys.exit(2)
    resolver = Resolver(zone)

    # Optionally become a daemon
    chosen_log = log_file
    if daemon:
        # Inform user how to find PID
        if write_pid:
            click.echo(f"Daemonizing. PID will be written to {pid_file}.")
        else:
            click.echo("Daemonizing.")
        # Default log file for daemon mode if not provided
        if chosen_log is None:
            chosen_log = Path("labdns.log")
        if chosen_log is not None:
            click.echo(f"Logging to {chosen_log}.")
        _daemonize()

    # After potential daemonization, write PID file if requested
    if write_pid:
        try:
            _write_pid_file(pid_file or Path("labdns.pid"))
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to write PID file %s: %s", pid_file, exc)
            sys.exit(1)

    # Configure file logging if requested or implied by daemon mode
    if chosen_log is not None:
        try:
            _enable_file_logging(chosen_log)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to configure file logging at %s: %s", chosen_log, exc)

    # Fill defaults if still None
    if port is None:
        port = 53
    if interface is None:
        interface = "0.0.0.0"

    config = ServerConfig(interface=interface, port=port, zonefile=str(zonefile) if zonefile else (str(zones_dir) if zones_dir else None), pid_file=str(pid_file) if write_pid else None)
    server = DNSServer(config, resolver)

    # Configure reload callback
    if zones_dir is not None:
        def _reload():
            from .zonefile import load_zones_dir
            new_zone = load_zones_dir(zones_dir)
            return Resolver(new_zone)
        server.set_reload_callback(_reload)
    elif zonefile is not None:
        def _reload():
            new_zone = load_zonefile(zonefile)
            return Resolver(new_zone)
        server.set_reload_callback(_reload)
    else:
        default_dir = Path("zones")
        if default_dir.exists() and default_dir.is_dir():
            def _reload():
                from .zonefile import load_zones_dir
                new_zone = load_zones_dir(default_dir)
                return Resolver(new_zone)
            server.set_reload_callback(_reload)

    server.run()


@cli.command(help="Show version")
def version() -> None:
    click.echo(__version__)


def main() -> None:
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()


def _daemonize() -> None:
    """Unix double-fork to run in background."""
    try:
        pid = os.fork()
        if pid > 0:
            # First parent exits
            os._exit(0)
    except OSError as e:
        logging.error("First fork failed: %s", e)
        sys.exit(1)

    # Decouple from parent environment
    os.setsid()
    os.umask(0)

    try:
        pid = os.fork()
        if pid > 0:
            # Second parent exits
            os._exit(0)
    except OSError as e:
        logging.error("Second fork failed: %s", e)
        sys.exit(1)

    # Redirect standard file descriptors to /dev/null
    sys.stdout.flush()
    sys.stderr.flush()
    with open("/dev/null", "rb", 0) as f_in:
        os.dup2(f_in.fileno(), sys.stdin.fileno())
    with open("/dev/null", "ab", 0) as f_out:
        os.dup2(f_out.fileno(), sys.stdout.fileno())
        os.dup2(f_out.fileno(), sys.stderr.fileno())


def _write_pid_file(path: Path) -> None:
    """Atomically write current PID to path.

    If an existing PID file points to a live process, abort.
    """
    pid = os.getpid()
    if path.exists():
        try:
            old = int(path.read_text().strip())
            if old > 0:
                try:
                    os.kill(old, 0)
                except ProcessLookupError:
                    # Stale PID; continue and overwrite
                    pass
                else:
                    raise RuntimeError(f"PID file {path} already exists and process {old} is running")
        except ValueError:
            # Corrupt PID file; overwrite
            pass
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(str(pid) + "\n", encoding="utf-8")
    os.replace(tmp, path)


@cli.command(help="Send SIGHUP to a running labdns server to reload zones")
@click.option("--pid", type=int, help="PID of the running server process")
@click.option(
    "--pid-file",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to PID file containing the server PID",
)
def reload(pid: int | None, pid_file: Path | None) -> None:  # type: ignore[func-returns-value]
    import os
    import signal as _signal

    if pid is None and pid_file is None:
        # Attempt default PID file in CWD
        default_pid = Path("labdns.pid")
        if default_pid.exists():
            pid_file = default_pid
        else:
            logging.error("Provide --pid or --pid-file (no default PID file found)")
            sys.exit(2)

    if pid is None and pid_file is not None:
        try:
            text = pid_file.read_text().strip()
            pid = int(text)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to read PID from %s: %s", pid_file, exc)
            sys.exit(2)

    assert pid is not None
    try:
        os.kill(pid, _signal.SIGHUP)
    except ProcessLookupError:
        logging.error("No process with PID %d", pid)
        sys.exit(1)
    except PermissionError:
        logging.error("Permission denied sending signal to PID %d", pid)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to send SIGHUP to PID %d: %s", pid, exc)
        sys.exit(1)
    click.echo(f"Sent SIGHUP to PID {pid}")


@cli.group(help="Configuration management")
@click.pass_context
def config(ctx: click.Context) -> None:  # noqa: D401 - simple group
    pass


@config.command(name="show", help="Show effective configuration (file + environment)")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    cfg = load_config(ctx.obj.get("config_path"))
    for k, v in to_dict(cfg).items():
        click.echo(f"{k}: {v}")


@config.command(name="init", help="Write a template labdns.ini")
@click.option("--path", type=click.Path(dir_okay=False, path_type=Path), default=Path("labdns.ini"), show_default=True)
def config_init(path: Path) -> None:
    try:
        write_template(path)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to write template to %s: %s", path, exc)
        sys.exit(1)
    click.echo(f"Wrote template configuration to {path}")
