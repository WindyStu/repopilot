class SourceAwareType:
    def convert(self, value, param, ctx):
        return value, ctx.get_parameter_source(param.name)
