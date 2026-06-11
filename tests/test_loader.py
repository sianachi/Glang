import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loader.loader import Loader, load
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import ImportError as GImportError, TypeError as GTypeError


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def write(directory, name: str, src: str) -> str:
    """Write a .lang file (creating parent dirs) and return its path."""
    path = os.path.join(str(directory), name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    return path


def decl_names(program) -> set:
    return {getattr(d, "name", None) for d in program.declarations}


def run(root_path: str) -> int:
    prog = Loader().load(root_path)
    env = Analyser().analyse(prog)
    return Interpreter(env).run(prog)


# ---------------------------------------------------------------------------
# Basic resolution & merging
# ---------------------------------------------------------------------------

class TestStdlibResolution:
    def test_std_prefix_resolves_to_stdlib_dir(self, tmp_path):
        stdlib = tmp_path / "stdlib"
        write(stdlib, "math.lang", "int answer() { return 42; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "std/math.lang";\n'
            "int main() { return answer(); }\n",
        )
        loader = Loader(stdlib_dir=str(stdlib))
        prog = loader.load(root)
        assert decl_names(prog) == {"answer", "main"}
        env = Analyser().analyse(prog)
        assert Interpreter(env).run(prog) == 42

    def test_std_prefix_is_not_relative_to_importer(self, tmp_path):
        # A sibling math.lang next to main must NOT be picked up for std/ imports.
        write(tmp_path, "math.lang", "int answer() { return 1; }\n")
        stdlib = tmp_path / "lib"
        write(stdlib, "math.lang", "int answer() { return 2; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "std/math.lang";\nint main() { return answer(); }\n',
        )
        env = Analyser().analyse(Loader(stdlib_dir=str(stdlib)).load(root))
        prog = Loader(stdlib_dir=str(stdlib)).load(root)
        assert Interpreter(env).run(prog) == 2

    def test_missing_std_file_raises(self, tmp_path):
        root = write(
            tmp_path, "main.lang",
            'import "std/nope.lang";\nint main() { return 0; }\n',
        )
        with pytest.raises(GImportError):
            Loader(stdlib_dir=str(tmp_path / "stdlib")).load(root)

    def test_glang_stdlib_env_override(self, tmp_path, monkeypatch):
        stdlib = tmp_path / "env_stdlib"
        write(stdlib, "math.lang", "int answer() { return 11; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "std/math.lang";\nint main() { return answer(); }\n',
        )
        monkeypatch.setenv("GLANG_STDLIB", str(stdlib))
        prog = Loader().load(root)
        assert Interpreter(Analyser().analyse(prog)).run(prog) == 11

    def test_finds_stdlib_next_to_executable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GLANG_STDLIB", raising=False)
        bin_dir = tmp_path / "bin"
        stdlib = bin_dir / "stdlib"
        write(stdlib, "math.lang", "int answer() { return 13; }\n")
        fake_exe = write(bin_dir, "glang", "")
        root = write(
            tmp_path, "main.lang",
            'import "std/math.lang";\nint main() { return answer(); }\n',
        )
        monkeypatch.setattr(sys, "executable", fake_exe)
        prog = Loader().load(root)
        assert Interpreter(Analyser().analyse(prog)).run(prog) == 13


class TestBasicImport:
    def test_imported_declarations_are_merged(self, tmp_path):
        write(tmp_path, "helper.lang", "int helper() { return 7; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "helper.lang";\n'
            "int main() { return helper(); }\n",
        )
        prog = Loader().load(root)
        assert decl_names(prog) == {"helper", "main"}
        # Merged program analyses cleanly.
        Analyser().analyse(prog)

    def test_imports_list_is_resolved_away(self, tmp_path):
        write(tmp_path, "helper.lang", "int helper() { return 1; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "helper.lang";\nint main() { return 0; }\n',
        )
        prog = Loader().load(root)
        assert prog.imports == []

    def test_module_level_load_helper(self, tmp_path):
        write(tmp_path, "helper.lang", "int helper() { return 1; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "helper.lang";\nint main() { return 0; }\n',
        )
        prog = load(root)
        assert decl_names(prog) == {"helper", "main"}


# ---------------------------------------------------------------------------
# End-to-end execution across files
# ---------------------------------------------------------------------------

class TestCrossFileExecution:
    def test_call_imported_function(self, tmp_path):
        write(tmp_path, "math.lang", "int square(int x) { return x * x; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "math.lang";\n'
            "int main() { return square(6); }\n",
        )
        assert run(root) == 36

    def test_use_imported_class(self, tmp_path):
        write(
            tmp_path, "counter.lang",
            "class Counter {\n"
            "  int n;\n"
            "  Counter() { this.n = 0; }\n"
            "  void inc() { this.n = this.n + 1; }\n"
            "  int get() { return this.n; }\n"
            "}\n",
        )
        root = write(
            tmp_path, "main.lang",
            'import "counter.lang";\n'
            "int main() { Counter* c = new Counter(); c->inc(); c->inc(); "
            "int v = c->get(); delete c; return v; }\n",
        )
        assert run(root) == 2


# ---------------------------------------------------------------------------
# Transitive imports & include guards
# ---------------------------------------------------------------------------

class TestTransitiveAndDiamond:
    def test_transitive_chain(self, tmp_path):
        write(tmp_path, "c.lang", "int c() { return 3; }\n")
        write(tmp_path, "b.lang", 'import "c.lang";\nint b() { return c(); }\n')
        write(tmp_path, "a.lang", 'import "b.lang";\nint a() { return b(); }\n')
        root = write(
            tmp_path, "main.lang",
            'import "a.lang";\nint main() { return a(); }\n',
        )
        prog = Loader().load(root)
        assert decl_names(prog) == {"a", "b", "c", "main"}
        assert run(root) == 3

    def test_diamond_include_guard(self, tmp_path):
        # main -> a -> shared, main -> b -> shared. `shared` must load once.
        write(tmp_path, "shared.lang", "int shared() { return 9; }\n")
        write(tmp_path, "a.lang", 'import "shared.lang";\nint a() { return shared(); }\n')
        write(tmp_path, "b.lang", 'import "shared.lang";\nint b() { return shared(); }\n')
        root = write(
            tmp_path, "main.lang",
            'import "a.lang";\nimport "b.lang";\n'
            "int main() { return a() + b(); }\n",
        )
        prog = Loader().load(root)
        # `shared` appears exactly once despite two import paths to it.
        names = [getattr(d, "name", None) for d in prog.declarations]
        assert names.count("shared") == 1
        # No "already defined" error, and it runs.
        assert run(root) == 18


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

class TestPathResolution:
    def test_relative_to_importing_file(self, tmp_path):
        # lib/util.lang imports lib/helper.lang via a path relative to lib/.
        write(tmp_path, "lib/helper.lang", "int helper() { return 5; }\n")
        write(
            tmp_path, "lib/util.lang",
            'import "helper.lang";\nint util() { return helper(); }\n',
        )
        root = write(
            tmp_path, "main.lang",
            'import "lib/util.lang";\nint main() { return util(); }\n',
        )
        assert run(root) == 5

    def test_same_file_via_different_paths_loads_once(self, tmp_path):
        # main imports lib/shared.lang directly and again via lib/wrap.lang;
        # realpath normalisation collapses them to one load.
        write(tmp_path, "lib/shared.lang", "int shared() { return 4; }\n")
        write(
            tmp_path, "lib/wrap.lang",
            'import "shared.lang";\nint wrap() { return shared(); }\n',
        )
        root = write(
            tmp_path, "main.lang",
            'import "lib/shared.lang";\nimport "lib/wrap.lang";\n'
            "int main() { return shared() + wrap(); }\n",
        )
        prog = Loader().load(root)
        names = [getattr(d, "name", None) for d in prog.declarations]
        assert names.count("shared") == 1
        assert run(root) == 8


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class TestErrors:
    def test_circular_import(self, tmp_path):
        write(tmp_path, "a.lang", 'import "b.lang";\nint a() { return 1; }\n')
        write(tmp_path, "b.lang", 'import "a.lang";\nint b() { return 2; }\n')
        root = write(tmp_path, "a.lang", 'import "b.lang";\nint a() { return 1; }\n')
        with pytest.raises(GImportError, match="circular import"):
            Loader().load(root)

    def test_missing_imported_file(self, tmp_path):
        root = write(
            tmp_path, "main.lang",
            'import "does_not_exist.lang";\nint main() { return 0; }\n',
        )
        with pytest.raises(GImportError, match="cannot find imported file"):
            Loader().load(root)

    def test_missing_root_file(self, tmp_path):
        missing = os.path.join(str(tmp_path), "nope.lang")
        with pytest.raises(GImportError, match="cannot find source file"):
            Loader().load(missing)

    def test_duplicate_name_across_files(self, tmp_path):
        write(tmp_path, "other.lang", "int dup() { return 1; }\n")
        root = write(
            tmp_path, "main.lang",
            'import "other.lang";\n'
            "int dup() { return 2; }\n"
            "int main() { return dup(); }\n",
        )
        prog = Loader().load(root)
        # Merged declarations reach Pass1, which rejects the duplicate name.
        with pytest.raises(GTypeError, match="already defined"):
            Analyser().analyse(prog)

    def test_parse_error_in_imported_file_propagates(self, tmp_path):
        from errors.errors import ParseError
        write(tmp_path, "bad.lang", "int oops( {\n")  # malformed
        root = write(
            tmp_path, "main.lang",
            'import "bad.lang";\nint main() { return 0; }\n',
        )
        with pytest.raises(ParseError):
            Loader().load(root)
