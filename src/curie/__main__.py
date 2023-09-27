import argparse
import logging
import os
import sys
from zipfile import ZipFile

import importlib.resources as pkg_resources

from . import Curie, modes
from .document import generate_docs, serve_docs


def etl(args):
    # Get all mode class names where the class is a subclass of Mode (excluding Mode itself)
    mode_names = ['clean'] + [name for name, obj in vars(modes).items() if isinstance(obj, type) and issubclass(obj, modes.Mode) and obj != modes.Mode]
    # Validate mode
    if args.mode not in mode_names:
        logging.error('Mode must be one of: {}'.format(', '.join(mode_names+['clean'])))
        sys.exit(1)
    
    # Create Curie instance and validate input parameters
    curie = Curie(defer_imports=True).validate(args.mode, args.pipeline, args.start, args.connection)

    # In the case of clean, just clean and exit
    if args.mode == 'clean':
        curie.clean(args.pipeline)
        return
    
    # Load pipeline
    # print('Loading pipeline... {}'.format(args.pipeline))
    pipe = curie.pipeline(args.pipeline)

    if args.connection is None:
        args.connection = pipe.get_connection()

    # Get overrides
    overrides = {}
    if args.override_names is not None:
        for name, value in zip(args.override_names, args.override_values):
            overrides[name] = value
    
    # Execute mode
    pipe.compile(args.mode,overrides=overrides)
    if args.compile:
        return
    
    if pipe.test_connection() is False:
        logging.error('Connection test failed - please check connection details for {}'.format(args.connection))
        sys.exit(1)

    pipe.execute(args.mode, args.start, args.tables)

def docs(args):
    actmap = {
        'generate': generate_docs,
        'serve': serve_docs
    }
    actmap[args.action](args)

def initialize_project(args):
    # initialize a new project
    print("Initializing new project: " + args.init)
    # Convert to absolute path
    args.init = os.path.abspath(args.init)
    # check if project already exists
    if os.path.exists(args.init):
        return logging.error("Error: Project already exists.")
    else:
        os.mkdir(args.init)
        __defaults__ = pkg_resources.files("curie.static").joinpath("XXX.zip")
        with ZipFile(__defaults__, "r") as zipFile:
            zipFile.extractall(path=args.init)
        logging.info("Success: Project initialized.")

def main():
    """
    Curie main function.
    Expected formats:
        # Pipeline execution
        curie etl <mode (run|save|clean)> <pipeline> --download <download dir> --connection <connection> {{multiple overrides ???}}

        # Documentation
        curie docs generate
        curie docs serve

    *
    |-> ETL
    |   |-> Run
    |   |-> Save
    |   |-> Clean
    |
    |   *  |-> Pipeline (required)
    |   *  |-> Download (optional) (defaults to path specified in pipeline)
    |   *  |-> Connection (optional) (defaults to connection specified in pipeline)
    |   *  |-> Overrides    (optional) (defaults to None) (multiple overrides possible) (takes percedence over pipeline defaults)
    |   *  |-> Start        (required) ("." for all) (No default, node or all must be specified)
    |
    |-> Docs
        |-> Generate
        |-> Serve
    """

    # Parse arguments
    parser = argparse.ArgumentParser(description='Curie ETL')
    # Subparsers for etl and docs
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    # ETL subparser
    etl_parser = subparsers.add_parser('etl', help='ETL')
    etl_parser.add_argument('mode', choices=['run', 'save', 'clean','deploy'], help='Mode to run the pipeline in')
    etl_parser.add_argument('pipeline', help='Path to the pipeline file')
    # Optional arguments
    # The node to start at (required unless mode is clean)
    etl_parser.add_argument('start', nargs='?', help='Node to start at', default='.')
    etl_parser.add_argument('--tables', nargs='*', help='Tables to run')
    etl_parser.add_argument('--download', help='Download directory')
    etl_parser.add_argument('--connection', help='Connection to use')
    etl_parser.add_argument('--compile', action='store_true', help='Compile the pipeline, no execution.')
    # Override named arguments using --<argument>
    etl_parser.add_argument('--override-names', nargs='*', help='Names of variables to override')
    # Override named arguments using --<argument>=<value>
    etl_parser.add_argument('--override-values', nargs='*', help='Overrides for variables')

    # Docs subparser
    docs_parser = subparsers.add_parser('docs', help='Documentation')
    docs_parser.add_argument('action', choices=['generate', 'serve'], help='Command to run')

    # Init subparser
    init_parser = subparsers.add_parser('init', help='Initialize new project')
    init_parser.add_argument('init', help='Name of project to initialize')

    # Parse arguments
    args = parser.parse_args()

    # Execute correct function using mapping

    command_mapping = {
        'etl': etl,
        'docs': docs,
        'init': initialize_project
    }
    command_mapping[args.command](args)


if __name__ == '__main__':
    main()
