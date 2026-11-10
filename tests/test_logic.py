import pytest

from logic import MAX_NAME_LENGTH, clean_member_name


def test_name_is_tidied():
    assert clean_member_name("  Eline   Hogh ") == "Eline Hogh"


def test_empty_name_is_rejected():
    with pytest.raises(ValueError):
        clean_member_name("   ")


def test_name_at_max_length_is_accepted():
    assert clean_member_name("a" * MAX_NAME_LENGTH) == "a" * MAX_NAME_LENGTH


def test_name_over_max_length_is_rejected():
    with pytest.raises(ValueError):
        clean_member_name("a" * (MAX_NAME_LENGTH + 1))
