import io

import pytest

from wizdantic.console import WizardConsole


class TestWizardConsoleInput:
    @pytest.fixture
    def console(self):
        return WizardConsole(file=io.StringIO(), force_terminal=True)

    def test_normal_input(self, mocker, console):
        """Normal (non-password, no stream) input delegates to prompt_toolkit."""
        mocker.patch.object(console.prompt_session, "prompt", return_value="hello")
        result = console.input("Enter: ", markup=False)
        assert result == "hello"
        console.prompt_session.prompt.assert_called_once_with("")

    def test_password_input(self, mocker, console):
        """Password input delegates to getpass."""
        mock_getpass = mocker.patch("wizdantic.console.getpass", return_value="secret")
        result = console.input("Pass: ", password=True, markup=False)
        assert result == "secret"
        mock_getpass.assert_called_once_with("", stream=None)

    def test_stream_input(self, console):
        """When a stream is provided, input reads a line from it."""
        stream = io.StringIO("from stream\n")
        result = console.input("Read: ", stream=stream, markup=False)
        assert result == "from stream\n"

    def test_empty_prompt(self, mocker, console):
        """An empty prompt skips printing and still reads input."""
        mocker.patch.object(console.prompt_session, "prompt", return_value="value")
        result = console.input("", markup=False)
        assert result == "value"

    def test_password_with_stream(self, mocker, console):
        """Password takes priority over stream when both are provided."""
        stream = io.StringIO("ignored\n")
        mock_getpass = mocker.patch("wizdantic.console.getpass", return_value="secret")
        result = console.input("Pass: ", password=True, stream=stream, markup=False)
        assert result == "secret"
        mock_getpass.assert_called_once_with("", stream=stream)
