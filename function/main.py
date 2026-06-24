"""The composition function's main CLI."""

import asyncio

import click
from crossplane.function import logging, runtime

from function import fn


@click.command()
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Emit debug logs.",
)
@click.option(
    "--address",
    default="0.0.0.0:9443",
    show_default=True,
    help="Address at which to listen for gRPC connections",
)
@click.option(
    "--tls-certs-dir",
    help="Serve using mTLS certificates.",
    envvar="TLS_SERVER_CERTS_DIR",
)
@click.option(
    "--insecure",
    is_flag=True,
    help="Run without mTLS credentials. If you supply this flag --tls-certs-dir will be ignored.",
)
@click.option(
    "--grpc-message-size",
    type=int,
    default=None,
    help="Maximum gRPC message size in MiB for both send and receive (defaults to 4 MiB).",
    envvar="GRPC_MESSAGE_SIZE",
)
# We only expect callers via the CLI.
def cli(
    debug: bool,  # noqa: FBT001
    address: str,
    tls_certs_dir: str,
    insecure: bool,  # noqa: FBT001
    grpc_message_size: int | None,
) -> None:
    """A Crossplane composition function."""
    level = logging.Level.INFO
    if debug:
        level = logging.Level.DEBUG
    logging.configure(level=level)
    options = None
    if grpc_message_size is not None:
        options = [
            ("grpc.max_send_message_length", grpc_message_size * 1024 * 1024),
            ("grpc.max_receive_message_length", grpc_message_size * 1024 * 1024),
        ]
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runtime.serve(
            fn.Runner(),
            address,
            creds=runtime.load_credentials(tls_certs_dir),
            insecure=insecure,
            options=options,
        )
    except Exception as e:
        click.echo(f"Cannot run function: {e}")


if __name__ == "__main__":
    cli()
