from click.types import String


class Argument:
    def __init__(self, name, type=None, required=True, nargs=1, deprecated=False):
        self.name = name
        self.type = type or String()
        self.required = required
        self.nargs = nargs
        self.deprecated = deprecated
        self.metavar = None

    def make_metavar(self, ctx=None):
        if self.metavar is not None:
            return self.metavar
        var = self.type.get_metavar(param=self, ctx=ctx)
        if not var:
            var = self.name.upper()
        if self.deprecated:
            var += "!"
        if not self.required:
            var = f"[{var}]"
        if self.nargs != 1:
            var += "..."
        return var
