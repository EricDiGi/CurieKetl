import importlib.resources as pkg_resources
import inspect
import logging as log
import os
import re
from functools import wraps
from glob import glob
from typing import Any

import jinja2
import sqlparse
import yaml
from dotenv import load_dotenv
from jinja2 import Template

from .paths import ensure_rooting

global loader, jenv
loader = jinja2.FileSystemLoader(searchpath="./")
jenv = jinja2.Environment(loader=loader)



def import_raw(path):
    s = open(ensure_rooting(path)).read()
    return sqlparse.format(s, reindent=True, keyword_case='upper')

def prettySQL(s):
    return sqlparse.format(s, reindent=True, keyword_case='upper')

def title(s):
    return s.title()

def strip_jinja(s):
    jinja_braces = r'\{[\{\%\#]-?|-?[\%\}\#]\}'
    return re.sub(jinja_braces, '', s)

jenv.globals.update(
    import_raw=import_raw,
    title=title,
    prettySQL=prettySQL,
)

class Documentation:
    def __init__(self, config=None):
        # Glob project.yaml / project.yml
        if config is None:
            config = glob('./project.yaml') + glob('./project.yml')
            if len(config) == 0:
                raise FileNotFoundError("No project.yaml or project.yml found in current directory.")
            elif len(config) > 1:
                raise FileNotFoundError("Multiple project.yaml or project.yml found in current directory.")
            else:
                config = config[0]
        self.config = ensure_rooting(config)
        self.project = yaml.safe_load(open(self.config).read())['Project']

        self.site_config = self.project['Documentation']
        self.site_config['site']['nav'] = {'pipelines': []}

        self.replace_index()

        pipes = list( self.render_pipelines(self.project)['Pipelines'] )

        for pipe in pipes:
            blueprint_file = ensure_rooting(pipe['pipeline'])
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
                del mapped_args['self']
                _template = jenv.from_string(pkg_resources.read_text('curie.static.jinja', template))

                _endpoint = ensure_rooting(Template(endpoint).render(**mapped_args))
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
    
    @document('project.md.j2', './docs/project.md')
    def render_pipelines(self, pathways):
        return pathways
    
    @document('pipeline.md.j2', './docs/pipes/{{pipe.name}}.md')
    def render_pipe(self, pipe, config):
        self.site_config['site']['nav']['pipelines'].append({'name': pipe['name'], 'link': f'pipes/{pipe["name"]}.md'})
        return {'def':pipe,'config':config}
    
    @document('docs-settings.yaml.j2', 'docs-settings.yaml')
    def render_site_config(self):
        return self.site_config