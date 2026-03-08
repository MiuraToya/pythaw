from __future__ import annotations

from pathlib import Path

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from pythaw.cli import _build_parser
from pythaw.lsp import (
    _uri_to_path,
    _violation_to_diagnostic,
    create_server,
)
from pythaw.violation import CallSite, Violation


class TestCreateServer:
    """Verify LSP server factory function."""

    def test_returns_language_server_instance(self) -> None:
        """create_server() returns a LanguageServer."""
        server = create_server()
        assert isinstance(server, LanguageServer)

    def test_server_name(self) -> None:
        """Server name is 'pythaw'."""
        server = create_server()
        assert server.name == "pythaw"


class TestViolationToDiagnostic:
    """Verify Violation to LSP Diagnostic conversion."""

    def test_basic_fields(self) -> None:
        """Converts code, message, source, and severity correctly."""
        violation = Violation(
            file="app.py",
            line=3,
            col=4,
            code="PW001",
            message="boto3.client() creates a new connection",
        )
        diag = _violation_to_diagnostic(violation)

        assert diag.message == "boto3.client() creates a new connection"
        assert diag.code == "PW001"
        assert diag.source == "pythaw"
        assert diag.severity == types.DiagnosticSeverity.Warning

    def test_line_number_1_indexed_to_0_indexed(self) -> None:
        """Converts 1-indexed line/col to 0-indexed LSP Position."""
        violation = Violation(
            file="app.py", line=10, col=5, code="PW001", message="test"
        )
        diag = _violation_to_diagnostic(violation)

        assert diag.range.start.line == 9
        assert diag.range.start.character == 5
        assert diag.range.end.line == 9
        assert diag.range.end.character == 5

    def test_no_call_chain_means_no_related_information(self) -> None:
        """related_information is None when call_chain is empty."""
        violation = Violation(
            file="app.py", line=1, col=0, code="PW001", message="test"
        )
        diag = _violation_to_diagnostic(violation)

        assert diag.related_information is None

    def test_call_chain_converted_to_related_information(self) -> None:
        """call_chain entries become DiagnosticRelatedInformation."""
        violation = Violation(
            file="app.py",
            line=5,
            col=4,
            code="PW001",
            message="test",
            call_chain=(CallSite(file="app.py", line=3, col=4, name="helper()"),),
        )
        diag = _violation_to_diagnostic(violation)

        assert diag.related_information is not None
        assert len(diag.related_information) == 1
        info = diag.related_information[0]
        assert info.location.range.start.line == 2  # 3 - 1
        assert "helper()" in info.message

    def test_multiple_call_chain_entries(self) -> None:
        """Multiple call_chain entries produce multiple relatedInformation."""
        violation = Violation(
            file="app.py",
            line=10,
            col=0,
            code="PW001",
            message="test",
            call_chain=(
                CallSite(file="app.py", line=3, col=0, name="foo()"),
                CallSite(file="utils.py", line=7, col=0, name="bar()"),
            ),
        )
        diag = _violation_to_diagnostic(violation)

        assert diag.related_information is not None
        assert len(diag.related_information) == 2


class TestUriToPath:
    """Verify file URI to Path conversion."""

    def test_file_uri(self) -> None:
        """Converts file:///path/to/file.py to a Path."""
        path = _uri_to_path("file:///path/to/file.py")
        assert path == Path("/path/to/file.py")

    def test_percent_encoded_uri(self) -> None:
        """Decodes percent-encoded characters."""
        path = _uri_to_path("file:///path/to/my%20file.py")
        assert path == Path("/path/to/my file.py")


class TestLspSubcommand:
    """Verify CLI 'lsp' subcommand registration."""

    def test_parser_recognizes_lsp(self) -> None:
        """The argument parser accepts 'lsp' and sets func."""
        parser = _build_parser()
        args = parser.parse_args(["lsp"])
        assert hasattr(args, "func")
