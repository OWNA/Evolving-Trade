import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "patching", Path(__file__).resolve().parents[1] / "alphaevolve/evolution/patching.py"
)
patching = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patching)
apply_patch = patching.apply_patch


def test_apply_patch_full_replace():
    parent = "print('old')"
    diff = {"code": "print('new')"}
    assert apply_patch(parent, diff) == "print('new')"


def test_apply_patch_block_replace():
    parent = (
        "def func():\n"
        "    # === EVOLVE-BLOCK: foo ===\n"
        "    print('old')\n"
        "    # === END EVOLVE-BLOCK ===\n"
    )
    diff = {"blocks": {"foo": "print('new')"}}
    result = apply_patch(parent, diff)
    expected = (
        "def func():\n"
        "    # === EVOLVE-BLOCK: foo ===\n"
        "    print('new')\n"
        "    # === END EVOLVE-BLOCK ===\n"
    )
    assert result == expected

def test_apply_patch_preserves_indentation():
    parent = (
        "def foo():\n"
        "    # === EVOLVE-BLOCK: block ===\n"
        "    print('old')\n"
        "    # === END EVOLVE-BLOCK ===\n"
    )
    diff = {"blocks": {"block": "a = 1\nb = 2"}}
    result = apply_patch(parent, diff)
    expected = (
        "def foo():\n"
        "    # === EVOLVE-BLOCK: block ===\n"
        "    a = 1\n"
        "    b = 2\n"
        "    # === END EVOLVE-BLOCK ===\n"
    )
    assert result == expected
