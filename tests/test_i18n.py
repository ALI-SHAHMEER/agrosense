import sys
import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_tr_returns_english_by_default():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    assert lm.tr("nav_dashboard") == "🏠  Dashboard"


def test_tr_returns_urdu_after_toggle():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
    assert lm.tr("nav_dashboard") == "🏠  ڈیش بورڈ"


def test_tr_returns_key_for_unknown_key():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    assert lm.tr("nonexistent_key_xyz") == "nonexistent_key_xyz"


def test_is_urdu_false_by_default():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    assert lm.is_urdu() is False


def test_toggle_twice_returns_to_english():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
        lm.toggle()
    assert lm.current_lang == "en"
    assert lm.is_urdu() is False


def test_language_changed_signal_fires_on_toggle():
    from desktop.i18n import LanguageManager
    received = []
    lm = LanguageManager()
    lm.language_changed.connect(lambda lang: received.append(lang))
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
    assert received == ["ur"]


def test_all_strings_have_both_languages():
    from desktop.i18n import STRINGS
    for key, val in STRINGS.items():
        assert "en" in val, f"Missing 'en' for key '{key}'"
        assert "ur" in val, f"Missing 'ur' for key '{key}'"


def test_lang_toggle_key_shows_correct_label():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    assert lm.tr("lang_toggle") == "🌐 اردو"
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
    assert lm.tr("lang_toggle") == "🌐 EN"
