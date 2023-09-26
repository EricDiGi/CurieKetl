import logging as log
import os
from typing import Any

import yaml
from dotenv import load_dotenv
from jinja2 import Template

from . import sources
from .inca import Chasqui
from .utils import ensure_rooting, secrets

class Curie:
    """
    The module we all came here for.
    Curie is a framework for database agnostic information routing.
    Common use cases include:
        - Data synchronization
        - API integration
        - MLOps pipelines
        - Data Lifecycle Management
    
    """
    __version__ = '0.1.0'
    def __init__(self, config_file='./config/pathways.yaml', debug=False, verbose=False, **kwargs):
        config_file = ensure_rooting(config_file)
        # Logging
        loglevel = log.root.level
        if log.root.level == log.NOTSET or log.root.level == log.WARNING:
            if debug:
                loglevel = log.DEBUG
            elif verbose:
                loglevel = log.INFO
        log.basicConfig(
            level=loglevel, format='%(asctime)s - %(levelname)s - %(message)s')
        # Flags
        self.ALL = Chasqui.ALL
        self.name = None

        if os.path.exists(config_file):
            self.__config_file = config_file
            self.__config__ = yaml.safe_load(open(self.__config_file))

            self.__connections = Connections(self.__config__['Connections'])
            self.__resource_tree = SourceTree(
                self.__connections, defer_import=True)

            self.__pathways = Pathways(self.__config__['Pathways'])
        else:
            raise FileNotFoundError(
                'Configuration file not found at ' + config_file)

    def __repr__(self):
        return f'Curie({len(self.__resource_tree)} Connections, {len(self.__pathways)} Pathways)'

    def connect(self, name: str, help=False) -> Any:
        if name not in self.__resource_tree:
            name = name.replace('_', '-')  # Snake case conformity.
        try:
            # Help will print out a snippet to aid in using the provided connection
            return self.__resource_tree[name].connect(help=help)
        except KeyError:
            raise AttributeError(f'No connection named {name}')

    def path(self, name):
        # Stages a pathway for loading
        if name == '.':
            for path in self.__config__['Pathways']:
                self.name = None
                self.__pathways.load_path(path, self)
        elif name not in self.__config__['Pathways']:
            raise AttributeError(f'No pathway named {name}')
        else:
            self.name = name
            self.__pathways.load_path(name, self)
        return self
    
    def show_dag(self, **kwargs):
        if self.name not in self.__pathways:
            raise AttributeError(f'No pathway named {self.name}')
        else:
            print("PATHWAY NAME >>> " + self.name)
            return self.__pathways[self.name].show_dag(**kwargs)

    def execute(self, tables: list):
        """
        Execute one pipeline only, ignore ALL flags
        """
        if self.name is None:
            raise AttributeError(
                'No pathway recognized. Please specify a single pathway using path()')
        if self.name not in self.__pathways:
            raise AttributeError(f'No pathway named {self.name}')
        self.__pathways[self.name].execute(tables)
        return None

    def clean(self, *facet):
        """
        Clean many or one pipelines from a project
        """
        if self.name is None:
            for name in self.__pathways:
                self.__pathways[name].clean(*facet)
        elif self.name not in self.__pathways:
            raise AttributeError(f'No pathway named {self.name}')
        else:
            self.__pathways[self.name].clean(*facet)
        return None

    def mode(self, mode):
        """
        Prepare pipeline using specified mode
        """
        if self.name is None:
            raise AttributeError(
                'No pathway recognized. Please specify a single pathway using path()')
        if self.name not in self.__pathways:
            raise AttributeError(f'No pathway named {self.name}')
        self.__pathways[self.name].mode(mode)
        return self

    @property
    def connections(self):
        return self.__resource_tree


class SourceTree(dict):
    def __init__(self, config, defer_import=True):
        super().__init__()
        self.defer_import = defer_import
        self.prepare(config)

    def prepare(self, config):
        for source in config:
            for conn in config[source]:
                temp = {conn: getattr(sources, source)(
                    **config[source][conn], defer_import=self.defer_import)}
                self.update(temp)
        return self


class Connections(dict):
    def __init__(self, config_dict):
        self.config_dict = config_dict
        self.connection_contents = self.__identify_and_load()

        for key in self.connection_contents:
            for _c in self.connection_contents[key]:
                if 'secrets' in self.connection_contents[key][_c]:
                    secret_manager = list(
                        self.connection_contents[key][_c]['secrets'].keys())[0]
                    args = getattr(secrets, secret_manager)(
                        **self.connection_contents[key][_c]['secrets'][secret_manager])
                    for kkey in self.connection_contents[key][_c]:
                        if kkey != 'secrets':
                            self.connection_contents[key][_c][kkey] = Template(
                                self.connection_contents[key][_c][kkey]).render(**args)
                    del self.connection_contents[key][_c]['secrets']
        super().__init__(self.connection_contents)

    def __load_from_file(self, obj):
        """
        Load a configuration file from a file path
        """
        self.__file = ensure_rooting(obj)
        if os.path.exists(self.__file):
            return yaml.safe_load(open(self.__file))


    def __identify_and_load(self):
        """
        Identify the loader to use for the configuration file and load it into a dictionary
        """
        __valid_handlers = {
            'file': lambda x: self.__load_from_file(x)
        }
        for key in __valid_handlers:
            if key in self.config_dict:
                return __valid_handlers[key](self.config_dict[key])
        raise ValueError('No valid configuration file handler found')


class Blueprint(Chasqui):
    def __init__(self, connection, blueprint, curie=None, **kwargs):
        """
        An abstraction of Chasqui
        Overlays utility functions on the Chasqui class to make it easier to use, and harder to break

        Args:
            connection (str): Connection name
            blueprint (str): Path to blueprint file
            curie (Curie, optional): Curie object. Defaults to None.

        Raises:
            AttributeError: Blueprint file not found

        """
        if curie is None:
            raise AttributeError('Curie object not passed to Blueprint')
        self.connection = connection
        if os.path.exists(ensure_rooting(blueprint)):
            self.blueprint_file = ensure_rooting(blueprint)
            self.blueprint = yaml.safe_load(open(self.blueprint_file))
            super().__init__(self.blueprint)
            if 'name' in kwargs:
                self.name = kwargs['name']
            self.source = curie.connections[self.connection]
        else:
            raise FileNotFoundError('Blueprint file not found at ' + blueprint)

    def mode(self, mode='save'):
        """
        Prepare pipeline using specified mode

        Args:
            mode (str, optional): Mode to prepare pipeline for. Defaults to 'save'.
        """
        self.mode_ = mode
        super().prepare(mode=mode)
        return self

    def execute(self, tables: list):
        """
        Execute the pipeline

        Args:
            tables (list): List of tables to execute
        """
        super().execute(tables)
        return self
    
    def show_dag(self, **kwargs):
        return super().show_dag(**kwargs)

    def clean(self, facet):
        super().clean(facet)


class Pathways(dict):
    def __init__(self, config_dict):
        """
        * Pathways is a dictionary of Blueprint objects
        * They are loaded from a configuration file and accessed by name
        """
        super().__init__()
        self.config_dict = config_dict

    def load_path(self, __name, __curie):
        """
        * Load a blueprint by name and return a Blueprint object
        """
        super().update({__name: Blueprint(curie=__curie,
                                          **self.config_dict[__name], name=__name)})
        return self[__name]
    
    def show_dag(self,__name, **kwargs):
        print("PATHWAY NAME >>> " + __name)
        return self[__name].show_dag(**kwargs)

    def __str__(self):
        return super().__str__()
