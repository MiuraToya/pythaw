from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from pythaw.checker import check
from pythaw.config import Config, ConfigError

if TYPE_CHECKING:
    from pythaw.violation import Violation


class PythawLanguageServer(LanguageServer):
    """LSP server for pythaw static analysis."""


def create_server() -> PythawLanguageServer:
    """Create and configure a PythawLanguageServer instance."""
    server = PythawLanguageServer(
        name="pythaw",
        version="0.2.2",
    )

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(
        ls: PythawLanguageServer,
        params: types.DidOpenTextDocumentParams,
    ) -> None:
        _validate(ls, params.text_document.uri)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE)
    def did_save(
        ls: PythawLanguageServer,
        params: types.DidSaveTextDocumentParams,
    ) -> None:
        _validate(ls, params.text_document.uri)

    return server


def _validate(ls: PythawLanguageServer, uri: str) -> None:
    """Run pythaw check on the file and publish diagnostics."""
    path = _uri_to_path(uri)
    if path.suffix != ".py":
        return

    try:
        config = Config.load()
    except ConfigError:
        config = Config()

    violations = check(path, config)
    diagnostics = [_violation_to_diagnostic(v) for v in violations]
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=uri,
            diagnostics=diagnostics,
        )
    )


def _uri_to_path(uri: str) -> Path:
    """Convert a file URI to a local filesystem Path."""
    parsed = urlparse(uri)
    return Path(unquote(parsed.path))


def _violation_to_diagnostic(violation: Violation) -> types.Diagnostic:
    """Convert a pythaw Violation to an LSP Diagnostic."""
    line = violation.line - 1  # 1-indexed -> 0-indexed

    related_information: list[types.DiagnosticRelatedInformation] | None = None
    if violation.call_chain:
        related_information = [
            types.DiagnosticRelatedInformation(
                location=types.Location(
                    uri=Path(site.file).resolve().as_uri(),
                    range=types.Range(
                        start=types.Position(
                            line=site.line - 1, character=site.col
                        ),
                        end=types.Position(
                            line=site.line - 1, character=site.col
                        ),
                    ),
                ),
                message=f"called via {site.name}",
            )
            for site in violation.call_chain
        ]

    return types.Diagnostic(
        range=types.Range(
            start=types.Position(line=line, character=violation.col),
            end=types.Position(line=line, character=violation.col),
        ),
        message=violation.message,
        severity=types.DiagnosticSeverity.Warning,
        code=violation.code,
        source="pythaw",
        related_information=related_information,
    )
