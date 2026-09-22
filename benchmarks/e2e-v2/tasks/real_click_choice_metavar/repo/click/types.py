class String:
    def get_metavar(self, param, ctx):
        return None


class Choice:
    def __init__(self, choices):
        self.choices = choices

    def get_metavar(self, param, ctx):
        return f"[{'|'.join(self.choices)}]"


class DateTime:
    def __init__(self, formats):
        self.formats = formats

    def get_metavar(self, param, ctx):
        return f"[{'|'.join(self.formats)}]"
