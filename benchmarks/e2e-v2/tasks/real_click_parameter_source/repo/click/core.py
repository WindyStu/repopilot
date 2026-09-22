from enum import Enum, auto


class ParameterSource(Enum):
    COMMANDLINE = auto()
    DEFAULT = auto()
    ENVIRONMENT = auto()


class Context:
    def __init__(self):
        self._sources = {}
        self.params = {}

    def set_parameter_source(self, name, source):
        self._sources[name] = source

    def get_parameter_source(self, name):
        return self._sources.get(name)


class Parameter:
    def __init__(self, name, converter, callback=None):
        self.name = name
        self.converter = converter
        self.callback = callback

    def process_value(self, ctx, value):
        value = self.converter.convert(value, self, ctx)
        if self.callback is not None:
            value = self.callback(ctx, self, value)
        return value

    def handle_parse_result(self, ctx, value, source):
        value = self.process_value(ctx, value)
        ctx.set_parameter_source(self.name, source)
        ctx.params[self.name] = value
        return value
