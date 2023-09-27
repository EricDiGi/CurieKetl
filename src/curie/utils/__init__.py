import os

class PersistentMemory(list):
    def __init__(self, *args, **kwargs):
        if 'DEPLOYMENT_FILE_PATHS' not in os.environ:
            os.environ['DEPLOYMENT_FILE_PATHS'] = ''
        self.load()
        # super().__init__(*args, **kwargs)

    def append(self, *args, **kwargs):
        super().append(*args, **kwargs)
        self.save()

    def save(self):
        os.environ['DEPLOYMENT_FILE_PATHS'] = ','.join(self)

    def load(self):
        self.clear()
        self.extend(os.environ['DEPLOYMENT_FILE_PATHS'].split(','))

    def __str__(self):
        return super().__str__() 
    
    def __repr__(self):
        return super().__repr__()

deployment_file_paths = PersistentMemory()