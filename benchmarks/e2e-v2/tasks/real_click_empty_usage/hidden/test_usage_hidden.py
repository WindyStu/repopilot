from click import HelpFormatter


def test_empty_args_preserve_default_prefix_and_program():
    formatter = HelpFormatter()
    formatter.write_usage("Program")
    assert formatter.getvalue() == "Usage: Program\n"


def test_empty_args_preserve_custom_prefix():
    formatter = HelpFormatter()
    formatter.write_usage("Program", prefix="Run: ")
    assert formatter.getvalue() == "Run: Program\n"


def test_empty_args_do_not_leave_trailing_space():
    formatter = HelpFormatter(width=20)
    formatter.write_usage("VeryLongProgramName")
    assert formatter.getvalue() == "Usage: VeryLongProgramName\n"
