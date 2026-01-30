import sys
from importlib import resources
from pathlib import Path

_loaded_key = "_powerfx_loaded"

# fix_clr_loader.py
"""
Patches clr_loader to support .NET 10+ (double-digit major versions).

This must be imported BEFORE any imports that trigger pythonnet/clr_loader,
such as `from powerfx import Engine` or `from agent_framework.declarative import AgentFactory`.

Bug reference: https://github.com/pythonnet/clr-loader/blob/61d7879d2b5f0b135dce179db2e684c60a96e745/clr_loader/util/runtime_spec.py#L21
"""


def apply_patch():
    """
    Patches DotnetCoreRuntimeSpec.floor_version and tfm to correctly parse
    versions like "10.0.0" instead of producing "10..0".

    Only applies the fix for major versions with length > 1 (10, 11, 12, etc.)
    Falls back to original methods for single-digit versions (8, 9, etc.)
    """
    try:
        from clr_loader.util.runtime_spec import DotnetCoreRuntimeSpec  # type: ignore
    except ImportError:
        print("Warning: clr_loader not installed, skipping patch")
        return False

    # Store originals for fallback
    _original_floor_version = DotnetCoreRuntimeSpec.floor_version.fget
    _original_tfm = DotnetCoreRuntimeSpec.tfm.fget

    def _fixed_floor_version(self) -> str:
        """
        Returns the floor version (major.minor.0) for runtime config.

        Original implementation used string slicing [:3] which breaks
        for double-digit major versions like "10.0.0".

        Examples:
            "8.0.0"  -> (original) "8.0.0"
            "9.0.0"  -> (original) "9.0.0"
            "10.0.0" -> (fixed)    "10.0.0"
            "11.0.4" -> (fixed)    "11.0.0"
        """
        parts = self.version.split(".")

        # Only apply fix for double-digit major versions (10, 11, 12, etc.)
        if len(parts) >= 1 and len(parts[0]) > 1:
            print(f"[floor_version] Applying fix for version: {self.version} -> {parts[0]}.{parts[1]}.0")
            return f"{parts[0]}.{parts[1]}.0"

        return _original_floor_version(self)

    def _fixed_tfm(self) -> str:
        """
        Returns the Target Framework Moniker (e.g., 'net8.0', 'net10.0').

        Original implementation used string slicing [:3] which breaks
        for double-digit major versions.

        Examples:
            "8.0.0"  -> (original) "net8.0"
            "9.0.0"  -> (original) "net9.0"
            "10.0.0" -> (fixed)    "net10.0"
            "11.0.4" -> (fixed)    "net11.0"
        """
        parts = self.version.split(".")

        # Only apply fix for double-digit major versions (10, 11, 12, etc.)
        if len(parts) >= 1 and len(parts[0]) > 1:
            print(f"[tfm] Applying fix for version: {self.version} -> net{parts[0]}.{parts[1]}")
            return f"net{parts[0]}.{parts[1]}"

        # Fallback to original behavior for single-digit versions
        print(f"[tfm] Using original for version: {self.version}")
        return _original_tfm(self)

    # Replace the properties with our fixed versions
    DotnetCoreRuntimeSpec.floor_version = property(_fixed_floor_version)
    DotnetCoreRuntimeSpec.tfm = property(_fixed_tfm)

    print("Patch applied successfully")
    return True


# Auto-apply when imported
_patched = apply_patch()

if _patched:
    print("✓ Applied clr_loader patch for .NET 10+ compatibility")


def load() -> None:
    """
    Ensure Microsoft.PowerFx assemblies are loadable via pythonnet (CoreCLR).

    Precedence for dll_dir:
    - explicit arg
    - env var POWERFX_DLL_DIR
    - <pkg>/runtime (optional fallback)
    """
    if getattr(sys.modules[__name__], _loaded_key, False):
        return

    base = _bundled_dir()
    if not base.is_dir():
        raise RuntimeError(f"Power Fx DLL directory '{base}' does not exist.")

    # Select CoreCLR BEFORE any clr import
    import pythonnet  # type: ignore

    pythonnet.load("coreclr")

    import clr  # type: ignore

    # Make sure PowerFx DLL folder is in probing paths
    if base not in sys.path:
        sys.path.append(str(base))

    # Load ONLY the PowerFx assemblies you ship; let CoreCLR resolve System.* deps.
    for name in ("Microsoft.PowerFx.Core", "Microsoft.PowerFx.Interpreter", "Microsoft.PowerFx.Transport.Attributes"):
        try:
            clr.AddReference(name)
        except Exception as ex:
            # Fallback to explicit path if name load fails
            print(f"Failed to load '{name}' by name, trying explicit path. Exception: {ex}")
            raise

    setattr(sys.modules[__name__], _loaded_key, True)


def _bundled_dir() -> Path:
    """
    Return the path to the bundled PowerFx assemblies inside this package.
    """
    return Path(str(resources.files("powerfx") / "_bundled")).resolve()
