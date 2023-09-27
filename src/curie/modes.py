from typing import List, Dict, Any
import os
from jinja2 import Template
from contextlib import suppress
from .utils.paths import ensure_rooting
from .utils.jinja import Environment
import json
from IPython.display import display

class SaveMode:
    csv = lambda d, p: d.to_csv(p, index=False)
    json = lambda d, p: d.to_json(p, orient='records')
    parquet = lambda d, p: d.to_parquet(p, index=False, compression='snappy')

class Mode:
    def __init__(self, name:str, script: str = None, query: str = None, depends_on: List[str] = None, method: str = None, globs: Dict[str, Any] = None, defaults: Dict[str, Any] = None, meta: Dict[str, Any] = None):
        if script:
            self.script = script
        if query:
            self.query = query
        if depends_on:
            self.depends_on = depends_on
        self.method = method
        self.name = name
        self.meta = meta
        self.defaults = defaults if defaults else {}
        if globs:
            self.dict2Attr(globs)
        self.jinjaEnv = Environment()

    def dict2Attr(self, d: Dict[str, Any]):
        """
        Converts a dictionary to attributes of the object
        
        Args:
            d (Dict[str, Any]): Dictionary to convert to attributes
        """
        for k, v in d.items():
            setattr(self, k, v)
    
    def compile(self, node:str, overrides:Dict[str, Any] = None, context:Dict[str,Any]=None,schema:str='public', **kwargs): # Compile the script with jinja and save it to the path (by overwriting the file)
        """
        Compiles the query for the specified node
        
        Args:
            node (str): The current node.
            overrides (Dict[str, Any], optional): Overrides for the defaults. Defaults to None.
            context (Dict[str,Any], optional): Context to use for the query. Defaults to None.
            schema (str, optional): Schema to use for the query. Defaults to 'public'.
        """
        if not overrides:
            overrides = {}
        args = self.defaults
        args.update(overrides)
        args.update({'this':f'{schema}{"." if schema != "" else ""}{node}'})
        if context:
            args.update(context)
        if hasattr(self,'query'):
            query = self.query
            try:
                template = self.jinjaEnv.from_string(query).render(**args)
            except Exception as e:
                print(f'Error compiling query for {node} in mode {self.name}.')
                print(f'Query: {query}')
                raise e
        else:
            raise Exception(f'No query defined for mode {self.name}.')
        self.compiled_query = template
        return template
    
    def execute(self, node:str, connection:Any = None, context:Dict[str,Any] = None, download_dir:str = None):
        """
        Executes the query for the specified node

        Args:
            node (str): The current node.
            connection (Any, optional): Connection to use for the query. Defaults to None.
            context (Dict[str,Any], optional): Context to use for the query. Defaults to None.
            download_dir (str, optional): Path to download data to. Defaults to None.
        """
        if hasattr(self, 'compiled_query'):
            steps = self.compiled_query.split(';')
            for step in steps:
                rez = connection.execute(step)
            return rez
        return None

    def __repr__(self) -> str:
        return self.name
    
class ModeNotDefined(Exception):
    def __init__(self, mode: str):
        self.mode = mode
    def __str__(self):
        return f'{self.mode}'

class save(Mode):
    def __init__(self, 
                name: str, 
                script: str = None, 
                query: str = None, 
                depends_on: List[str] = None, 
                method: str = None, 
                variants: List[str] = None, 
                globs: Dict[str, Any] = None, 
                defaults: Dict[str, Any] = None, 
                store_results: bool = False,
                outputs: List[str] = None,
                meta: Dict[str, Any] = None
                ):
        super().__init__(name, script, query, depends_on, method, globs, defaults, meta)
        self.variants = variants
        self.store_results = store_results
        self.outputs = outputs

        self.execution_context = {}
        self.j2 = Environment()


    def compile(self, node:str, path:str, overrides:Dict[str, Any] = None, context:Dict[str,Any] = None, schema:str = 'public', **kwargs): # Compile the script with jinja and save it to the path (by overwriting the file)'
        """
        Compiles the query for the specified node

        Args:
            node (str): The current node.
            path (str): Path to save the query to.
            overrides (Dict[str, Any], optional): Overrides for the defaults. Defaults to None.
            context (Dict[str,Any], optional): Context to use for the query. Defaults to None.
            schema (str, optional): Schema to use for the query. Defaults to 'public'.

        Returns:
            str: The compiled query - if there are variants, this will be the base query
        """
        # Load the script from the path into memory if it exists
        if hasattr(self, 'script'):
            with open(ensure_rooting(self.script), 'r') as f:
                self.query = f.read()
        
        # Non-variant definitions go first
        if self.variants is None:
            path = ensure_rooting(f'{path}/{self.name}/{node}.sql')
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with open(path, 'w') as f:
                rendered = super().compile(node, overrides, context, schema=schema)
                self.compiled_query = rendered
                f.write(rendered)
            return None
        
        # Oh no, variants!
        for vn, variant in enumerate(self.variants):
            # Each variant will store the query in memory - starting with the base query
            variant['query'] = self.query
            output_name = variant['name']
            path = ensure_rooting(f'{path}/{self.name}/{node}/{output_name}.sql')
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            # * Jinja Iteration Profiles look like this: {{refTable.parameter}}
            # * This will return a list of values for that parameter
            # Handle Iteration Profiles
            if 'iterate_on' in variant.keys():
                # Render Jinja Iteration Profiles
                for arg in variant['iterate_on'].keys():
                    if isinstance(variant['iterate_on'][arg], str):
                        cont = context.copy()
                        cont.update(overrides)
                        if isinstance(variant['iterate_on'][arg], str):
                            variant['iterate_on'][arg] = json.loads(self.j2.from_string(variant['arguments'][arg]).render(**cont))
                iterator_profiles = [] # List of dictionaries
                # Validate the iteration profiles are the same length
                if len(set([len(k) for k in variant['iterate_on'].values()])) > 1:
                    raise Exception('Length of iteration profiles must be the same.')
                # Append a dictionary for each iteration profile
                for k in range(len(list(variant['iterate_on'].values())[0])):
                    profile = {}
                    for iarg in variant['iterate_on'].keys():
                        # if isinstance(variant['iterate_on'][iarg], str):
                        #     profile[iarg] = self.j2.from_string(variant['iterate_on'][iarg][k]).render(**overrides)
                        if isinstance(variant['iterate_on'][iarg], list):
                            profile[iarg] = variant['iterate_on'][iarg][k]
                    iterator_profiles.append(profile)
                # Compile the query for each iteration profile and the expected filename using the jinja context
                self.variants[vn]['queries'] = []
                self.variants[vn]['filenames'] = []
                for profile in iterator_profiles:
                    if 'arguments' in variant.keys():
                        temp = overrides.copy()
                        temp.update(profile)
                        for arg in variant['arguments'].keys():
                            profile[arg] = self.j2.from_string(variant['arguments'][arg]).render(**temp)
                    overrides.update(profile)
                    # Dump context keys that are overridden
                    for key in overrides.keys():
                        if key in context.keys():
                            del context[key]
                    query = super().compile(node, overrides, context, schema=schema)
                    path = os.path.join(os.path.dirname(path), self.j2.from_string(variant['name']).render(**overrides)+'.sql')
                    self.variants[vn]['queries'].append(query)
                    self.variants[vn]['filenames'].append(self.j2.from_string(variant['name']).render(**overrides))
                    with open(path, 'w') as f:
                        f.write(query)
            # Handle non-iteration profiles
            else:
                if 'arguments' in variant.keys():
                     for arg in variant['arguments'].keys(): # using jinja to render variables
                        if isinstance(variant['arguments'][arg], str):
                            variant['arguments'][arg] = self.j2.from_string(variant['arguments'][arg]).render(**overrides)
                variant['query'] = super().compile(node, overrides, context, schema=schema)
                variant['name'] = self.j2.from_string(variant['name']).render(**overrides)
                path = os.path.join(os.path.dirname(path), variant['name']+'.sql')
                with open(path, 'w') as f:
                    f.write(variant['query'])
        return None
    
    def execute(self, node:str, connection:Any = None, context:Dict[str,Any] = None, download_dir:str = None):
        """
        Executes the query for the specified node
        
        Args:
            node (str): The current node.
            connection (Any, optional): Connection to use for the query. Defaults to None.
            context (Dict[str,Any], optional): Context to use for the query. Defaults to None.
            download_dir (str, optional): Path to download data to. Defaults to None.
        
        Returns:
            pandas.DataFrame: The result of the query
        """
        rez = None
        # Variants go first
        # * If there are variants, execute each variant according to the stored query
        # * Save to the stored filename
        if hasattr(self, 'variants') and self.variants is not None:
            for i, variant in enumerate(self.variants):
                if 'iterate_on' in variant.keys():
                    for query, fn in zip(variant['queries'],variant['filenames']):
                        print(f'\t\tExecuting variant {fn}...')
                        path = ensure_rooting(f'{download_dir}/{node}/{fn}{".csv" if not hasattr(self, "filetype") else "."+self.filetype}')
                        if not os.path.exists(os.path.dirname(path)):
                            os.makedirs(os.path.dirname(path))
                        rez = connection.execute(query)
                        if hasattr(self, 'filetype') and self.filetype in SaveMode.__dict__.keys() and rez is not None:
                            getattr(SaveMode, self.filetype)(rez, path)
                        else:
                            getattr(SaveMode, 'csv')(rez, path)
                else:
                    print(f'\t\tExecuting variant {variant["name"]}...')
                    path = ensure_rooting(f'{download_dir}/{node}/{variant["name"]}{".csv" if not hasattr(self, "filetype") else "."+self.filetype}')
                    if not os.path.exists(os.path.dirname(path)):
                        os.makedirs(os.path.dirname(path))
                    rez = connection.execute(variant['query'])
                    if hasattr(self, 'filetype') and self.filetype in SaveMode.__dict__.keys() and rez is not None:
                        getattr(SaveMode, self.filetype)(rez, path)
                    else:
                        getattr(SaveMode, 'csv')(rez, path)
            return None
        # If it's normal, do normal things
        if hasattr(self, 'query'):
            path = ensure_rooting(f'{download_dir}/{node}{".csv" if not hasattr(self, "filetype") else "."+self.filetype}')
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            rez = connection.execute(self.compiled_query)
            if hasattr(self, 'filetype') and self.filetype in SaveMode.__dict__.keys() and rez is not None:
                getattr(SaveMode, self.filetype)(rez, path)
            else:
                getattr(SaveMode, 'csv')(rez, path)
            return rez

class run(Mode):
    def compile(self, node:str, path:str, overrides:Dict[str, Any] = None, context:Dict[str,Any] = None, connection:Any = None, schema:str = 'public'): # Compile the script with jinja and save it to the path (by overwriting the file)'
        """
        Compiles the query for the specified node
        
        Args:
            node (str): The current node.
            path (str): Path to save the query to.
            overrides (Dict[str, Any], optional): Overrides for the defaults. Defaults to None.
            context (Dict[str,Any], optional): Context to use for the query. Defaults to None.
            connection (Any, optional): Connection to use for the query. Defaults to None.
            schema (str, optional): Schema to use for the query. Defaults to 'public'.
            
            Returns:
                str: The compiled query
        """
        print(f'{path}/{self.name}/{node}.sql')
        path = ensure_rooting(f'{path}/{self.name}/{node}.sql')
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        
        if hasattr(self, 'query'):
            if hasattr(self, 'method'):
                rendered = ';'.join(connection.method_patterns()[self.method](self.query))
            rendered = super().compile(node, overrides, context, schema=schema)
        elif hasattr(self, 'script'):
            with open(ensure_rooting(self.script), 'r') as f:
                if hasattr(self, 'method'):
                    script = ';'.join(connection.method_patterns()[self.method](f.read()))
                else:
                    script = f.read()
                self.query = script
            rendered = super().compile(node, overrides, context, schema=schema)
        else:
            raise Exception(f'No script or query defined for mode {self.name}.')
        self.compiled_query = rendered
        with open(path, 'w') as f:
            f.write(rendered)
        return None
    
    def execute(self, node: str, connection: Any = None, context: Dict[str, Any] = None, download_dir: str = None):
        # Use the super execute method
        return super().execute(node, connection, context, download_dir)
    
    def __repr__(self):
        return 'run'