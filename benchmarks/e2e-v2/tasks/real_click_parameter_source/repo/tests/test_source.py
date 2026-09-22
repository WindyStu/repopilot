from click import Context, Parameter, ParameterSource, SourceAwareType


def test_final_source_is_recorded():
    context = Context()
    parameter = Parameter("path", SourceAwareType())
    parameter.handle_parse_result(context, "file", ParameterSource.COMMANDLINE)
    assert context.get_parameter_source("path") is ParameterSource.COMMANDLINE
