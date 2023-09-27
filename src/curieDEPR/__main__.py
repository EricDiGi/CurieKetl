import argparse
import importlib.resources as pkg_resources
import logging as log
import os
import subprocess
import sys
import time
from zipfile import ZipFile
import yaml

try:
    from .lab import Curie
    from .mk import Documentation
    from .utils import ensure_rooting
except FileNotFoundError as e:
    pass # this is fine, other errors will be raised if there is a problem. Doing this allows us to initialize a project without the lab and mk modules.

def generate_docs(args):
    try:
        subprocess.run(["mkdocs", "build", "--config-file", "docs-settings.yaml"])
        log.info("Documentation generated using mkdocs.")
        docs = Documentation()
    except Exception as e:
        log.error("Error generating documentation:", str(e))

def serve_docs(args):
    try:
        docs = Documentation()
        subprocess.run(["mkdocs", "serve", "--config-file", "docs-settings.yaml"])
    except Exception as e:
        log.error("Error serving documentation:", str(e))

def __initialize_project(args):
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

def add_pipeline(args):
    project_def_file = ensure_rooting('./project.yaml')
    project_def = yaml.safe_load(open(project_def_file).read())['Configuration']
    connections_file, pathways_file = [ensure_rooting(project_def[x]) for x in ['connections', 'pathways']]

    print("Adding pipeline: " + args.name)
    # if a connection is specified, check if it exists
    connection_found = False
    if hasattr(args, "connection") and args.connection is not None:
        connections = yaml.safe_load(open(connections_file).read())
        for dbtype in connections:
            if args.connection in connections[dbtype]:
                connection_found = True
                break
        if not connection_found:
            return log.error("Error: Connection not found.")
        
    # check if pipeline already exists
    if os.path.exists(pathways_file):
        pathways = yaml.safe_load(open(pathways_file).read())
        name_in_files = lambda n,f: any([n in x for x in f])
        if args.name in pathways['Pathways'] or name_in_files(args.name, os.listdir('./blueprints')):
            return log.error("Error: Pipeline already exists.")
        else:
            pathways['Pathways'][args.name] = {
                'connection': '' if not hasattr(args, "connection") or args.connection is None else args.connection,
                'blueprint': f'./blueprints/{args.name}.yaml',
                'description': ''
            }
            with open(pathways_file, 'w') as f:
                yaml.dump(pathways, f)

            # create blueprint
            blueprint_file = ensure_rooting(f'./blueprints/{args.name}.yaml')
            with open(blueprint_file, 'w') as f:
                yaml.dump({
                    "sync": {
                        "target": "default",
                        "overwrite": True
                    },
                    "arguments": {'limit':100},
                    "etl": {
                        "some_table":{
                            "manifest": 'table',
                            "schema": "public",
                            "save": {
                                "query": "SELECT * FROM {{this}}"
                            }
                        }
                    }
                }, f)
    pass


def main():
    # initialize parser
    parser = argparse.ArgumentParser(description="Curie - A Python-based framework for database agnostic information routing.", prog="curie")
    subparsers = parser.add_subparsers(help="Curie commands", dest="command", required=True)

    # docs arguments
    docs_parser = subparsers.add_parser("docs", help="Documentation commands")
    docs_subparsers = docs_parser.add_subparsers(help="Documentation commands", dest="docs_command")

    docs_parser_generate = docs_subparsers.add_parser("generate", help="Generate documentation")
    docs_parser_generate.set_defaults(func=generate_docs)

    docs_parser_serve = docs_subparsers.add_parser("serve", help="Serve documentation")
    docs_parser_serve.set_defaults(func=serve_docs)

    # etl arguments
    etl_parser = subparsers.add_parser("etl", help="ETL commands")
    etl_subparsers = etl_parser.add_subparsers(help="ETL commands", dest="etl_command")
    
    # ETL functions

    # Add a pipeline
    etl_parser_add = etl_subparsers.add_parser("add", help="Add a pipeline")
    etl_parser_add.add_argument('-n', '--name', help="Name of the pipeline", action="store", metavar="<pipeline_name>")
    etl_parser_add.add_argument('-c', '--connection', help="Connection to use for the pipeline", action="store", metavar="<connection_name>")
    etl_parser_add.set_defaults(func=add_pipeline)

    # ETL arguments
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
    args, extras = parser.parse_known_args()


    if hasattr(args, "func"):
        print("Running command: " + args.command)
        args.func(args)
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
