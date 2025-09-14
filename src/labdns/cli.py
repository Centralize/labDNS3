import logging
import sys
from pathlib import Path

import click

from . import __version__
from .resolver import Resolver
from .server import DNSServer, ServerConfig
from .zonefile import load_zonefile


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@click.group(help="labDNS – lightweight DNS server")
@click.version_option(__version__, prog_name="labdns")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool) -> None:
    _configure_logging(verbose)


@cli.command(help="Validate a BIND-style zonefile")
@click.argument("zonefile", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def check(zonefile: Path) -> None:
    try:
        load_zonefile(zonefile)
    except Exception as exc:  # noqa: BLE001
        logging.error("Zonefile validation failed: %s", exc)
        sys.exit(2)
    click.echo(f"OK: {zonefile}")


@cli.command(help="Start DNS server")
@click.option("--zonefile", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--port", default=53, show_default=True, type=int)
@click.option("--interface", default="0.0.0.0", show_default=True)
def start(zonefile: Path, port: int, interface: str) -> None:
    try:
        zone = load_zonefile(zonefile)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to load zonefile: %s", exc)
        sys.exit(2)
    resolver = Resolver(zone)
    config = ServerConfig(interface=interface, port=port, zonefile=str(zonefile))
    server = DNSServer(config, resolver)
    server.run()


@cli.command(help="Show version")
def version() -> None:
    click.echo(__version__)


def main() -> None:
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
