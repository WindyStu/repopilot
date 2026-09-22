from more_itertools import interleave_evenly


def test_two_inputs_preserve_all_values():
    assert list(interleave_evenly([[1, 3], [2, 4]], lengths=[2, 2])) == [1, 2, 3, 4]
