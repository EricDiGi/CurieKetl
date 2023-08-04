import logging as log
import os
from typing import Any

import yaml
from dotenv import load_dotenv
from jinja2 import Template

from .utils import ensure_rooting, secrets
import importlib.resources as pkg_resources


class Documentation:
    def __init__(self, config="./config/pathways.yaml"):
        self.config = ensure_rooting(config)
        self.pathways = yaml.safe_load(open(self.config).read())
        
        self.document_pathways(self.pathways)
    
    def document_pathways(self, pathways):
        template = Template(pkg_resources.read_text('curie.defaults', 'pipeline.md.j2'))
        endpoint = ensure_rooting('./docs/pipelines.md')
        with open(endpoint, 'w') as f:
            f.write(template.render(pathways))