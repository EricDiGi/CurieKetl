import os
import shutil
from glob import glob
from typing import Any, Dict, List

import yaml
from dotenv import dotenv_values

from . import connect, modes
from .dag import DAG
from .utils.jinja import Environment
from .utils.paths import ensure_rooting

class Pipeline:
    def __init__(self,name:str = None, pipeline:str = None, compile_path:str = None, download:str = None, connection:str = None, context:List[Any] = list(),  meta:Dict[str, Any] = None):
        """
        Pipeline object that represents a Curie pipeline
        
        Args:
            name (str, optional): Name of the pipeline. Defaults to None.
            pipeline (str, optional): Path to the pipeline file. Defaults to None.
            compile_path (str, optional): Path to the compiled pipeline. Defaults to None.
            download (str, optional): Path to download data to. Defaults to None.
            connection (str, optional): Connection to use for the pipeline. Defaults to None.
            context (List[Any], optional): Context to use for the pipeline. Defaults to list().
            meta (Dict[str, Any], optional): Meta information about the pipeline. Defaults to None.
        """
        
        self.path = pipeline
        self.compile_path = compile_path
        self.dag = None
        self.meta = None
        self.arguments = None
        self.context = context
        self.connection = connection
        self.download = download

        self.load(self.path)

    def load(self, path:str = None):
        """
        Loads the Pipeline from the specified path

        Args:
            path (str, optional): Path to the pipeline file. Defaults to None.
        """
        if path:
            self.path = path
        with open(self.path, 'r') as f:
            pipe = yaml.safe_load(f)
            self.arguments = pipe['arguments']
            self.dag = DAG(pipe['etl'],defaults=self.arguments)
    
    def clean(self):
        """
        Cleans the compiled DAG
        """
        # Purge the contents of the compile path if it exists
        # and the download path if it exists
        if self.compile_path:
            if os.path.exists(self.compile_path):
                shutil.rmtree(self.compile_path)
        if self.download:
            if os.path.exists(self.download):
                shutil.rmtree(self.download)
        
    def execute(self, mode:str,start:str = None, tables:List=None, args:dict = None):
        """
        Executes the DAG in the specified mode
        
        Args:
            mode (str): Mode to execute the DAG in
            args (dict, optional): Arguments to override the defaults. Defaults to None.
        """
        self.dag.execute(mode,start,tables, args, connection=self.context[self.connection], download_dir=self.download)
        return self
    
    def compile(self, mode:str, overrides:dict = None):
        """
        Compiles the DAG in the specified mode

        Args:
            mode (str): Mode to compile the DAG in
            overrides (dict, optional): Arguments to override the defaults. Defaults to None.
        """
        args = self.arguments
        if overrides:
            args.update(overrides)
        self.dag.compile(mode, compile_path=self.compile_path, overrides=args, connection=self.context[self.connection], download_dir=self.download)
        return self

    def describe(self, mode:str):
        """
        Describes the DAG in the specified mode

        Args:
            mode (str): Mode to describe the DAG in
        """

        return self.dag.describe(mode)
    
    def update_arguments(self, args:dict):
        """
        Updates the arguments for the DAG

        Args:
            args (dict): Arguments to update
        """
        self.arguments.update(args)
        return self

    def test_connection(self):
        """
        Tests the connection to the database

        Returns:
            bool: True if the connection is successful, False otherwise
        """
        return self.context[self.connection].test()
    
    def use_profile(self, name:str):
        """
        Switches the connection to the specified profile

        Args:
            name (str): Name of the profile to switch to
        """

        self.connection = name
        return self


class ProjectManager:
    j2 = Environment() # Jinja2 environment for rendering templates
    def __init__(self, path:str = None, defer_imports:bool = False):
        """
        ProjectManager object for coordinating pipelines and connections

        Args:
            path (str, optional): Path to the project file. Defaults to None.
            defer_imports (bool, optional): Whether to defer imports of the connections. Defaults to False.
        """
        self.path = path
        self.pipelines = {}
        self.connections = {}
        self.defer_imports = defer_imports
        self.load_pipelines(path)

    ###########################################################
    # Environment Loading Functions
    ###########################################################
    def env_file(self, path:str = None):
        """
        Loads the environment variables from the specified path

        Args:
            path (str, optional): Path to the environment file. Defaults to None.
        """
        path = ensure_rooting(path)
        env = dotenv_values(path)
        return dict(env)
    
    def build_connections(self, path:str = None):
        """
        Prepare all connections defined in the connections configuration file

        Args:
            path (str, optional): Path to the connections configuration file. Defaults to None.
        """
        with open(ensure_rooting(path), 'r') as f:
            cons = yaml.safe_load(f)
            for db in cons:
                for profile in cons[db]:
                    # > If there are secrets, load them and render the connection string
                    if 'secrets' in cons[db][profile]:
                        handler = list(cons[db][profile]['secrets'].keys())[0]
                        secrets = getattr(self, handler)(**cons[db][profile]['secrets'][handler])
                        for key in cons[db][profile]:
                            if key != 'secrets':
                                cons[db][profile][key] = self.j2.from_string(cons[db][profile][key]).render(**secrets)
                    self.connections[profile] = getattr(connect, db)(**cons[db][profile], defer_import=self.defer_imports)

    def load_pipelines(self, path:str = None):
        """
        Loads all pipelines defined in the project configuration file

        Args:
            path (str, optional): Path to the project configuration file. Defaults to None.
        """
        if path:
            self.path = path
        with open(self.path, 'r') as f:
            project = yaml.safe_load(f)
            self.build_connections(project['Project']['Connections'])
            for pipeline in project['Project']['Pipelines']:
                self.pipelines[pipeline['name']] = Pipeline(**pipeline, context=self.connections)
    def clean(self, pipeline:str = 'all'):
        print(pipeline)
        """
        Cleans the compiled DAG

        Args:
            pipeline (str, optional): Name of the pipeline to clean. Defaults to all.
        """
        if pipeline in ['all','.']:
            for pipeline in self.pipelines:
                self.pipelines[pipeline].clean()
        else:
            self.pipelines[pipeline].clean()
        return self

class Curie:
    """
    Curie object for managing projects and pipelines
    
    Args:
        path (str, optional): Path to the project file. Defaults to None.
        defer_imports (bool, optional): Whether to defer imports of the connections. Defaults to False.
    """
    def __init__(self, path:str = None, defer_imports:bool = False):
        self.path = path
        self.project = None
        self.defer_imports = defer_imports
        self.load(path)

        self.active_pipeline_name = None
        self.active_pipeline = None
        self.compiled_pipeline = None
        
    def load(self, path:str = None):
        """
        Loads the project from the specified path

        Args:
            path (str, optional): Path to the project file. Defaults to None.
        """
        if path is None:
            globbed = glob('**/project.yaml', recursive=True)
            if len(globbed) == 0:
                raise FileNotFoundError('Could not find project.yaml in the current directory or any of its parents.')
            elif len(globbed) > 1:
                raise FileNotFoundError('Found more than one project.yaml in the current directory or any of its parents.')
            else:
                path = globbed[0]
        self.path = path
        self.project = ProjectManager(path, defer_imports=self.defer_imports)

    def pipeline(self, name:str):
        """
        Returns the pipeline with the specified name

        Args:
            name (str): Name of the pipeline to return
        """
        self.active_pipeline_name = name
        self.active_pipeline = self.project.pipelines[name]
        return self
    
    def execute(self, mode:str, start:str = None,tables:List=None, args:dict = None):
        """
        Executes the pipeline in the specified mode

        Args:
            mode (str): Mode to execute the pipeline in
            args (dict, optional): Arguments to override the defaults. Defaults to None.
        """
        if not self.compiled_pipeline:
            raise Exception('Pipeline must be compiled before it can be executed.')
        self.active_pipeline.execute(mode,start,tables,args)
        return self
    
    def compile(self, mode:str, overrides:dict = None):
        """
        Compiles the pipeline in the specified mode

        Args:
            mode (str): Mode to compile the pipeline in
            overrides (dict, optional): Arguments to override the defaults. Defaults to None.
        """
        try:
            self.active_pipeline.compile(mode,overrides)
            self.compiled_pipeline = True
        except Exception as e:
            self.compiled_pipeline = False
            raise e
        return self
    
    def test_connection(self):
        """
        Tests the connection to the database

        Returns:
            bool: True if the connection is successful, False otherwise
        """
        return self.active_pipeline.test_connection()
    
    def describe(self, mode:str):
        """
        Describes the DAG in the specified mode

        Args:
            mode (str): Mode to describe the DAG in
        """
        return self.active_pipeline.describe(mode)
    
    def validate(self, mode:str, pipeline:str = None, node:str = None, connection:str = None):
        """
        Validates names are correct and that the DAG is valid
        """
        mode_classes = ['clean']+[name for name, obj in vars(modes).items() if isinstance(obj, type) and issubclass(obj, modes.Mode) and obj != modes.Mode]
        if mode not in mode_classes:
            raise ValueError(f'Invalid mode: {mode}')
        if mode == 'clean':
            acceptable_pipeline_names = ['.', 'all'] + list(self.project.pipelines.keys())
            if pipeline not in acceptable_pipeline_names:
                raise ValueError(f'Invalid pipeline: {pipeline}')
            return self
        acceptable_pipeline_names = list(self.project.pipelines.keys())
        if pipeline not in acceptable_pipeline_names:
            raise ValueError(f'Invalid pipeline: {pipeline}')
        acceptable_node_names = ['.', 'all'] + list(self.project.pipelines[pipeline].dag.nodes.keys())
        if node not in acceptable_node_names:
            raise ValueError(f'Invalid node: {node}')
        if connection and connection not in list(self.project.connections.keys()):
            raise ValueError(f'Invalid connection: {connection}')
        return self
    
    def clean(self, pipeline:str = 'all'):
        """
        Cleans the compiled DAG
        """
        self.project.clean(pipeline)
        return self
    
    def get_connection(self):
        """
        Returns the connection for the active pipeline
        """
        return self.active_pipeline.connection