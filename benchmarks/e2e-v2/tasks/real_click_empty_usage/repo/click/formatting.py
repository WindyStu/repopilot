from io import StringIO


class HelpFormatter:
    def __init__(self, width=80):
        self.width = width
        self.current_indent = 0
        self.buffer = StringIO()

    def write(self, value):
        self.buffer.write(value)

    def getvalue(self):
        return self.buffer.getvalue()

    def write_usage(self, prog, args="", prefix=None):
        if prefix is None:
            prefix = "Usage: "
        usage_prefix = f"{prefix:>{self.current_indent}}{prog} "
        if not args:
            self.write("\n")
            return
        self.write(f"{usage_prefix}{args}\n")
