import pytest

from logic import (
    INVITE_ALPHABET,
    INVITE_CODE_LENGTH,
    MAX_FLAT_NAME_LENGTH,
    MAX_NAME_LENGTH,
    clean_flat_name,
    clean_invite_code,
    clean_member_name,
    new_invite_code,
)


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


def test_flat_name_is_tidied():
    assert clean_flat_name("  Rua   Augusta 12 ") == "Rua Augusta 12"


def test_empty_flat_name_is_rejected():
    with pytest.raises(ValueError):
        clean_flat_name("")


def test_flat_name_over_max_length_is_rejected():
    with pytest.raises(ValueError):
        clean_flat_name("a" * (MAX_FLAT_NAME_LENGTH + 1))


def test_new_invite_code_uses_only_allowed_characters():
    for _ in range(100):
        code = new_invite_code()
        assert len(code) == INVITE_CODE_LENGTH
        assert all(c in INVITE_ALPHABET for c in code)


def test_invite_code_is_normalised():
    assert clean_invite_code(" k7q x2m ") == "K7QX2M"


@pytest.mark.parametrize("raw", ["", "K7QX2", "K7QX2MM", "K7QX2O", "K7-X2M"])
def test_invalid_invite_codes_are_rejected(raw):
    with pytest.raises(ValueError):
        clean_invite_code(raw)
