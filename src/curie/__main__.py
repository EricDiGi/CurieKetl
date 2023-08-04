import argparse
import importlib.resources as pkg_resources
import logging as log
import os
import subprocess
import sys
import time
from zipfile import ZipFile

from .lab import Curie
from .mk import Documentation
from .utils import ensure_rooting

global watch_list
watch_list = []

def generate_docs():
    global watch_list
    try:
        subprocess.run(["mkdocs", "build", "--config-file", "docs-settings.yaml"])
        log.info("Documentation generated using mkdocs.")
        docs = Documentation()
        watch_list = docs.get_watch()
    except Exception as e:
        log.error("Error generating documentation:", str(e))

def serve_docs():
    global watch_list
    try:
        docs = Documentation()
        watch_list = docs.get_watch()
        subprocess.run(["mkdocs", "serve", "--config-file", "docs-settings.yaml"])
    except Exception as e:
        log.error("Error serving documentation:", str(e))

def __initialize_project(args):
        watch_list = [
            ensure_rooting("./config/pathways.yaml"),
        ]
    # initialize a new project
        print("Initializing new project: " + args.init)
        # check if project already exists
        if os.path.exists(args.init):
            return log.error("Error: Project already exists.")
        else:
            os.mkdir(args.init)
            __defaults__ = pkg_resources.files("curie.defaults").joinpath("curie_seed.zip")
            with ZipFile(__defaults__, "r") as zipFile:
                zipFile.extractall(path=args.init)
            log.info("Success: Project initialized.")


def main():
    # initialize parser
    parser = argparse.ArgumentParser(description="Curie - A Python-based framework for database agnostic information routing.", prog="curie")
    subparsers = parser.add_subparsers(help="Curie commands", dest="command")

    # docs arguments
    docs_parser = subparsers.add_parser("docs", help="Documentation commands")
    docs_subparsers = docs_parser.add_subparsers(help="Documentation commands", dest="docs_command")

    docs_parser_generate = docs_subparsers.add_parser("generate", help="Generate documentation")
    docs_parser_generate.set_defaults(func=generate_docs)

    docs_parser_serve = docs_subparsers.add_parser("serve", help="Serve documentation")
    docs_parser_serve.set_defaults(func=serve_docs)

    # etl arguments
    etl_parser = subparsers.add_parser("etl", help="ETL commands")

    etl_parser.add_argument('-v','--version', help="Print the version of Curie", action="store_true")
    etl_parser.add_argument('-i', '--init', help="Initialize a new project", action="store", metavar="<project_name>")

    etl_parser.add_argument('-r', '--run', help="Run the pipeline against the database", action="store", metavar="<pipeline_name>")
    etl_parser.add_argument('-s', '--save', help="Save tables locally", action="store", metavar="<pipeline_name>")

    etl_parser.add_argument('--clean', help="Clean a project", action="store", metavar="<pipeline_name>")
    etl_parser.add_argument('-c','--compile', help="Compile a pipeline", action="store_true", default=False)
    
    etl_parser.add_argument('-t','--tables', nargs="+", help="List of tables to affect. For all use \".\"", action="store", metavar="<table>")
    etl_parser.add_argument('--facet', nargs="+", help="List of facets to clean (compiled, data). For all use \".\"", action="store", metavar="<facet>") # Not required

    etl_parser.add_argument('--debug', help="Enable debug mode", action="store_const", dest="loglevel", const=log.DEBUG, default=log.WARNING)
    etl_parser.add_argument('--verbose', help="Enable verbose mode", action="store_const", dest="loglevel", const=log.INFO)
    etl_parser.add_argument('--show-dag', help="Generate a DAG of the pipeline", action="store_true", default=False)

    def dagman(args,prep):
        if args.show_dag:
            log.info("DAG ++ " + str(prep.show_dag(use_filenames=True)))


    # USE SUBPARSERS
    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func()
    elif args.command == "etl":
        log.basicConfig(level=args.loglevel, format='%(asctime)s - %(levelname)s - %(message)s')
        args.tables = args.tables if args.tables is not None else ['.']
        if args.init:
            __initialize_project(args)
            return
        elif args.clean:
            # curie --clean <pipeline_name> --facet <facet(s)>
            # Defaults to all facets: curie --clean <pipeline_name>
            pipeline = args.clean
            facets = ['.']
            if args.facet is not None:
                facets = args.facet
            log.info("Cleaning project: " + pipeline)
            curie_ = Curie()
            curie_.path(pipeline).clean(facets)
            return
        elif args.version:
            # curie --version
            print("Curie version: " + Curie.__version__)
            return
        elif args.compile:
            curie_ = Curie()
            if args.run:
                # curie --run <pipeline_name> --compile
                # curie -r <pipeline_name> -c
                com = curie_.path(args.run).mode('run')
                dagman(args,com)
            elif args.save:
                # curie --save <pipeline_name> --compile
                # curie -s <pipeline_name> -c
                com = curie_.path(args.save).mode('save')
                dagman(args,com)
            return
        elif args.run:
            # curie --run <pipeline_name> -t <table(s)>
            # curie -r <pipeline_name> -t <table(s)>
            curie_ = Curie()
            curie_.path(args.run).mode('run').execute(args.tables)
            return
        elif args.save:
            # curie -s <pipeline_name> -t <table(s)>
            curie_ = Curie()
            curie_.path(args.save).mode('save').execute(args.tables)
            return
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
