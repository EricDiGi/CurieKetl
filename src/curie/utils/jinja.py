import jinja2
import datetime

# A class to replace undefined variables with the original variable name as jinja ( {{undef_var}} -> {{undef_var}} )
class CurieUndefined(jinja2.Undefined):
    def __init__(self, hint=None, obj=jinja2.runtime.missing, name=None, exc=None):
        super().__init__(hint, obj, name, exc)
        try:
            self._undefined_name = "{{"+name+"}}"
        except:
            print(name)
            self._undefined_name = "{{"+name+"}}"
    def __str__(self):
        return self._undefined_name

class Environment(jinja2.Environment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.funcs = {
            'current_date': lambda format: datetime.datetime.now().strftime(format),
        }
        self.globals.update(self.funcs)
        self.undefined = CurieUndefined