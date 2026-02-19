import os

from dartfx.ddi import ddicodebook


def data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def test_load_codebook():
    cb_path = os.path.join(data_dir(), "codebook/NES1948.xml")
    cb = ddicodebook.loadxml(cb_path)

    assert cb is not None
    assert getattr(cb, "stdyDscr", None) is not None

    # helper methods
    assert len(cb.search_variables()) == 67
    assert cb.get_title() is not None
