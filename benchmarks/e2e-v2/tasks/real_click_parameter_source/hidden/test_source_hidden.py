from click import Context, Parameter, ParameterSource, SourceAwareType


def test_converter_observes_commandline_source():
    context = Context()
    parameter = Parameter("path", SourceAwareType())
    value, source = parameter.handle_parse_result(
        context, "cli.txt", ParameterSource.COMMANDLINE
    )
    assert value == "cli.txt"
    assert source is ParameterSource.COMMANDLINE


def test_converter_observes_default_source():
    context = Context()
    parameter = Parameter("path", SourceAwareType())
    value, source = parameter.handle_parse_result(
        context, "default.txt", ParameterSource.DEFAULT
    )
    assert value == "default.txt"
    assert source is ParameterSource.DEFAULT


def test_eager_callback_observes_source_during_processing():
    observed = []

    def callback(ctx, param, value):
        observed.append(ctx.get_parameter_source(param.name))
        return value

    context = Context()
    parameter = Parameter("debug", SourceAwareType(), callback=callback)
    parameter.handle_parse_result(context, True, ParameterSource.ENVIRONMENT)
    assert observed == [ParameterSource.ENVIRONMENT]
