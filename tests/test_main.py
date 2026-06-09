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
# File I/O builtins (run with cwd at the temp dir so relative paths resolve)
# ---------------------------------------------------------------------------

class TestFileIO:
    def test_write_then_read_round_trip(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = write(
            tmp_path, "p.lang",
            'int main() {\n'
            '    writeFile("data.txt", "hello world");\n'
            '    print(fileExists("data.txt"));\n'
            '    print(readFile("data.txt"));\n'
            '    return 0;\n'
            '}\n',
        )
        code = cli.main(["run", path])
        assert code == 0
        assert capsys.readouterr().out == "true\nhello world\n"

    def test_file_exists_false_for_missing(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = write(
            tmp_path, "p.lang",
            'int main() { print(fileExists("nope.txt")); return 0; }\n',
        )
        assert cli.main(["run", path]) == 0
        assert capsys.readouterr().out == "false\n"

    def test_read_missing_file_errors(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = write(
            tmp_path, "p.lang",
            'int main() { string s = readFile("nope.txt"); return 0; }\n',
        )
        assert cli.main(["run", path]) == 1
        assert "error:" in capsys.readouterr().err

    def test_stdlib_io_helpers(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = write(
            tmp_path, "p.lang",
            'import "std/io.lang";\n'
            'int main() {\n'
            '    writeFile("log.txt", "a\\n");\n'
            '    appendFile("log.txt", "b\\n");\n'
            '    print(readLineCount("log.txt"));\n'
            '    return 0;\n'
            '}\n',
        )
        assert cli.main(["run", path]) == 0
        assert capsys.readouterr().out == "2\n"


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

    def test_run_with_no_subcommand_is_error(self, capsys):
        assert cli.main(["a.lang"]) == 2
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


# ---------------------------------------------------------------------------
# Compiler I/O builtins via CLI
# ---------------------------------------------------------------------------

class TestCompilerIO:
    def test_extra_args_passed_as_prog_args(self, tmp_path, capsys):
        path = write(
            tmp_path, "p.lang",
            "int main() { print(getArgCount()); print(getArg(0)); return 0; }\n",
        )
        code = cli.main(["run", path, "hello"])
        captured = capsys.readouterr()
        assert code == 0
        assert captured.out == "1\nhello\n"

    def test_multiple_extra_args(self, tmp_path, capsys):
        path = write(
            tmp_path, "p.lang",
            "int main() { print(getArgCount()); return 0; }\n",
        )
        code = cli.main(["run", path, "a", "b", "c"])
        assert code == 0
        assert capsys.readouterr().out == "3\n"

    def test_exit_builtin_propagates_code(self, tmp_path):
        path = write(tmp_path, "p.lang", "int main() { exit(42); return 0; }\n")
        assert cli.main(["run", path]) == 42

    def test_print_err_goes_to_stderr(self, tmp_path, capsys):
        path = write(
            tmp_path, "p.lang",
            'int main() { printErr("bad news"); return 0; }\n',
        )
        code = cli.main(["run", path])
        captured = capsys.readouterr()
        assert code == 0
        assert "bad news\n" in captured.err
        assert captured.out == ""
