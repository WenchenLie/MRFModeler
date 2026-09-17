"""Self-contained HTML model reports for steel and RC frames."""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
from typing import Any


def _number(value: float | int) -> str:
    value = float(value)
    if value == 0:
        return "0"
    if abs(value) >= 1.0e6 or abs(value) < 1.0e-3:
        return f"{value:.4e}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _assignment_table(mapping: dict[int, list[str]], level_name: str) -> str:
    return _table(
        [level_name, "截面（从左至右）"],
        [[level, " · ".join(names)] for level, names in sorted(mapping.items())],
    )


def _display_value(value: Any) -> str:
    if value is None:
        return "未设置"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, (list, tuple)):
        return "、".join(_display_value(item) for item in value) if value else "无"
    return str(value)


def _load_material_report(frame: Any) -> str:
    data = frame.dict_info["load_and_material"]
    nodal_mass = data["nodal_mass"]
    nodal_load = data["nodal_vertical_load"]
    frame_mass = nodal_mass["moment_frame"]
    leaning_mass = nodal_mass["leaning_column"]
    frame_load = nodal_load["moment_frame"]
    leaning_load = nodal_load["leaning_column"]
    axis_headers = [f"轴线 {axis}" for axis in range(1, frame.axis + 1)]
    mass_rows = [
        [floor, *(_number(value) for value in values), _number(leaning_value)]
        for floor, (values, leaning_value) in enumerate(zip(frame_mass, leaning_mass), start=2)
    ]
    load_rows = [
        [floor, *(_number(value) for value in values), _number(leaning_value)]
        for floor, (values, leaning_value) in enumerate(zip(frame_load, leaning_load), start=2)
    ]

    is_rc = getattr(frame, "frame_type", None) == "reinforced_concrete"
    material_labels = (
        {
            "fc_expected": "混凝土期望抗压强度 fc",
            "ec": "混凝土弹性模量 Ec",
            "fy_expected": "钢筋期望屈服强度 fy",
            "es": "钢筋弹性模量 Es",
            "poisson_ratio": "泊松比",
        }
        if is_rc
        else {
            "elastic_modulus": "钢材弹性模量 E",
            "fy_beam": "梁钢材屈服强度 fy",
            "fy_column": "柱钢材屈服强度 fy",
            "poisson_ratio": "泊松比",
        }
    )
    material = data.get("material", {})
    material_rows = [
        [
            material_labels.get(key, key),
            _display_value(value),
            "MPa" if key != "poisson_ratio" else "—",
        ]
        for key, value in material.items()
    ]
    material_rows.append(
        [
            "柱轴压比放大系数",
            _display_value(data.get("axial_load_ratio_amplification_factor", 1.25)),
            "—",
        ]
    )
    column_stiffness_card = ""
    if is_rc:
        loads = frame.load_and_material
        material_rows.extend(
            [
                ["梁有效刚度折减系数 EIy/EIg", _display_value(loads.beam_ei_ratio), "—"],
                ["柱有效刚度计算式", "限于 0.2–0.6 的 0.75 × (0.1 + PPy)^0.8", "—"],
            ]
        )
        column_rows = []
        for story, ratios in sorted(loads.column_ei_ratios.items()):
            for axis, ratio in enumerate(ratios, start=1):
                ppy = loads.ppy[f"{story}b"][axis - 1]
                column_rows.append([story, axis, _number(ppy), _number(ratio)])
        column_stiffness_card = (
            '<section class="card"><h3>柱等效刚度计算结果</h3>'
            + _table(["故事", "轴线", "放大后轴压比 PPy", "EIy/EIg"], column_rows)
            + "</section>"
        )
    return (
        '<div class="grid">'
        '<section class="card"><h3>节点质量</h3><p>单位：t</p>'
        + _table(["楼层", *axis_headers, "虚拟柱"], mass_rows)
        + '</section><section class="card"><h3>节点竖向荷载</h3>'
        "<p>单位：N；表中数值以向下为正。</p>"
        + _table(["楼层", *axis_headers, "虚拟柱"], load_rows)
        + '</section><section class="card"><h3>材料与刚度</h3>'
        + _table(["参数", "数值", "单位"], material_rows)
        + "</section>"
        + column_stiffness_card
        + "</div>"
    )


def _boundary_report(frame: Any) -> str:
    data = frame.dict_info["connection_and_boundary"]
    labels = {
        "base_support": "柱脚边界",
        "beam_column_connection": "梁柱连接形式",
        "rbs_parameters": "RBS 参数",
        "panel_zone_deformation": "考虑节点域变形",
        "soil_constraint": "土体约束楼层",
        "rigid_diaphragm": "刚性楼板约束",
        "joint_panel_model": "Joint2D 节点域模型",
    }
    rows = []
    for key, value in data.items():
        if key.startswith("//"):
            continue
        if key == "joint_panel_model" and isinstance(value, dict):
            provider_type = value.get("type", "未设置")
            factor = value.get("stiffness_factor")
            descriptions = {
                "Elastic": "弹性节点域（Elastic）",
                "Rigid": "刚性节点域（高刚度 Elastic）",
                "MCFT": "MCFT 节点域（Pinching4）",
            }
            value = descriptions.get(provider_type, provider_type)
            if factor is not None:
                value += f"（刚度倍率 {_display_value(factor)}）"
            if provider_type == "MCFT":
                value += (
                    "（钢筋硬化比 "
                    f"{_display_value(data[key].get('steel_hardening_ratio'))}，"
                    "最大骨料粒径 "
                    f"{_display_value(data[key].get('maximum_aggregate_size'))} mm）"
                )
        elif key == "base_support":
            value = {"Fixed": "固接", "Pinned": "铰接"}.get(value, value)
        elif key == "beam_column_connection":
            value = {"Full": "全强连接", "RBS": "削弱型连接（RBS）", "Hinged": "铰接"}.get(
                value, value
            )
        rows.append([labels.get(key, key), _display_value(value)])
    return _table(["参数", "设置"], rows)


def _steel_svg(name: str, properties: list[float]) -> str:
    flange_width, depth, web_thickness, flange_thickness = properties[:4]
    scale = min(150 / flange_width, 170 / depth)
    width = flange_width * scale
    height = depth * scale
    web = max(web_thickness * scale, 2)
    flange = max(flange_thickness * scale, 2)
    x = 110 - width / 2
    y = 105 - height / 2
    web_x = 110 - web / 2
    return f"""
    <svg viewBox="0 0 220 230" role="img" aria-label="{html.escape(name)} steel section">
      <rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{flange:.2f}" class="section"/>
      <rect x="{web_x:.2f}" y="{y + flange:.2f}" width="{web:.2f}" height="{max(height - 2 * flange, 1):.2f}" class="section"/>
      <rect x="{x:.2f}" y="{y + height - flange:.2f}" width="{width:.2f}" height="{flange:.2f}" class="section"/>
      <text x="110" y="205" text-anchor="middle">d={_number(depth)} mm · bf={_number(flange_width)} mm</text>
      <text x="110" y="221" text-anchor="middle">tw={_number(web_thickness)} mm · tf={_number(flange_thickness)} mm</text>
    </svg>"""


def _rc_bar_positions(section: Any, face: str) -> list[tuple[float, float, float]]:
    rows = section.longitudinal_rows(face)
    depths = section.longitudinal_row_depths(face)
    sign = 1 if face == "top" else -1
    positions: list[tuple[float, float, float]] = []
    for row, depth in zip(rows, depths):
        diameters = row.expanded_diameters()
        if not diameters:
            continue
        inset = section.cover + section.stirrup_diameter + max(diameters) / 2
        span = section.b - 2 * inset
        y = sign * (section.h / 2 - depth)
        for index, diameter in enumerate(diameters):
            x = inset if len(diameters) == 1 else inset + span * index / (len(diameters) - 1)
            positions.append((x - section.b / 2, y, diameter))
    if face == "top":
        side = section.side_each.expanded_diameters()
        for side_sign in (-1, 1):
            for index, diameter in enumerate(side):
                x = side_sign * (
                    section.b / 2 - section.cover - section.stirrup_diameter - diameter / 2
                )
                y = -section.h / 2 + (index + 1) * section.h / (len(side) + 1)
                positions.append((x, y, diameter))
    return positions


def _rc_svg(section: Any) -> str:
    scale = min(160 / section.b, 170 / section.h)
    width, height = section.b * scale, section.h * scale
    x, y = 110 - width / 2, 105 - height / 2
    stirrup_inset = (section.cover + section.stirrup_diameter / 2) * scale
    circles = []
    for bar_x, bar_y, diameter in _rc_bar_positions(section, "top") + _rc_bar_positions(
        section, "bottom"
    ):
        circles.append(
            f'<circle cx="{110 + bar_x * scale:.2f}" cy="{105 - bar_y * scale:.2f}" '
            f'r="{max(diameter * scale / 2, 1.5):.2f}" class="bar"/>'
        )
    return f"""
    <svg viewBox="0 0 220 230" role="img" aria-label="{html.escape(section.name)} RC section">
      <rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" class="concrete"/>
      <rect x="{x + stirrup_inset:.2f}" y="{y + stirrup_inset:.2f}"
            width="{max(width - 2 * stirrup_inset, 1):.2f}"
            height="{max(height - 2 * stirrup_inset, 1):.2f}" class="stirrup"/>
      {"".join(circles)}
      <text x="110" y="205" text-anchor="middle">b={_number(section.b)} mm · h={_number(section.h)} mm</text>
      <text x="110" y="221" text-anchor="middle">cover={_number(section.cover)} mm</text>
    </svg>"""


def _steel_sections(frame: Any) -> str:
    records: dict[tuple[str, str], list[float]] = {}
    for floor, names in frame.structural_components.beams.items():
        for name, properties in zip(names, frame.structural_components.beam_properties[floor]):
            records.setdefault((name, "梁"), properties)
    for story, names in frame.structural_components.columns.items():
        for name, properties in zip(names, frame.structural_components.column_properties[story]):
            records.setdefault((name, "柱"), properties)
    cards = []
    for (name, member), values in sorted(records.items()):
        bf, depth, tw, tf, ry, area, inertia, moment, clear_depth = values
        rows = [
            ["构件用途", member],
            ["截面高度 d", f"{_number(depth)} mm"],
            ["翼缘宽度 bf", f"{_number(bf)} mm"],
            ["腹板厚度 tw", f"{_number(tw)} mm"],
            ["翼缘厚度 tf", f"{_number(tf)} mm"],
            ["截面面积 A", f"{_number(area)} mm²"],
            ["强轴惯性矩 Ix", f"{_number(inertia)} mm⁴"],
            ["弱轴回转半径 ry", f"{_number(ry)} mm"],
            ["腹板净高 h", f"{_number(clear_depth)} mm"],
            ["屈服弯矩 My", f"{_number(moment)} N·mm"],
        ]
        cards.append(
            f'<article class="card"><h3>{html.escape(name)}</h3>{_steel_svg(name, values)}'
            f"{_table(['参数', '数值'], rows)}</article>"
        )
    return "".join(cards)


def _rc_moment_ranges(frame: Any) -> dict[str, tuple[float, float, float, float]]:
    moments: dict[str, list[tuple[float, float]]] = {}
    for floor, names in frame.structural_components.beams.items():
        for name, hinge in zip(names, frame.beam_hinges[floor]):
            moments.setdefault(name, []).append((hinge.my_positive, hinge.my_negative))
    for story, names in frame.structural_components.columns.items():
        for name, hinge in zip(names, frame.column_hinges[story]):
            moments.setdefault(name, []).append((hinge.my_positive, hinge.my_negative))
    return {
        name: (
            min(value[0] for value in values),
            max(value[0] for value in values),
            min(value[1] for value in values),
            max(value[1] for value in values),
        )
        for name, values in moments.items()
    }


def _rc_sections(frame: Any) -> str:
    from .rc_hinge import calculate_rc_hinge

    ranges = _rc_moment_ranges(frame)
    cards = []
    for name, section in frame.structural_components.section_library.items():
        moment = ranges.get(name)
        rows = [
            ["截面宽度 b", f"{_number(section.b)} mm"],
            ["截面高度 h", f"{_number(section.h)} mm"],
            ["净保护层", f"{_number(section.cover)} mm"],
            ["截面面积 A", f"{_number(section.area)} mm²"],
            ["毛截面惯性矩 Ig", f"{_number(section.gross_inertia)} mm⁴"],
            ["顶部纵筋", section.top_bars.canonical()],
            ["底部纵筋", section.bottom_bars.canonical()],
            ["每侧纵筋", section.side_each.canonical()],
            ["箍筋", f"{section.stirrup.canonical()} @ {_number(section.stirrup_spacing)} mm"],
            ["顶部纵筋率", _number(section.top_bars.area / section.area)],
            ["底部纵筋率", _number(section.bottom_bars.area / section.area)],
        ]
        if moment:
            rows.extend(
                [
                    ["模型正向屈服弯矩范围", f"{_number(moment[0])} – {_number(moment[1])} N·mm"],
                    ["模型负向屈服弯矩范围", f"{_number(moment[2])} – {_number(moment[3])} N·mm"],
                ]
            )
        else:
            reference = calculate_rc_hinge(
                section,
                fc=frame.load_and_material.fc_expected,
                ec=frame.load_and_material.elastic_modulus,
                fy=frame.load_and_material.fy_expected,
                es=frame.load_and_material.es,
                length=section.h,
                ei_ratio=1.0,
            )
            rows.extend(
                [
                    ["零轴力参考正向屈服弯矩", f"{_number(reference.my_positive)} N·mm"],
                    ["零轴力参考负向屈服弯矩", f"{_number(reference.my_negative)} N·mm"],
                ]
            )
        cards.append(
            f'<article class="card"><h3>{html.escape(name)}</h3>{_rc_svg(section)}'
            f"{_table(['参数', '数值'], rows)}</article>"
        )
    return "".join(cards)


def write_model_report(frame: Any, path: str | Path) -> Path:
    """Write a self-contained HTML model summary and return its path."""
    output = Path(path)
    is_rc = getattr(frame, "frame_type", None) == "reinforced_concrete"
    geometry_rows = [
        ["模型名称", frame.frame_name],
        ["结构类型", "钢筋混凝土框架" if is_rc else "钢框架"],
        ["层数", frame.N],
        ["跨数", frame.bays],
        ["层高", ", ".join(_number(value) for value in frame.building_geometry.story_height)],
        ["跨度", ", ".join(_number(value) for value in frame.building_geometry.bay_length)],
        ["生成时间", dt.datetime.now().isoformat(timespec="seconds")],
    ]
    if frame.notes:
        geometry_rows.insert(2, ["备注", frame.notes])
    section_cards = _rc_sections(frame) if is_rc else _steel_sections(frame)
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(frame.frame_name)} 建模报告</title>
<style>
body{{font:14px/1.55 system-ui,"Microsoft YaHei",sans-serif;margin:0;background:#f4f6f8;color:#18212b}}
main{{max-width:1200px;margin:auto;padding:28px}} h1{{margin-bottom:4px}} h2{{margin-top:30px}}
.muted{{color:#607080}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:18px}}
.card{{background:white;border:1px solid #dce2e8;border-radius:10px;padding:16px;box-shadow:0 2px 8px #0000000d}}
table{{border-collapse:collapse;width:100%;background:white}} th,td{{border:1px solid #dce2e8;padding:7px 9px;text-align:left}}
th{{background:#eef2f6}} svg{{display:block;width:100%;height:230px}} svg text{{font-size:10px;fill:#334}}
.section{{fill:#90a4ae;stroke:#263238}} .concrete{{fill:#eceff1;stroke:#37474f;stroke-width:2}}
.stirrup{{fill:none;stroke:#1976d2;stroke-width:2}} .bar{{fill:#c62828;stroke:#7f0000;stroke-width:.5}}
</style></head><body><main>
<h1>{html.escape(frame.frame_name)} 建模报告</h1><p class="muted">单位体系：N、mm、t</p>
<h2>模型概况</h2>{_table(["项目", "数值"], geometry_rows)}
<h2>构件布置</h2><div class="grid"><section><h3>梁</h3>{_assignment_table(frame.structural_components.beams, "楼层")}</section>
<section><h3>柱</h3>{_assignment_table(frame.structural_components.columns, "楼层段")}</section></div>
<h2>荷载与材料输入</h2>{_load_material_report(frame)}
<h2>连接与边界输入</h2>{_boundary_report(frame)}
<h2>截面示意与特性</h2><div class="grid">{section_cards}</div>
</main></body></html>"""
    output.write_text(document, encoding="utf-8")
    return output
