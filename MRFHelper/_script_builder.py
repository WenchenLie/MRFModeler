"""Shared text-buffer and model-registry support for script generation."""

from __future__ import annotations

import warnings
from typing import Any


class ScriptBuilder:
    """Collect paired scripts and register model geometry for visualisation."""

    def __init__(self, axes: Any) -> None:
        self.ax = axes
        self.tcl_script: list[str] = []
        self.py_script: list[str] = []
        self.nodes_Id: dict[int, tuple[float, float]] = {}
        self.eles_Id: dict[int, tuple[int, int]] = {}
        self.Nlines = 0
        self.Nlinespy = 0
        self.Nrecorder = 0

    def write(self, *text) -> None:
        """Append one logical line to the Tcl script."""
        if len(text) == 1:
            line = str(text[0])
        else:
            line = "  ".join(str(item) for item in text)
        self.tcl_script.append(line)
        self.Nlines += 1

    def writepy(self, *text, start="    ") -> None:
        """Append one logical line to the OpenSeesPy script."""
        if not text:
            line = ""
        elif len(text) == 1:
            line = start + str(text[0])
        else:
            line = "\n".join(start + str(item) for item in text) + "\n"
        self.py_script.append(line)
        self.Nlinespy += 1

    @staticmethod
    def get_id(*parts: int) -> int:
        """Build a node or element tag from zero-padded numeric parts."""
        if any(isinstance(part, bool) or not isinstance(part, int) or part < 0 for part in parts):
            raise ValueError("ID parts must be non-negative integers")
        return int("".join(f"{part:02d}" for part in parts))

    def node(
        self,
        x: float | int,
        y: float | int,
        c: str = "black",
        node_id: int | None = None,
        size=2,
        check=True,
    ) -> None:
        self.ax.plot(x, y, "o", color=c, markersize=size)
        if node_id is None:
            return
        if node_id in self.nodes_Id and check:
            warnings.warn(f"Node id {node_id} already exists", stacklevel=2)
            return
        self.nodes_Id[int(node_id)] = (x, y)

    def ele(
        self,
        i_node: int,
        j_node: int,
        c: str = "blue",
        element_id: int | None = None,
        check=True,
    ) -> None:
        xi, yi = self.get_coord(i_node)
        xj, yj = self.get_coord(j_node)
        self.ax.plot([xi, xj], [yi, yj], color=c, lw=1)
        if element_id is None:
            return
        if element_id in self.eles_Id and check:
            warnings.warn(f"Element id {element_id} already exists", stacklevel=2)
            return
        self.eles_Id[element_id] = (i_node, j_node)

    def zero_length(
        self,
        i_node: int,
        j_node: int,
        c: str = "red",
        element_id: int | None = None,
        size=3,
    ) -> None:
        xi, yi = self.get_coord(i_node)
        xj, yj = self.get_coord(j_node)
        if (xi, yi) != (xj, yj):
            raise ValueError(
                "Coordinates of zero-length element nodes are different\n"
                f"{i_node}: ({xi}, {yi})\n{j_node}: ({xj}, {yj})"
            )
        self.ax.plot(xi, yi, marker="o", color=c, markersize=size, zorder=99999)
        self.ax.plot(xj, yj, marker="o", color=c, markersize=size, zorder=99999)
        if element_id is None:
            return
        if element_id in self.eles_Id:
            warnings.warn(f"Element id {element_id} already exists", stacklevel=2)
            return
        self.eles_Id[element_id] = (i_node, j_node)

    def joint2d(
        self,
        center_node: int,
        bottom_node: int,
        right_node: int,
        top_node: int,
        left_node: int,
        c: str = "tab:purple",
        element_id: int | None = None,
    ) -> None:
        """Draw a Joint2D as its physical rectangular panel."""
        center_x, center_y = self.get_coord(center_node)
        bottom_x, bottom_y = self.get_coord(bottom_node)
        right_x, right_y = self.get_coord(right_node)
        top_x, top_y = self.get_coord(top_node)
        left_x, left_y = self.get_coord(left_node)
        if not (
            bottom_x == center_x == top_x
            and left_y == center_y == right_y
            and left_x < center_x < right_x
            and bottom_y < center_y < top_y
        ):
            raise ValueError(f"Joint2D {element_id} external nodes do not form a valid panel")
        x_values = [left_x, right_x, right_x, left_x, left_x]
        y_values = [bottom_y, bottom_y, top_y, top_y, bottom_y]
        self.ax.plot(x_values, y_values, color=c, lw=1.25, zorder=5)
        if element_id is None:
            return
        if element_id in self.eles_Id:
            warnings.warn(f"Element id {element_id} already exists", stacklevel=2)
            return
        self.eles_Id[element_id] = (bottom_node, right_node)

    def get_coord(self, node_id: int) -> tuple[float, float]:
        """Return the coordinate registered for a node tag."""
        node_id = int(node_id)
        if node_id not in self.nodes_Id:
            raise ValueError(f"Node id {node_id} does not exist")
        return self.nodes_Id[node_id]

    def add_recorder(self) -> None:
        self.Nrecorder += 1
