import os

def find_root(landmark: str = 'project.yaml') -> str:
    """
    Find the root directory of a project.
    """
    root = os.getcwd()
    while True:
        if os.path.exists(os.path.join(root, landmark)):
            return root
        else:
            root = os.path.dirname(root)
            # Test if we have reached the root of the drive
            if root == os.path.dirname(root):
                raise FileNotFoundError(f'Could not identify the project root. Please ensure that {landmark} exists in the project root.')
    return None

try:
    __project_root__ = find_root()
except FileNotFoundError:
    __project_root__ = None

def ensure_rooting(path) -> str:
    """
    Ensure that the path is rooted to the project.
    """
    if os.path.isabs(path) and path.startswith(__project_root__):
        return path
    else:
        return os.path.normpath(os.path.join(__project_root__, path))

def unroot(path) -> str:
    """
    Ensure that the path is unrooted from the project.
    """
    if os.path.isabs(path) and path.startswith(__project_root__):
        return str(os.path.relpath(path, __project_root__)).replace('\\', '/')
    else:
        return path
