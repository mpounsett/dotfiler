# ==============================================================================
#  Copyright 2026 Matthew Pounsett <matt@conundrum.com>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ==============================================================================
"""The main application setup functions."""

import argparse
import pathlib
import sys

from dotfiler.enum import ConflictAction


# Glory be to Jeppe Ledet-Pedersen!
# https://stackoverflow.com/a/13429281/951589
class SubcommandHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Format help for subcommands.

    Removes the redundant <command> from help output in subparsers.
    """
    def _format_action(self, action: argparse.Action) -> str:
        parts = super()._format_action(action)
        if action.nargs == argparse.PARSER:
            parts = "\n".join(parts.split("\n")[1:])
        return parts


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="dotfiler",
        description=__doc__,
        formatter_class=SubcommandHelpFormatter,
    )
    subparsers = parser.add_subparsers()

    global_options = argparse.ArgumentParser(add_help=False)
    global_options.add_argument(
        '-r', '--rules-file',
        help='Path to rules file',
        type=pathlib.Path,
        metavar='PATH',
        default=pathlib.Path('~/.config/dotfiler/rules.yaml').expanduser(),
    )
    global_options.add_argument(
        '-N', '--no-op',
        help=(
            """
            Skip any data-altering steps, reporting what would have been done
            instead.
            """
        ),
        action='store_false',
        dest='op',
    )

    tasks_cmd = subparsers.add_parser(
        'tasks',
        help="Run file setup tasks.",
        formatter_class=SubcommandHelpFormatter,
        parents=[global_options],
    )
    tasks_cmd.add_argument(
        '--on-conflict',
        help="Override on_conflict setting from rules file.",
        choices=[action.value for action in ConflictAction]
    )
    tasks_cmd.add_argument(
        '--source-base',
        help=(
            """
            Override default source base directory (normally the directory
            containing the rules file).
            """
        ),
        type=pathlib.Path,
        metavar='PATH',
    )

    return parser.parse_args(args)


def cli() -> None:
    """Main entrypoint."""
    parse_args()
