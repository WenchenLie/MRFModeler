"""Reinforced-concrete section input and geometry helpers."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

BAR_SPEC = re.compile(r"^(?P<count>\d+)[dD](?P<diameter>(?:\d+(?:\.\d*)?|\.\d+))$")
REQUIRED_COLUMNS = {
    "section_name",
    "b",
    "h",
    "cover",
    "top_corner",
    "top_inner",
    "bottom_corner",
    "bottom_inner",
    "side_each",
    "stirrup",
    "stirrup_spacing",
}


@dataclass(frozen=True)
class BarGroup:
    """One or more groups of bars sharing a section location."""

    groups: tuple[tuple[int, float], ...] = ()

    def __post_init__(self) -> None:
        if any(count <= 0 or diameter <= 0 for count, diameter in self.groups):
            raise ValueError("Bar count and diameter must be positive")

    @classmethod
    def parse(cls, value, *, field: str) -> BarGroup:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return cls()
        text = str(value).strip()
        if not text or text == "0":
            return cls()
        groups: list[tuple[int, float]] = []
        for term in text.split("+"):
            match = BAR_SPEC.fullmatch(term.strip())
            if match is None:
                raise ValueError(
                    f"Invalid reinforcement specification `{value}` in `{field}`; "
                    "expected `countDdiameter` rows separated by `+`"
                )
            count = int(match.group("count"))
            diameter = float(match.group("diameter"))
            if count <= 0 or diameter <= 0:
                raise ValueError(f"Bar count and diameter in `{field}` must be positive")
            groups.append((count, diameter))
        return cls(tuple(groups))

    @classmethod
    def from_dict(cls, data: list[dict]) -> BarGroup:
        return cls(tuple((int(item["count"]), float(item["diameter"])) for item in data))

    @property
    def count(self) -> int:
        return sum(count for count, _ in self.groups)

    @property
    def area(self) -> float:
        return sum(count * math.pi * diameter**2 / 4 for count, diameter in self.groups)

    @property
    def maximum_diameter(self) -> float:
        return max((diameter for _, diameter in self.groups), default=0.0)

    def expanded_diameters(self) -> list[float]:
        values = [diameter for count, diameter in self.groups for _ in range(count)]
        return sorted(values, reverse=True)

    def to_dict(self) -> list[dict[str, int | float]]:
        return [{"count": count, "diameter": diameter} for count, diameter in self.groups]

    def canonical(self) -> str:
        if not self.groups:
            return "0"
        return "+".join(f"{count}D{diameter:g}" for count, diameter in self.groups)


@dataclass(frozen=True)
class RCSection:
    name: str
    b: float
    h: float
    cover: float
    top_corner: BarGroup
    top_inner: BarGroup
    bottom_corner: BarGroup
    bottom_inner: BarGroup
    side_each: BarGroup
    stirrup: BarGroup
    stirrup_spacing: float
    bond_slip: int = 1

    @classmethod
    def from_row(cls, row: dict) -> RCSection:
        name = str(row["section_name"]).strip()
        if not name:
            raise ValueError(f"Illegal RC section name: {name!r}")
        try:
            b = float(row["b"])
            h = float(row["h"])
            cover = float(row["cover"])
            spacing = float(row["stirrup_spacing"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Section `{name}` contains a non-numeric dimension") from error
        if min(b, h, spacing) <= 0 or cover < 0:
            raise ValueError(f"Section `{name}` dimensions must be positive")
        bond_slip_value = row.get("bond_slip", 1)
        if bond_slip_value is None or (
            isinstance(bond_slip_value, float) and math.isnan(bond_slip_value)
        ):
            bond_slip_value = 1
        try:
            bond_slip_number = float(bond_slip_value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Section `{name}` bond_slip must be 0 or 1") from error
        if bond_slip_number not in {0.0, 1.0}:
            raise ValueError(f"Section `{name}` bond_slip must be 0 or 1")
        bond_slip = int(bond_slip_number)
        section = cls(
            name=name,
            b=b,
            h=h,
            cover=cover,
            top_corner=BarGroup.parse(row["top_corner"], field="top_corner"),
            top_inner=BarGroup.parse(row["top_inner"], field="top_inner"),
            bottom_corner=BarGroup.parse(row["bottom_corner"], field="bottom_corner"),
            bottom_inner=BarGroup.parse(row["bottom_inner"], field="bottom_inner"),
            side_each=BarGroup.parse(row["side_each"], field="side_each"),
            stirrup=BarGroup.parse(row["stirrup"], field="stirrup"),
            stirrup_spacing=spacing,
            bond_slip=bond_slip,
        )
        section.validate()
        return section

    @classmethod
    def from_dict(cls, data: dict) -> RCSection:
        reinforcement = data["reinforcement"]
        section = cls(
            name=str(data["name"]).strip(),
            b=float(data["b"]),
            h=float(data["h"]),
            cover=float(data["cover"]),
            top_corner=BarGroup.from_dict(reinforcement["top_corner"]),
            top_inner=BarGroup.from_dict(reinforcement["top_inner"]),
            bottom_corner=BarGroup.from_dict(reinforcement["bottom_corner"]),
            bottom_inner=BarGroup.from_dict(reinforcement["bottom_inner"]),
            side_each=BarGroup.from_dict(reinforcement["side_each"]),
            stirrup=BarGroup.from_dict(data["stirrup"]),
            stirrup_spacing=float(data["stirrup_spacing"]),
            bond_slip=int(data.get("bond_slip", 1)),
        )
        section.validate()
        return section

    @property
    def area(self) -> float:
        return self.b * self.h

    @property
    def gross_inertia(self) -> float:
        return self.b * self.h**3 / 12

    @property
    def top_bars(self) -> BarGroup:
        return BarGroup(self.top_corner.groups + self.top_inner.groups)

    @property
    def bottom_bars(self) -> BarGroup:
        return BarGroup(self.bottom_corner.groups + self.bottom_inner.groups)

    @property
    def side_area_total(self) -> float:
        return 2 * self.side_each.area

    @property
    def transverse_ratio(self) -> float:
        return self.stirrup.area / (self.b * self.stirrup_spacing)

    @property
    def stirrup_diameter(self) -> float:
        return self.stirrup.maximum_diameter

    def layer_centroid_from_face(self, group: BarGroup) -> float:
        if group.area == 0:
            raise ValueError(f"Section `{self.name}` has an empty longitudinal layer")
        weighted = sum(
            count * math.pi * diameter**2 / 4 * (self.cover + self.stirrup_diameter + diameter / 2)
            for count, diameter in group.groups
        )
        return weighted / group.area

    def longitudinal_rows(self, face: str) -> list[BarGroup]:
        """Return reinforcement rows ordered from the selected concrete face inward."""
        if face not in {"top", "bottom"}:
            raise ValueError("face must be `top` or `bottom`")
        corner = self.top_corner if face == "top" else self.bottom_corner
        inner = self.top_inner if face == "top" else self.bottom_inner
        row_count = max(len(corner.groups), len(inner.groups))
        rows = []
        for index in range(row_count):
            groups = ()
            if index < len(corner.groups):
                groups += (corner.groups[index],)
            if index < len(inner.groups):
                groups += (inner.groups[index],)
            rows.append(BarGroup(groups))
        return rows

    def longitudinal_row_depths(self, face: str) -> list[float]:
        """Return row-centroid depths using code-style minimum clear spacing."""
        rows = self.longitudinal_rows(face)
        depths: list[float] = []
        previous_diameter = 0.0
        for index, row in enumerate(rows):
            diameter = row.maximum_diameter
            if index == 0:
                depth = self.cover + self.stirrup_diameter + diameter / 2
            else:
                clear_spacing = max(25.0, previous_diameter, diameter)
                depth = depths[-1] + previous_diameter / 2 + clear_spacing + diameter / 2
            depths.append(depth)
            previous_diameter = diameter
        return depths

    def longitudinal_centroid_from_face(self, face: str) -> float:
        rows = self.longitudinal_rows(face)
        depths = self.longitudinal_row_depths(face)
        total_area = sum(row.area for row in rows)
        if total_area <= 0:
            raise ValueError(f"Section `{self.name}` has no {face} longitudinal reinforcement")
        return sum(row.area * depth for row, depth in zip(rows, depths)) / total_area

    def validate(self) -> None:
        if not self.name:
            raise ValueError(f"Illegal RC section name: {self.name!r}")
        if min(self.b, self.h, self.stirrup_spacing) <= 0 or self.cover < 0:
            raise ValueError(f"Section `{self.name}` dimensions must be positive")
        if self.bond_slip not in {0, 1}:
            raise ValueError(f"Section `{self.name}` bond_slip must be 0 or 1")
        if any(count != 2 for count, _ in self.top_corner.groups) or any(
            count != 2 for count, _ in self.bottom_corner.groups
        ):
            raise ValueError(
                f"Section `{self.name}` must define exactly two corner bars in each corner row"
            )
        if not self.top_corner.groups or not self.bottom_corner.groups:
            raise ValueError(f"Section `{self.name}` must define top and bottom corner bars")
        if self.stirrup.count < 2:
            raise ValueError(
                f"Section `{self.name}` must define at least two effective stirrup legs"
            )
        maximum_bar = max(
            self.top_bars.maximum_diameter,
            self.bottom_bars.maximum_diameter,
            self.side_each.maximum_diameter,
        )
        inset = self.cover + self.stirrup_diameter + maximum_bar / 2
        if 2 * inset >= min(self.b, self.h):
            raise ValueError(
                f"Reinforcement in section `{self.name}` does not fit within the section cover"
            )
        top_rows = self.longitudinal_rows("top")
        bottom_rows = self.longitudinal_rows("bottom")
        top_depths = self.longitudinal_row_depths("top")
        bottom_depths = self.longitudinal_row_depths("bottom")
        top_extent = top_depths[-1] + top_rows[-1].maximum_diameter / 2
        bottom_extent = bottom_depths[-1] + bottom_rows[-1].maximum_diameter / 2
        if top_extent + bottom_extent >= self.h:
            raise ValueError(f"Top and bottom reinforcement rows overlap in section `{self.name}`")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "b": self.b,
            "h": self.h,
            "cover": self.cover,
            "reinforcement": {
                "top_corner": self.top_corner.to_dict(),
                "top_inner": self.top_inner.to_dict(),
                "bottom_corner": self.bottom_corner.to_dict(),
                "bottom_inner": self.bottom_inner.to_dict(),
                "side_each": self.side_each.to_dict(),
            },
            "stirrup": self.stirrup.to_dict(),
            "stirrup_spacing": self.stirrup_spacing,
            "bond_slip": self.bond_slip,
        }


def load_rc_sections_csv(path: str | Path) -> dict[str, RCSection]:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"RC section CSV file not found: {csv_path}")
    table = pd.read_csv(csv_path, encoding="utf-8-sig", keep_default_na=False)
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    if missing:
        raise ValueError(f"RC section CSV is missing required columns: {missing}")
    duplicated = table["section_name"].astype(str).str.strip().duplicated(keep=False)
    if duplicated.any():
        names = sorted(set(table.loc[duplicated, "section_name"].astype(str)))
        raise ValueError(f"Duplicate RC section names: {names}")
    sections = [RCSection.from_row(row) for row in table.to_dict(orient="records")]
    if not sections:
        raise ValueError("RC section CSV contains no sections")
    return {section.name: section for section in sections}
