"""MRFHelper public package interface."""

import sys

__version__ = "2.6.0"

from . import (
    building_geometry,
    connection_and_boundary,
    load_and_material,
    mrf_helper,
    structural_components,
    user_command,
    validation,
    write_info,
    write_script,
)
from .mrf_helper import Frame, from_json
from .write_script import ScriptWriter

# Import compatibility without retaining duplicate CamelCase module files.
_legacy_modules = {
    "BuildingGeometry": building_geometry,
    "ConnectionAndBoundary": connection_and_boundary,
    "LoadAndMaterial": load_and_material,
    "MRFhelper": mrf_helper,
    "StructuralComponents": structural_components,
    "UserCommand": user_command,
    "WriteInfo": write_info,
    "WriteScript": write_script,
    "func": validation,
}
for _legacy_name, _module in _legacy_modules.items():
    sys.modules[f"{__name__}.{_legacy_name}"] = _module

# Used by the original ``main.py`` import style.
MRFhelper = mrf_helper

__all__ = ["Frame", "ScriptWriter", "from_json", "__version__"]
