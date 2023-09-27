import logging as log
import subprocess

from .utils.docs import Documentation


def generate_docs(args):
    print("Generating docs")
    try:
        subprocess.run(["mkdocs", "build", "--config-file", "docs-settings.yaml"])
        docs = Documentation()
    except Exception as e:
        log.error("Error building docs: ", e.with_traceback())

def serve_docs(args):
    print("Serving docs")
    try:
        subprocess.run(["mkdocs", "serve", "--config-file", "docs-settings.yaml"])
    except Exception as e:
        log.error("Error serving docs: ", e.with_traceback())