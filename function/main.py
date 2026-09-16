"""The composition function's main CLI."""

import click
from crossplane.function import cli as sdkcli

from function import fn


@click.command()
@sdkcli.standard_options
def cli(**kwargs):
    """CLI entrypoint for function-naming-convention. We only expect callers via the CLI."""
    sdkcli.run(fn.Runner(), **kwargs)


if __name__ == "__main__":
    cli()
