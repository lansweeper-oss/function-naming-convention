"""The composition function's main CLI."""

import click
from crossplane.function import cli as sdkcli

from function import fn


@click.command()
@sdkcli.standard_options
@click.option(
    "--grpc-message-size",
    type=int,
    default=None,
    help="Alias for --max-recv-message-size.",
)
def cli(grpc_message_size, **kwargs):
    """CLI entrypoint for function-naming-convention. We only expect callers via the CLI."""
    if grpc_message_size is not None:
        kwargs["max_recv_message_size"] = grpc_message_size
    sdkcli.run(fn.Runner(), **kwargs)


if __name__ == "__main__":
    cli()
