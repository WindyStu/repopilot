from click import HelpFormatter


def test_usage_with_arguments():
    formatter = HelpFormatter()
    formatter.write_usage("cli", "[OPTIONS]")
    assert formatter.getvalue() == "Usage: cli [OPTIONS]\n"
