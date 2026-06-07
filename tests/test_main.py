import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main as cli


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def write(directory, name: str, src: str) -> str:
    path = os.path.join(str(directory), name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    return path


# ---------------------------------------------------------------------------
# Successful runs
# ---------------------------------------------------------------------------

class TestRun:
    def test_exit_code_is_main_return_value(self, tmp_path):
        path = write(tmp_path, "p.lang", "int main() { return 7; }\n")
        assert cli.main(["run", path]) == 7

    def test_default_zero_exit(self, tmp_path):
        path = write(tmp_path, "p.lang", "int main() { return 0; }\n")
        assert cli.main(["run", path]) == 0

    def test_print_goes_to_stdout(self, tmp_path, capsys):
        path = write(
            tmp_path, "p.lang",
            'int main() { print("hello"); print(42); return 0; }\n',
        )
        code = cli.main(["run", path])
        out = capsys.readouterr().out
        assert code == 0
        assert out == "hello\n42\n"

    def test_multi_file_program(self, tmp_path, capsys):
        write(tmp_path, "lib.lang", "int square(int x) { return x * x; }\n")
        path = write(
            tmp_path, "main.lang",
            'import "lib.lang";\n'
            "int main() { print(square(5)); return square(5); }\n",
        )
        code = cli.main(["run", path])
        assert code == 25
        assert capsys.readouterr().out == "25\n"


# ---------------------------------------------------------------------------
# Usage errors -> exit 2
# ---------------------------------------------------------------------------

class TestUsage:
    def test_no_args(self, capsys):
        assert cli.main([]) == 2
        assert "usage:" in capsys.readouterr().err

    def test_unknown_subcommand(self, capsys):
        assert cli.main(["build", "x.lang"]) == 2
        assert "usage:" in capsys.readouterr().err

    def test_too_many_args(self, capsys):
        assert cli.main(["run", "a.lang", "b.lang"]) == 2
        assert "usage:" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Glang errors -> exit 1 with message on stderr
# ---------------------------------------------------------------------------

class TestErrors:
    def test_type_error(self, tmp_path, capsys):
        path = write(tmp_path, "p.lang", "int main() { return true; }\n")
        assert cli.main(["run", path]) == 1
        assert "error:" in capsys.readouterr().err

    def test_parse_error(self, tmp_path, capsys):
        path = write(tmp_path, "p.lang", "int main( { return 0; }\n")
        assert cli.main(["run", path]) == 1
        assert "error:" in capsys.readouterr().err

    def test_runtime_error(self, tmp_path, capsys):
        path = write(
            tmp_path, "p.lang",
            "int main() { int* p = null; return *p; }\n",
        )
        assert cli.main(["run", path]) == 1
        assert "error:" in capsys.readouterr().err

    def test_missing_file(self, tmp_path, capsys):
        missing = os.path.join(str(tmp_path), "nope.lang")
        assert cli.main(["run", missing]) == 1
        assert "error:" in capsys.readouterr().err

    def test_no_main_function(self, tmp_path, capsys):
        path = write(tmp_path, "p.lang", "int helper() { return 1; }\n")
        assert cli.main(["run", path]) == 1
        assert "error:" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Output is flushed even when a runtime error follows
# ---------------------------------------------------------------------------

class TestPartialOutput:
    def test_output_before_runtime_error_is_emitted(self, tmp_path, capsys):
        path = write(
            tmp_path, "p.lang",
            'int main() { print("before"); int* p = null; return *p; }\n',
        )
        code = cli.main(["run", path])
        captured = capsys.readouterr()
        assert code == 1
        assert "before\n" in captured.out
        assert "error:" in captured.err
