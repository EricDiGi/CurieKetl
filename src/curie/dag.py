from typing import List, Dict, Any
import os
from contextlib import suppress
import re
from . import utils
from .modes import Mode, save, run

class Node:
    def __init__(self, name:str, manifest:str = None, schema:str = 'public', fields: List[Dict[str, Any]] = None, meta: Dict[str, Any] = None, mode_globals: Dict[str, Any] = None, defaults: Dict[str, Any] = None, **modes):
        self.fields = fields
        self.meta = meta
        self.manifest = manifest
        self.schema = schema
        self.modes = dict([(mode, globals()[mode](mode, **modes[mode], globs=mode_globals, defaults=defaults)) for mode in modes.keys()])
        self.name = name
        
    def get_mode(self, name: str) -> Mode:
        """
        Returns the mode object with the specified name

        Args:
            name (str): Name of the mode
        """
        try:
            return self.modes[name]
        except:
            return None
        
    def to_dict(self):
        """
        Returns a dictionary representation of the node
        """
        base = {'name':self.name, 'manifest':self.manifest, 'schema':self.schema, 'fields':self.fields, 'meta':self.meta}
        for mode in self.modes:
            base[mode] = self.modes[mode].__dict__
        return base
    
    def __repr__(self) -> str:
        return self.to_dict().__repr__()

class DAG:
    def __init__(self, nodes: List[Node] = None, mode_globals: Dict[str, Any] = None, defaults: Dict[str, Any] = None):
        self.nodes = dict([(node, Node(node, **nodes[node], mode_globals=mode_globals, defaults=defaults)) for node in nodes.keys()])
        distinct_modes = set([mode for node in self.nodes for mode in self.nodes[node].modes])
        for mode in distinct_modes:
            self.detect_cycles(mode)

    def detect_cycles(self, mode:str):
        """
        Detects cycles in the DAG   
        
        Args:
            mode (str): Mode to detect cycles in
        """
        # Use DFS to detect cycles

        # Create a dictionary of nodes and their dependencies
        dependencies = {}
        for node in self.nodes:
            with suppress(AttributeError):
                dependencies[node] = self.nodes[node].get_mode(mode).depends_on

        # Create a dictionary of nodes and their visited status
        visited = {}
        for node in self.nodes:
            visited[node] = False

        # Create a dictionary of nodes and their recursion status
        recursion = {}
        for node in self.nodes:
            recursion[node] = False

        # Create a list of nodes that have been visited
        def dfs(node):
            visited[node] = True
            recursion[node] = True
            if node in dependencies:
                for neighbor in dependencies[node]:
                    if not visited[neighbor]:
                        dfs(neighbor)
                    elif recursion[neighbor]:
                        raise Exception(f'Cycle detected: {node} -> {neighbor}')
            recursion[node] = False

        # Run DFS on all nodes
        for node in self.nodes:
            if not visited[node]:
                dfs(node)
        return True

    def infer_dag(self, mode:str, compiled:bool = False):
        """
        Infers the DAG in the specified mode from the node dependencies

        Args:
            mode (str): Mode to infer the DAG in
            compiled (bool, optional): Whether or not the DAG is compiled. Defaults to False.
        """
        # Get nodes in order of execution
        # During compilation, the DAG should show files that will be created
        queue = []
        # Root nodes are nodes that require no dependencies for the given mode (No attribute depends_on or depends_on is empty)
        for node in self.nodes:
            if not hasattr(self.nodes[node].get_mode(mode),'depends_on') or self.nodes[node].get_mode(mode).depends_on == []:
                queue.append(node)
        while set(queue) != set(self.nodes.keys()):
            # Add nodes that have all dependencies met
            for node in self.nodes:
                if node not in queue:
                    if hasattr(self.nodes[node].get_mode(mode),'depends_on'):
                        if set(self.nodes[node].get_mode(mode).depends_on).issubset(set(queue)):
                            queue.append(node)

        # A dependency is required if the node has a script or query
        # Only keep nodes that have a script or query
        # Validate all necessary dependencies are met for each node
        queue = [node for node in queue if hasattr(self.nodes[node].get_mode(mode),'script') or hasattr(self.nodes[node].get_mode(mode),'query')]
        return queue

    def get_node(self, name: str) -> Node:
        return self.nodes[name]
    
    def compile(self, mode:str, compile_path:str, overrides:Dict[str, Any] = None, connection:Any = None, **kwargs):
        download_dir = kwargs.get('download_dir', './data/Unknown/')
        """
        Compiles the script or query for each node in the DAG in the specified mode

        Args:
            mode (str): Mode to compile the DAG in
            compile_path (str): Path to the compiled DAG
            overrides (Dict[str, Any], optional): Arguments to override the defaults. Defaults to None.
            connection (Any, optional): Connection to use for the pipeline. Defaults to None.
        """
        # print(f'Compiling DAG in {mode} mode...')
        outputs = {}
        for node in self.infer_dag(mode):
            if mode in self.nodes[node].modes.keys():
                schema = "public" if not hasattr(self.nodes[node],'schema') else self.nodes[node].schema
                context = self.as_dict()
                context.update(outputs)
                self.nodes[node].modes[mode].compile(node, compile_path, overrides,schema=schema, context=context,connection=connection)
                if 'outputs' in self.nodes[node].modes[mode].__dict__ and self.nodes[node].modes[mode].outputs is not None:
                    # Run the script or query
                    try:
                         connection.test()
                    except:
                        raise Exception(f'Connection failed for node {node}. Active connection is required for compilation.')
                    rez = self.nodes[node].modes[mode].execute(node=node, connection=connection, context=context, download_dir=download_dir)
                    for output in self.nodes[node].modes[mode].outputs:
                        if 'store_results' in self.nodes[node].modes[mode].__dict__ and self.nodes[node].modes[mode].store_results:
                            outputs[output] = rez[output].to_list()
                            
    def execute(self, mode:str,start:str = None,tables:List=None, args: List[str] = None, connection:Any = None, download_dir:str='./data/Unknown/', kwargs: Dict[str, Any] = None):
        """
        Executes the DAG in the specified mode

        Args:
            mode (str): Mode to execute the DAG in
            args (List[str], optional): Arguments to override the defaults. Defaults to None.
            connection (Any, optional): Connection to use for the pipeline. Defaults to None.
            download_dir (str, optional): Path to download data to. Defaults to './data/Unknown/'.

        Raises:
            Exception: If connection is not specified during execution
            Exception: If output already exists in DAG. Please rename output.
        """
        if not connection:
            raise Exception('Connection not specified during execution')
        if start is not None and start not in ['.','all']:
            if start not in self.nodes:
                raise Exception(f'Node {start} not found in DAG')
            if start == '.':
                start = None
            queue = self.infer_dag(mode)
            queue = queue[queue.index(start):]
        else:
            queue = self.infer_dag(mode)
        outputs = {}
        print(f'Executing DAG in {mode} mode')
        if tables is not None:
            queue = [node for node in queue if node in tables]
        for node in queue:
            print(f'\tWorking on {node}...')
            if mode in self.nodes[node].modes.keys():
                rez = self.nodes[node].modes[mode].execute(node=node, connection=connection, context=outputs, download_dir=download_dir)
                if 'outputs' in self.nodes[node].modes[mode].__dict__ and self.nodes[node].modes[mode].outputs is not None:
                    for output in self.nodes[node].modes[mode].outputs:
                        if output in outputs:
                            raise Exception(f'Output {output} already exists in DAG. Please rename output.')
                        if 'store_results' in self.nodes[node].modes[mode].__dict__ and self.nodes[node].modes[mode].store_results:
                            outputs[node] = {output: rez[output].to_list()}
        return None

    def extract_tree_structure(self, mode:str):
        """
        Extracts the tree structure of the DAG in the specified mode

        Args:
            mode (str): Mode to extract the tree structure in
        """
        # Return a dictionary of nodes and their dependencies
        dependencies = {}
        for node in self.nodes:
            with suppress(AttributeError):
                dependencies[node] = self.nodes[node].get_mode(mode).depends_on
        return dependencies

    def describe(self, mode:str):
        """
        Describes the DAG in the specified mode using mermaid syntax

        Args:
            mode (str): Mode to describe the DAG in
        """
        # Print DAG in a human-readable format (mermaid syntax?)
        return Mermaid(self, mode)
    
    def document(self, mode:str):
        dargs = {
            'dag': Mermaid(self, mode),
            # 'deploys': self.infer_dag(mode),
            'nodes': self.nodes,
        }

    def as_dict(self):
        """
        Returns a dictionary representation of the DAG
        """
        return dict([(node, self.nodes[node].to_dict()) for node in self.nodes])

    def __repr__(self):
        return str(self.nodes)
    
class Mermaid:
    """
    Mermaid syntax for DAGs
    
    Example:
        
        stateDiagram-v2
            [*] --> A
            A --> B 
            B --> C
            C --> [*]
    """
    def __init__(self, dag:DAG, mode:str):
        self.tree = dag.extract_tree_structure(mode)   
        self.mermaid = None
        self.write()

    def write(self):
        self.mermaid = 'stateDiagram-v2\n'
        # Dependencies are parents, nodes are children
        for node in self.tree:
            for dependency in self.tree[node]:
                self.mermaid += f'{dependency} --> {node}\n'
        self.mermaid += '\n'
        # Add nodes that have no dependencies (root nodes)
        for node in self.tree:
            if self.tree[node] == []:
                self.mermaid += f'[*] --> {node}\n'
        # Add nodes that have no children (leaf nodes)
        for node in self.tree:
            if node not in [child for parent in self.tree for child in self.tree[parent]]:
                self.mermaid += f'{node} --> [*]\n'
        self.mermaid += '\n'
        # Remove unnecessary whitespace
        self.mermaid = re.sub(r'\n\s*\n', '\n', self.mermaid)

    def __repr__(self):
        return self.mermaid

