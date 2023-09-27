import logging as log
import os
import shutil

from jinja2 import Template
from .utils import ensure_rooting


class Chasqui:
    ALL = '.'
    def __init__(self, topology, **kwargs):
        """
        Args:
            topology (dict): A dictionary containing the ETL topology. AKA the config.
            kwargs (dict): A dictionary containing the arguments for the ETL topology.
        """
        self.topology = topology
        self.ARGUMENTS = topology['arguments']
        self.preprocessed = None
        self.kwargs = kwargs
        self._name = "unnamed"
        self._source = None
        self._mode = None

    def prepare(self, mode=None):
        """
        Prepare the ETL topology for execution.

        Args:
            mode (str): The mode to prepare the ETL topology for. (run, save)
        """
        if mode is None:
            raise Exception("Error: No mode specified. Please specify a mode.")
        self._mode = mode
        self.dag = self.__infer_dag(self.topology['etl'], mode=mode)
        self.dag_roots = self.__dag_roots(self.topology['etl'], mode=mode)
        self.preprocessed = self.__prepare_etl(self.topology['etl'],self.dag, mode=mode, **self.ARGUMENTS)
        self.__handle_compiled_queries(self.preprocessed, mode=mode)
        return self
    
    def show_dag(self, use_filenames=False):
        """
        Show the DAG for the ETL topology.

        Args:
            use_filenames (bool): Whether or not to use filenames instead of table names.
        """
        return self.__infer_dag(self.topology['etl'], mode=self._mode, use_filenames=use_filenames)
    
    def __handle_compiled_queries(self, config, mode=None):
        if mode is None:
            raise Exception("Error: No mode specified. Please specify a mode.")
        __def_path_dir = ensure_rooting(os.path.join('./scripts', 'compiled', self._name, mode))
        if not os.path.exists(__def_path_dir):
            os.makedirs(__def_path_dir)
        for name in config.keys():
            if mode in config[name] and 'query' in config[name][mode]:
                with open(os.path.join(__def_path_dir, name + '.sql'), 'w') as f:
                    if mode in config[name] and 'query' in config[name][mode]:
                        f.write(config[name][mode]['query'])
    
    def __infer_dag(self, config, mode=None, use_filenames=False):
        queue = []
        # Infer Root Nodes (nodes with no dependencies)
        for node in config.keys():
            if mode in config[node] and 'depends_on' not in config[node][mode]:
                queue.append(node)
            if mode not in config[node]:
                queue.append(node)
        # Add nodes to queue if all dependencies are met
        while set(queue)!=set(config.keys()):
            for node in config.keys():
                if node not in queue:
                    if set(config[node][mode]['depends_on']).issubset(set(queue)):
                        queue.append(node)
        # Identify missing dependency tables
        for node in config.keys():
            if mode in config[node] and 'depends_on' in config[node][mode]:
                missing = [dep for dep in config[node][mode]['depends_on'] if dep not in queue]
                if len(missing)>0:
                    raise Exception(f'Missing dependencies for {node}: {missing}')
        if use_filenames:
            # Use script defined in config, skip if not defined
            requeue = []
            for i, node in enumerate(queue):
                if mode in config[node] and 'script' in config[node][mode]:
                    requeue.append(config[node][mode]['script'])
            queue = requeue
                
            # queue = ['' if 'script' not in config[node][mode] else config[node][mode]['script'] for node in queue]
        return queue

    def __dag_roots(self, config, mode=None):
        roots = []
        for node in config.keys():
            if mode in config[node] and 'depends_on' not in config[node][mode]:
                roots.append(node)
            if mode not in config[node]:
                roots.append(node)
        return roots

    def __wrap_query(self, source, query, method=None):
        """
        Wrap query with a method from the source class.
        
        :param source: A source class that exsavetends the Database class.
        :param query: A query string.
        :param method: A method from the source class. (seed, replace, etc.)
        """
        if method is None:
            raise Exception("Error: No method specified. Please specify a method.")
        # method_patterns is correlated a method and their corresponding query patterns (see sources.py, Redshift class)
        result = source.method_patterns()[method](query) # returns a list of queries
        return ';'.join(result) # returns a single query string
    
    def __prepare_etl(self, config, dag, mode=None, **kwargs):
        def apply_template(query, params): # Jinja Template, this function written to make code easier to read
            return Template(query).render(**params)
        # Execute the DAG
        for node in dag:
            try:
                # Prepare arguments and config
                config_node = config[node][mode]
                this = f"{'public' if 'schema' not in config[node] else config[node]['schema']}.{node}" # relates to {{this}} in query
                args = {**config, 'this':this, **kwargs} # combines config and arguments

                log.info(f"Preparing query for {node}...")
                # Decide to handle as query or script. Script is always a file path. Query is always a SQL string.
                if 'query' in config_node:
                    if 'method' in config_node: # if method is specified, wrap query with method
                        log.info(f"Using method: {config_node['method']}")
                        config_node['query'] = self.__wrap_query(self.source, config_node['query'], method=config_node['method'])
                    config[node][mode]['query'] = apply_template(config_node['query'], args)
                elif 'script' in config_node:
                    with open(ensure_rooting(config_node['script'])) as f:
                        log.info(f"Using script: {config_node['script']}")
                        config_node['query'] = f.read()
                        if 'method' in config_node:
                            log.info(f"Using method: {config_node['method']}")
                            config_node['query'] = self.__wrap_query(self.source, config_node['query'] , method=config_node['method'])
                    config[node][mode]['query'] = apply_template(config_node['query'], args)
            except Exception as e:
                if mode == 'save':
                    config[node].update({mode:{'query':f"SELECT * FROM {node}"}}) # Default to SELECT * FROM table
                    log.error(f'Error preparing query for {node}: {e}')
                    log.warning('Defaulting to preset query.')
                else:
                    log.warning(f'Error preparing query for "{node}" using {mode} mode: SKIPPING ASSUMED ROOT TABLE.')
                    log.error(e)
        return config
    
    def execute(self, tables:list):
        """
        Execute the ETL topology.

        Args:
            tables (list): A list of tables to execute. Order is important.
        """
        # Error Handling - Check if tables are in preprocessed queries
        if self.preprocessed is None:
            raise Exception("Error: No preprocessed queries. Please run prepare() first.")
        if Chasqui.ALL in tables:
            tables = self.dag
        if not isinstance(tables, list):
            raise Exception("Error: tables must be a list.")
        for table in tables:
            if table not in self.preprocessed:
                raise Exception(f"Error: {table} not found in preprocessed queries.")
        
        if self._mode == 'run':
            tables = list(filter(lambda x: x not in self.dag_roots, tables))
            print(tables)

        # Execute Queries
        self.results_ = None
        for table in tables:
            log.info(f"Running {table} using {self.mode_} mode...")
            if self._mode in self.preprocessed[table]:
                steps = self.preprocessed[table][self._mode]['query'].split(';')
                # trim empty strings
                steps = [step for step in steps if step != '']
                for step in steps:
                    # Save mode executes on source, and saves results to a target directory as the specified file type
                    # Results are expected to be pandas dataframes
                    if self._mode == 'save':
                        self.results_ = self._source.execute(step, mode=self._mode)
                        target__ = ensure_rooting(self.topology[self._mode]['target'])
                        file_type__ = None
                        if 'file_type' in self.topology[self._mode]:
                            file_type__ = self.topology[self._mode]['file_type']
                        if not os.path.exists(target__):
                            os.makedirs(target__)
                        __save_types = {
                            'csv': lambda t_: self.results_.to_csv(os.path.join(target__, t_ + '.csv'), index=False),
                            'json': lambda t_: self.results_.to_json(os.path.join(target__, t_ + '.json'), orient='records'),
                            'parquet': lambda t_: self.results_.to_parquet(os.path.join(target__, t_ + '.parquet'), index=False)
                        }
                        if file_type__ is None:
                            __save_types['csv'](table)
                        else:
                            __save_types[file_type__](table)
                    # Run mode only needs to execute, no results should be expected
                    else:
                        self._source.execute(step)
    
    def clean(self, facet):
        """
        Clean the ETL topology.

        Args:
            facet (str): The facet to clean. (compiled, data)
        """
        def remove_directory(dir):
                try:
                    shutil.rmtree(dir)
                except Exception as e:
                    return None
        if '.' in facet:
            facet = ['compiled', 'data']
        if 'compiled' in facet:
            known_target = ensure_rooting(f'./scripts/compiled/{self._name}')
            remove_directory(known_target)
        if 'data' in facet:
            known_targets = list(filter(lambda x: x!=0,[(0 if m not in self.topology else self.topology[m]['target']) for m in ['run', 'save']]))
            for kt in known_targets:
                remove_directory(ensure_rooting(kt))
    
    #====================================================================================================
    # DO NOT TOUCH BELOW ::: REQUIRED FOR CLASS INHERITANCE
    #====================================================================================================
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name):
        self._name = name

    @property
    def source(self):
        return self._source
    @source.setter
    def source(self, source):
        self._source = source

    @property
    def mode_(self):
        return self._mode
    @mode_.setter
    def mode_(self, mode):
        self._mode = mode

    #====================================================================================================
    # DO NOT TOUCH ABOVE ::: REQUIRED FOR CLASS INHERITANCE
    #====================================================================================================