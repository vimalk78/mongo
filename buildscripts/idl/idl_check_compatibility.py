# Copyright (C) 2021-present MongoDB, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the Server Side Public License, version 1,
# as published by MongoDB, Inc.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Server Side Public License for more details.
#
# You should have received a copy of the Server Side Public License
# along with this program. If not, see
# <http://www.mongodb.com/licensing/server-side-public-license>.
#
# As a special exception, the copyright holders give permission to link the
# code of portions of this program with the OpenSSL library under certain
# conditions as described in each individual source file and distribute
# linked combinations including the program with the OpenSSL library. You
# must comply with the Server Side Public License in all respects for
# all of the code used other than as permitted herein. If you modify file(s)
# with this exception, you may extend this exception to your version of the
# file(s), but you are not obligated to do so. If you do not wish to do so,
# delete this exception statement from your version. If you delete this
# exception statement from all source files in the program, then also delete
# it in the license file.
"""Checks compatibility of old and new IDL files.

In order to support user-selectable API versions for the server, server commands are now
defined using IDL files. This script checks that old and new commands are compatible with each
other, which allows commands to be updated without breaking the API specifications within a
specific API version.

This script accepts two directories as arguments, the "old" and the "new" IDL directory.
Before running this script, run checkout_idl_files_from_past_releases.py to find and create
directories containing the old IDL files from previous releases.
"""

import argparse
import logging
import os
import sys
from typing import Dict, List

from idl import parser, syntax
from idl.compiler import CompilerImportResolver
import idl_compatibility_errors


def check_compatibility(old_idl_dir: str, new_idl_dir: str, import_directories: List[str]
                        ) -> idl_compatibility_errors.IDLCompatibilityErrorCollection:
    """Check IDL compatibility between old and new IDL commands."""
    ctxt = idl_compatibility_errors.IDLCompatibilityContext(
        old_idl_dir, new_idl_dir, idl_compatibility_errors.IDLCompatibilityErrorCollection())
    new_commands: Dict[str, syntax.Command] = dict()

    for dirpath, _, filenames in os.walk(new_idl_dir):
        for new_filename in filenames:
            new_idl_file_path = os.path.join(dirpath, new_filename)
            with open(new_idl_file_path) as new_file:
                new_idl_file = parser.parse(
                    new_file, new_idl_file_path,
                    CompilerImportResolver(import_directories + [new_idl_dir]))
                if new_idl_file.errors:
                    new_idl_file.errors.dump_errors()
                    raise ValueError(f"Cannot parse {new_idl_file_path}")

                for new_cmd in new_idl_file.spec.symbols.commands:
                    if new_cmd.api_version == "":
                        continue

                    if new_cmd.api_version != "1":
                        # We're not ready to handle future API versions yet.
                        ctxt.add_command_invalid_api_version_error(
                            new_cmd.command_name, new_cmd.api_version, new_idl_file_path)
                        continue

                    if new_cmd.command_name in new_commands:
                        ctxt.add_duplicate_command_name_error(new_cmd.command_name, new_idl_dir,
                                                              new_idl_file_path)
                        continue

                    new_commands[new_cmd.command_name] = new_cmd

    ctxt.errors.dump_errors()
    return ctxt.errors


def main():
    """Run the script."""
    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument("-v", "--verbose", action="count", help="Enable verbose logging")
    arg_parser.add_argument("old_idl_dir", metavar="OLD_IDL_DIR",
                            help="Directory where old IDL files are located")
    arg_parser.add_argument("new_idl_dir", metavar="NEW_IDL_DIR",
                            help="Directory where new IDL files are located")
    args = arg_parser.parse_args()

    error_coll = check_compatibility(args.old_idl_dir, args.new_idl_dir, [])
    if error_coll.errors.has_errors():
        sys.exit(1)


if __name__ == "__main__":
    main()
