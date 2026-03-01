from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pythaw.checker import check
from pythaw.config import Config


def _make_files(base: Path, files: dict[str, str]) -> None:
    """Create files under *base* with the given content."""
    for name, content in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


HANDLER_SRC = "def handler(event, context):\n    pass\n"


# ---------------------------------------------------------------------------
# Handler extraction (tested via check)
# ---------------------------------------------------------------------------


class TestHandlerPatternMatching:
    """Verify handler discovery with fnmatch pattern matching."""

    @pytest.mark.parametrize(
        ("func_name", "should_match"),
        [
            ("handler", True),
            ("my_handler", True),
            ("process_data", False),
        ],
    )
    def test_default_pattern_matching(
        self, tmp_path: Path, func_name: str, *, should_match: bool
    ) -> None:
        """Default patterns match 'handler' and '*_handler' but not arbitrary names."""
        source = (
            f'import boto3\ndef {func_name}(event, context):\n    boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        if should_match:
            assert len(violations) == 1
        else:
            assert violations == []

    def test_custom_handler_patterns(self, tmp_path: Path) -> None:
        """Uses handler_patterns from config instead of defaults."""
        source = "import boto3\ndef my_entry(event, context):\n    boto3.client('s3')\n"
        _make_files(tmp_path, {"app.py": source})
        cfg = Config(handler_patterns=("my_entry",))
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, cfg)
        assert len(violations) == 1

    def test_only_checks_top_level_functions(self, tmp_path: Path) -> None:
        """Nested functions and class methods are not detected as handlers."""
        source = (
            "import boto3\n"
            "class MyClass:\n"
            "    def handler(self):\n"
            "        boto3.client('s3')\n"
            "\n"
            "def outer():\n"
            "    def handler():\n"
            "        boto3.client('s3')\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_multiple_handlers_in_one_file(self, tmp_path: Path) -> None:
        """Multiple matching functions in a single file are all checked."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            "    boto3.client('s3')\n"
            "\n"
            "def lambda_handler(event, context):\n"
            "    boto3.resource('s3')\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        codes = sorted(v.code for v in violations)
        assert codes == ["PW001", "PW002"]

    def test_async_handler(self, tmp_path: Path) -> None:
        """Async handler functions are also detected."""
        source = (
            "import boto3\nasync def handler(event, context):\n    boto3.client('s3')\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1

    def test_single_file_path(self, tmp_path: Path) -> None:
        """A single file path is checked directly for handlers."""
        py = tmp_path / "app.py"
        py.write_text(
            "import boto3\ndef handler(event, context):\n    boto3.client('s3')\n"
        )
        violations = check(py, Config())
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# Violation detection
# ---------------------------------------------------------------------------


class TestCheckDirectViolations:
    """Verify detection of rule violations directly inside handler functions."""

    @pytest.mark.parametrize(
        ("call", "code"),
        [
            ('boto3.client("s3")', "PW001"),
            ('boto3.resource("s3")', "PW002"),
            ("boto3.Session()", "PW003"),
        ],
        ids=["PW001", "PW002", "PW003"],
    )
    def test_detects_violation(self, tmp_path: Path, call: str, code: str) -> None:
        """Each built-in rule detects its corresponding boto3 call in a handler."""
        source = f"def handler(event, context):\n    {call}\n"
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].code == code

    def test_no_violation_at_module_scope(self, tmp_path: Path) -> None:
        """Calls at module scope (outside handler) are not flagged."""
        source = (
            "import boto3\n"
            "\n"
            'client = boto3.client("s3")\n'
            "\n"
            "def handler(event, context):\n"
            "    return client.get_object(Bucket='b', Key='k')\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_multiple_violations_in_one_handler(self, tmp_path: Path) -> None:
        """Multiple violating calls in a single handler are all reported."""
        source = (
            "import boto3\n"
            "\n"
            "def handler(event, context):\n"
            '    client = boto3.client("s3")\n'
            '    resource = boto3.resource("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        codes = sorted(v.code for v in violations)
        assert codes == ["PW001", "PW002"]

    def test_violation_in_nested_function(self, tmp_path: Path) -> None:
        """Calls inside a nested function within a handler are detected."""
        source = (
            "import boto3\n"
            "\n"
            "def handler(event, context):\n"
            "    def helper():\n"
            '        boto3.client("s3")\n'
            "    helper()\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].code == "PW001"


class TestCheckPositionInfo:
    """Verify that violations carry correct file, line, and column info."""

    def test_correct_position(self, tmp_path: Path) -> None:
        """Violation points to the exact call location with a relative path."""
        source = (
            "import boto3\n"
            "\n"
            "def handler(event, context):\n"
            '    client = boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        v = violations[0]
        assert not Path(v.file).is_absolute()
        assert v.line == 4
        assert v.col == 13


class TestSelectIgnoreFiltering:
    """Verify select/ignore rule filtering in check()."""

    def test_select_filters_rules(self, tmp_path: Path) -> None:
        """Only rules in the select set are applied."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
            '    boto3.resource("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config(), select=frozenset({"PW001"}))
        assert len(violations) == 1
        assert violations[0].code == "PW001"

    def test_ignore_excludes_rules(self, tmp_path: Path) -> None:
        """Rules in the ignore set are excluded."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
            '    boto3.resource("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config(), ignore=frozenset({"PW001"}))
        codes = [v.code for v in violations]
        assert "PW001" not in codes
        assert "PW002" in codes

    def test_select_and_ignore_combined(self, tmp_path: Path) -> None:
        """Select narrows first, then ignore removes from that set."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
            '    boto3.resource("s3")\n'
            "    boto3.Session()\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(
                tmp_path,
                Config(),
                select=frozenset({"PW001", "PW002"}),
                ignore=frozenset({"PW002"}),
            )
        assert len(violations) == 1
        assert violations[0].code == "PW001"

    def test_empty_select_runs_all_rules(self, tmp_path: Path) -> None:
        """Empty select set means all rules are active (default behaviour)."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
            '    boto3.resource("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config(), select=frozenset())
        assert len(violations) == 2


class TestInlineSuppression:
    """Verify inline suppression with '# nopw: PWXXX' comments."""

    def test_nopw_suppresses_single_rule(self, tmp_path: Path) -> None:
        """A '# nopw: PW001' comment suppresses that rule on the same line."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")  # nopw: PW001\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_nopw_suppresses_only_specified_rule(self, tmp_path: Path) -> None:
        """Other rules on the same line are still reported."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")  # nopw: PW002\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].code == "PW001"

    def test_nopw_multiple_codes(self, tmp_path: Path) -> None:
        """Comma-separated codes suppress multiple rules on one line."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")  # nopw: PW001, PW002\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_nopw_does_not_affect_other_lines(self, tmp_path: Path) -> None:
        """Suppression only applies to the line where the comment appears."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")  # nopw: PW001\n'
            '    boto3.client("dynamodb")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].line == 4


class TestFileLevelSuppression:
    """Verify file-level suppression with '# pythaw: nocheck' comment."""

    def test_nocheck_skips_entire_file(self, tmp_path: Path) -> None:
        """A file starting with '# pythaw: nocheck' is completely skipped."""
        source = (
            "# pythaw: nocheck\n"
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_nocheck_after_shebang_and_encoding(self, tmp_path: Path) -> None:
        """'# pythaw: nocheck' after shebang/encoding comments is still recognised."""
        source = (
            "#!/usr/bin/env python3\n"
            "# -*- coding: utf-8 -*-\n"
            "# pythaw: nocheck\n"
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_nocheck_after_code_is_ignored(self, tmp_path: Path) -> None:
        """'# pythaw: nocheck' after a code line has no effect."""
        source = (
            "import boto3\n"
            "# pythaw: nocheck\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1

    def test_nocheck_does_not_affect_other_files(self, tmp_path: Path) -> None:
        """Other files in the same directory are still checked."""
        _make_files(
            tmp_path,
            {
                "skip.py": (
                    "# pythaw: nocheck\n"
                    "import boto3\n"
                    "def handler(event, context):\n"
                    '    boto3.client("s3")\n'
                ),
                "check.py": (
                    "import boto3\n"
                    "def handler(event, context):\n"
                    '    boto3.client("s3")\n'
                ),
            },
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert "check.py" in violations[0].file


class TestPerFileIgnores:
    """Verify per-file-ignores config option."""

    def test_ignores_rule_for_matching_file(self, tmp_path: Path) -> None:
        """Files matching the glob pattern have the specified rules ignored."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
            '    boto3.resource("s3")\n'
        )
        _make_files(tmp_path, {"tests/test_app.py": source})
        cfg = Config(per_file_ignores=(("tests/*", ("PW001",)),))
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, cfg)
        codes = [v.code for v in violations]
        assert "PW001" not in codes
        assert "PW002" in codes

    def test_no_effect_on_non_matching_file(self, tmp_path: Path) -> None:
        """Files that do not match the glob pattern are checked normally."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"src/app.py": source})
        cfg = Config(per_file_ignores=(("tests/*", ("PW001",)),))
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, cfg)
        assert len(violations) == 1
        assert violations[0].code == "PW001"

    def test_multiple_patterns(self, tmp_path: Path) -> None:
        """Multiple per-file-ignores entries are all applied."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
            '    boto3.resource("s3")\n'
        )
        _make_files(tmp_path, {"tests/test_app.py": source})
        cfg = Config(
            per_file_ignores=(
                ("tests/*", ("PW001",)),
                ("tests/*", ("PW002",)),
            ),
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, cfg)
        assert violations == []

    def test_empty_per_file_ignores(self, tmp_path: Path) -> None:
        """Empty per_file_ignores has no effect."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        cfg = Config(per_file_ignores=())
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, cfg)
        assert len(violations) == 1


class TestCallChainResolution:
    """Verify call graph traversal and call_chain population."""

    def test_same_file_function_call(self, tmp_path: Path) -> None:
        """A helper function in the same file is followed and violations reported."""
        source = (
            "import boto3\n"
            "\n"
            "def helper():\n"
            '    boto3.client("s3")\n'
            "\n"
            "def handler(event, context):\n"
            "    helper()\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        v = violations[0]
        assert v.code == "PW001"
        assert v.line == 4
        assert len(v.call_chain) == 1
        assert v.call_chain[0].name == "helper()"

    def test_cross_file_import_resolution(self, tmp_path: Path) -> None:
        """A function imported from another local file is followed."""
        _make_files(
            tmp_path,
            {
                "infra.py": (
                    "import boto3\n"
                    "\n"
                    "def get_client():\n"
                    '    return boto3.client("s3")\n'
                ),
                "app.py": (
                    "from infra import get_client\n"
                    "\n"
                    "def handler(event, context):\n"
                    "    get_client()\n"
                ),
            },
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        v = violations[0]
        assert v.code == "PW001"
        assert "infra.py" in v.file
        assert len(v.call_chain) == 1
        assert v.call_chain[0].name == "get_client()"

    def test_module_attribute_call(self, tmp_path: Path) -> None:
        """A call via module.func() resolves across files."""
        _make_files(
            tmp_path,
            {
                "infra.py": (
                    "import boto3\n"
                    "\n"
                    "def get_client():\n"
                    '    return boto3.client("s3")\n'
                ),
                "app.py": (
                    "import infra\n"
                    "\n"
                    "def handler(event, context):\n"
                    "    infra.get_client()\n"
                ),
            },
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        v = violations[0]
        assert v.code == "PW001"
        assert len(v.call_chain) == 1
        assert v.call_chain[0].name == "infra.get_client()"

    def test_multi_level_chain(self, tmp_path: Path) -> None:
        """Call chains across multiple functions are tracked."""
        source = (
            "import boto3\n"
            "\n"
            "def level2():\n"
            '    boto3.client("s3")\n'
            "\n"
            "def level1():\n"
            "    level2()\n"
            "\n"
            "def handler(event, context):\n"
            "    level1()\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        v = violations[0]
        assert v.code == "PW001"
        assert len(v.call_chain) == 2
        assert v.call_chain[0].name == "level1()"
        assert v.call_chain[1].name == "level2()"

    def test_circular_call_does_not_loop(self, tmp_path: Path) -> None:
        """Circular function calls are handled without infinite recursion."""
        source = (
            "def foo():\n"
            "    bar()\n"
            "\n"
            "def bar():\n"
            "    foo()\n"
            "\n"
            "def handler(event, context):\n"
            "    foo()\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_class_init_is_followed(self, tmp_path: Path) -> None:
        """Class instantiation follows __init__ for violations."""
        source = (
            "import boto3\n"
            "\n"
            "class Client:\n"
            "    def __init__(self):\n"
            '        self.c = boto3.client("s3")\n'
            "\n"
            "def handler(event, context):\n"
            "    Client()\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        v = violations[0]
        assert v.code == "PW001"
        assert len(v.call_chain) == 1
        assert v.call_chain[0].name == "Client()"

    def test_direct_violation_has_empty_chain(self, tmp_path: Path) -> None:
        """Direct violations in the handler have an empty call_chain."""
        source = 'import boto3\ndef handler(event, context):\n    boto3.client("s3")\n'
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].call_chain == ()

    def test_unresolvable_call_is_skipped(self, tmp_path: Path) -> None:
        """Calls to stdlib/third-party functions are silently skipped."""
        source = (
            "import json\n"
            "def handler(event, context):\n"
            "    json.loads('{}')\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []


class TestCheckEdgeCases:
    """Verify edge cases for the checker."""

    def test_skips_syntax_error_files(self, tmp_path: Path) -> None:
        """Files with syntax errors are skipped without raising."""
        _make_files(
            tmp_path,
            {
                "good.py": (
                    "import boto3\n"
                    "def handler(event, context):\n"
                    '    boto3.client("s3")\n'
                ),
                "bad.py": "def handler(event, context\n",
            },
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert not Path(violations[0].file).is_absolute()
