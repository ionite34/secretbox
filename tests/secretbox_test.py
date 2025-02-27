"""Unit tests against secretbox.py"""
import os
from typing import Any
from typing import Generator
from unittest.mock import patch

import pytest
from secretbox import EnvFileLoader
from secretbox import EnvironLoader
from secretbox import SecretBox

from tests.conftest import ENV_FILE_EXPECTED


@pytest.fixture
def secretbox() -> Generator[SecretBox, None, None]:
    """Default instance of LoadEnv"""
    secrets = SecretBox()
    assert not secrets.values
    yield secrets


def test_load_from_with_unknown(secretbox: SecretBox, mock_env_file: str) -> None:
    """Load secrets, throw an unknown loader in to ensure clean fall-through"""
    assert not secretbox.values
    secretbox.load_from(["envfile", "unknown"], filename=mock_env_file)
    assert secretbox.values


def test_load_order_file_over_environ(secretbox: SecretBox, mock_env_file: str) -> None:
    """Loaded file should override existing environ values"""
    altered_expected = {key: f"{value} ALT" for key, value in ENV_FILE_EXPECTED.items()}
    with patch.dict(os.environ, altered_expected):
        secretbox.use_loaders(EnvironLoader(), EnvFileLoader(mock_env_file))
        for key, value in ENV_FILE_EXPECTED.items():
            assert secretbox.get(key) == value, f"Expected: {key}, {value}"


def test_load_order_environ_over_file(secretbox: SecretBox, mock_env_file: str) -> None:
    """Loaded environ should override file values"""
    altered_expected = {key: f"{value} ALT" for key, value in ENV_FILE_EXPECTED.items()}
    with patch.dict(os.environ, altered_expected):
        secretbox.load_from(["envfile", "environ"], filename=mock_env_file)
        for key, value in ENV_FILE_EXPECTED.items():
            assert secretbox.get(key) == f"{value} ALT", f"Expected: {key}, {value} ALT"


def test_update_loaded_values(secretbox: SecretBox) -> None:
    """Ensure we are updating state correctly"""
    secretbox._update_loaded_values({"TEST": "TEST01"})
    assert secretbox.get("TEST") == "TEST01"

    secretbox._update_loaded_values({"TEST": "TEST02"})
    assert secretbox.get("TEST") == "TEST02"


def test_auto_load_flag() -> None:
    with patch.object(SecretBox, "load_from") as mocked_load_from:
        SecretBox(auto_load=True)

        mocked_load_from.assert_called_once()


def test_get_missing_key_is_empty(secretbox: SecretBox) -> None:
    """Missing key? Check behind the milk"""
    with pytest.raises(KeyError):
        secretbox.get("BYWHATCHANCEWOULDTHISSEXIST")


def test_get_default_missing_key(secretbox: SecretBox) -> None:
    """Missing key? Return the provided default instead"""
    assert secretbox.get("BYWHATCHANCEWOULDTHISSEXIST", "Hello") == "Hello"


def test_get_as_valid_int(secretbox: SecretBox) -> None:
    """Helper to return ints"""
    with patch.dict(os.environ, {"TEST_INT": "42"}):
        secretbox.load_from(["environ"])
        assert secretbox.get_int("TEST_INT") == 42
        assert secretbox.get_int("TEST_INT", 0) == 42


def test_get_as_invalid_int(secretbox: SecretBox) -> None:
    """Helper to return ints should raise on assumption that value is an int"""
    with patch.dict(os.environ, {"TEST_INT": "Forty-two"}):
        secretbox.load_from(["environ"])
        with pytest.raises(ValueError):
            secretbox.get_int("TEST_INT", -1)


def test_get_default_int(secretbox: SecretBox) -> None:
    """Return the default if provided instead of raising"""
    assert secretbox.get_int("NOTTHERE", 10) == 10


def test_get_as_list(secretbox: SecretBox) -> None:
    """Helper to return a list based on given delimiter"""
    with patch.dict(os.environ, {"TEST_STR": "rooBlank", "TEST_LIST": "1 | 2|3"}):
        secretbox.load_from(["environ"])
        assert secretbox.get_list("TEST_LIST") == ["1 | 2|3"]
        assert secretbox.get_list("TEST_STR", "|") == ["rooBlank"]
        assert secretbox.get_list("TEST_LIST", "|") == ["1 ", " 2", "3"]


def test_get_as_list_default(secretbox: SecretBox) -> None:
    """Return the default if provided instead of raising"""
    assert secretbox.get_list("NOTTHERE", ",", ["1", "2", "3"]) == ["1", "2", "3"]


def test_load_debug_flag(caplog: Any) -> None:
    """Ensure logging is silentish"""
    _ = SecretBox()
    assert "Debug flag passed." not in caplog.text

    _ = SecretBox(debug_flag=True)
    assert "Debug flag passed." in caplog.text


def test_set(secretbox: SecretBox) -> None:
    """Set a value"""
    secretbox.set("TEST", "TEST")
    assert secretbox.get("TEST") == "TEST"
    assert os.getenv("TEST") == "TEST"


def test_set_converts_to_str(secretbox: SecretBox) -> None:
    """Set a value"""
    secretbox.set("TEST", 42)  # type: ignore
    assert secretbox.get("TEST") == "42"
    assert os.getenv("TEST") == "42"
