import importlib.resources as pkg_resources
import inspect
import logging as log
import os
from functools import wraps
from typing import Any

import yaml
from dotenv import load_dotenv
from jinja2 import Template
import jinja2

from .utils import ensure_rooting, secrets

global loader, jenv
loader = jinja2.FileSystemLoader(searchpath="./")
jenv = jinja2.Environment(loader=loader)

def import_raw(path):
    return open(ensure_rooting(path)).read()

def title(s):
    return s.title()

jenv.globals.update(
    import_raw=import_raw,
    title=title
)

class Documentation:
    def __init__(self, config="./config/pathways.yaml"):
        
        self.config = ensure_rooting(config)
        self.pathways = yaml.safe_load(open(self.config).read())

        self.site_config = self.pathways['Documentation']
        self.site_config['site']['nav'] = {'pipelines': []}

        self.replace_index()

        pipes = list( self.render_pathways(self.pathways)['Pathways'].keys() )

        for pipe in pipes:
            blueprint_file = ensure_rooting(self.pathways['Pathways'][pipe]['blueprint'])
            if not os.path.exists(blueprint_file):
                raise FileNotFoundError(f"Blueprint file for {pipe} not found at {blueprint_file}.")
            blueprint = yaml.safe_load(open(blueprint_file).read())
            self.render_pipe(pipe, blueprint)
        
        self.render_site_config()
        print(self.site_config)
    
    def document(template, endpoint):
        def decorator(func):
            def wrapper(*args, **kwargs):
                mapped_args = dict(zip(inspect.getfullargspec(func).args, args))
                mapped_args.update(kwargs)
                _template = jenv.from_string(pkg_resources.read_text('curie.defaults.jinja', template))
                _endpoint = ensure_rooting(endpoint.format(**mapped_args))
                results = func(*args, **kwargs)
                if not os.path.exists(os.path.dirname(_endpoint)):
                    os.makedirs(os.path.dirname(_endpoint))
                with open(_endpoint, 'w') as f:
                    f.write(_template.render(**results))
                return results
            return wrapper
        return decorator

    def replace_index(self, readme='./README.md', endpoint="./docs/index.md"):
        src = ensure_rooting(readme)
        dst = ensure_rooting(endpoint)
        with open(dst, 'w') as f:
            f.write(open(src).read())
    
    @document('pipeline.md.j2', './docs/pipelines.md')
    def render_pathways(self, pathways):
        return pathways
    
    @document('pipeline-bp.md.j2', './docs/pipes/{name}.md')
    def render_pipe(self, name, pipeline_def):
        pipeline_def['pipeline_name'] = name
        self.site_config['site']['nav']['pipelines'].append({'name': name, 'link': f'pipes/{name}.md'})
        return pipeline_def
    
    @document('docs-settings.yaml.j2', 'docs-settings.yaml')
    def render_site_config(self):
        return self.site_config