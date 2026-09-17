"""Tcl/OpenSeesPy writer for reinforced-concrete frames."""

from __future__ import annotations

import os
from pathlib import Path

from .write_script import ScriptWriter, _plain_number


class RCScriptWriter(ScriptWriter):
    """Generate an OpenSAS-compatible RC model while preserving steel tag rules."""

    def write_script(self):
        super().write_script()
        py_replacements = {
            "from subroutines.BeamHinge import BeamHinge": (
                "from subroutines.RCHinge import RCHinge"
            ),
            "from subroutines.ColumnHinge import ColumnHinge": "",
            "from subroutines.PanelZone import PanelZone": (
                "from subroutines.RCJoint2D import RCJoint2D"
            ),
        }
        tcl_replacements = {
            "source PanelZone.tcl": "source RCJoint2D.tcl",
            "source BeamHinge.tcl": "source RCHinge.tcl",
            "source ColumnHinge.tcl": "",
        }
        self.py_script = [py_replacements.get(line, line) for line in self.py_script]
        self.tcl_script = [tcl_replacements.get(line, line) for line in self.tcl_script]

    def _write_imk_hinge(self, subroutine, tag, inode, jnode, parameters, *, reverse=False) -> None:
        args = parameters.subroutine_arguments(reverse=reverse)
        args_tcl = " ".join(_plain_number(value) for value in args)
        args_py = ", ".join(_plain_number(value) for value in args)
        self.write(f"{subroutine} {tag} {inode} {jnode} {args_tcl};")
        self.writepy(f"{subroutine}({tag}, {inode}, {jnode}, {args_py})")
        self.zero_length(inode, jnode, element_id=tag)

    def _write_joint_row(self, floor: int, x_axis: list[float], y_floor: list[float]) -> None:
        """Create one floor of Joint2D assemblies inside the column-hinge block."""
        frame = self.frame
        components = frame.structural_components
        story = floor - 1
        row_tcl = []
        row_python = []
        for axis in range(1, frame.axis + 1):
            x, y = x_axis[axis - 1], y_floor[floor - 1]
            column_depth = components.column_sections[story][axis - 1].h
            beam_depth = frame._joint_beam_depth(floor, axis)
            center = self.get_id(11, floor, axis, 0)
            node_b = self.get_id(11, floor, axis, 1)
            node_l = self.get_id(11, floor, axis, 2)
            node_t = self.get_id(11, floor, axis, 3)
            node_r = self.get_id(11, floor, axis, 4)
            material = frame.joint_materials[f"{floor}:{axis}"]
            material_args_tcl = " ".join(_plain_number(value) for value in material.arguments)
            material_args_py = ", ".join(_plain_number(value) for value in material.arguments)
            fixed_tcl = ""
            fixed_python = ""
            if material.panel_model == "Pinching4":
                fixed_tcl = (
                    " $RCPinchingReloadDisp $RCPinchingReloadForce "
                    "$RCPinchingUnloadForce $RCPinchingDegradation "
                    "$RCPinchingEnergyCapacity $RCPinchingDamageType"
                )
                fixed_python = (
                    ", RCPinchingReloadDisp, RCPinchingReloadForce, "
                    "RCPinchingUnloadForce, RCPinchingDegradation, "
                    "RCPinchingEnergyCapacity, RCPinchingDamageType"
                )
            row_tcl.append(
                f"RCJoint2D {center} {node_b} {node_r} {node_t} {node_l} "
                f"$Axis{axis} $Floor{floor} {_plain_number(column_depth)} "
                f"{_plain_number(beam_depth)} {material.panel_model} "
                f"{material_args_tcl}{fixed_tcl};"
            )
            row_python.append(
                f"RCJoint2D({center}, {node_b}, {node_r}, {node_t}, {node_l}, "
                f"Axis{axis}, Floor{floor}, {_plain_number(column_depth)}, "
                f"{_plain_number(beam_depth)}, "
                f'"{material.panel_model}", {material_args_py}{fixed_python})'
            )
            coordinates = (
                (node_b, x, y - beam_depth / 2),
                (node_r, x + column_depth / 2, y),
                (node_t, x, y + beam_depth / 2),
                (node_l, x - column_depth / 2, y),
            )
            for node_id, node_x, node_y in coordinates:
                self.node(node_x, node_y, "green", node_id=node_id)
            self.node(x, y, "green", node_id=center)
            self.joint2d(center, node_b, node_r, node_t, node_l, element_id=center)
        self.write(*row_tcl)
        self.writepy(*row_python)

    def write_elements(self):
        frame = self.frame
        components = frame.structural_components
        loads = frame.load_and_material
        title = " Elements ".center(80, "-")
        self.write("# " + title)
        self.writepy("# " + title)
        self.write("set n 10.;")
        self.writepy("n = 10.")
        if any(material.panel_model == "Pinching4" for material in frame.joint_materials.values()):
            self.write("# Fixed Pinching4 cyclic parameters")
            self.write("set RCPinchingReloadDisp 0.25;")
            self.write("set RCPinchingReloadForce 0.25;")
            self.write("set RCPinchingUnloadForce 0.0;")
            self.write("set RCPinchingDegradation 0.0;")
            self.write("set RCPinchingEnergyCapacity 10.0;")
            self.write("set RCPinchingDamageType energy;")
            self.writepy("# Fixed Pinching4 cyclic parameters")
            self.writepy("RCPinchingReloadDisp = 0.25")
            self.writepy("RCPinchingReloadForce = 0.25")
            self.writepy("RCPinchingUnloadForce = 0.0")
            self.writepy("RCPinchingDegradation = 0.0")
            self.writepy("RCPinchingEnergyCapacity = 10.0")
            self.writepy('RCPinchingDamageType = "energy"')
        self.write()
        self.writepy()

        x_axis = [0.0]
        for length in frame.building_geometry.bay_length:
            x_axis.append(x_axis[-1] + length)
        y_floor = [0.0]
        for height in frame.building_geometry.story_height:
            y_floor.append(y_floor[-1] + height)

        self.write("# RC column elastic elements")
        self.writepy("# RC column elastic elements")
        for story in range(1, frame.N + 1):
            row_tcl = []
            row_python = []
            for axis, section in enumerate(components.column_sections[story], start=1):
                column_ei_ratio = loads.column_ei_ratios[story][axis - 1]
                inode = self.get_id(10, story, axis, 1)
                jnode = self.get_id(10, story + 1, axis, 2)
                tag = self.get_id(10, story, axis, 1)
                row_tcl.append(
                    f"element elasticBeamColumn {tag} {inode} {jnode} "
                    f"{_plain_number(section.area)} $E "
                    f"[expr ($n+1)/$n*{_plain_number(column_ei_ratio)}*"
                    f"{_plain_number(section.gross_inertia)}] 2;"
                )
                row_python.append(
                    f'ops.element("elasticBeamColumn", {tag}, {inode}, {jnode}, '
                    f"{_plain_number(section.area)}, E, "
                    f"(n+1)/n*{_plain_number(column_ei_ratio)}*"
                    f"{_plain_number(section.gross_inertia)}, 2)"
                )
                self.ele(inode, jnode, element_id=tag)
            self.write(*row_tcl)
            self.writepy(*row_python)
        self.write()
        self.writepy()

        self.write("# RC beam elastic elements")
        self.writepy("# RC beam elastic elements")
        for floor in range(2, frame.N + 2):
            row_tcl = []
            row_python = []
            for bay, section in enumerate(components.beam_sections[floor], start=1):
                inode = self.get_id(10, floor, bay, 4)
                jnode = self.get_id(10, floor, bay + 1, 5)
                tag = self.get_id(10, floor, bay, 4)
                row_tcl.append(
                    f"element elasticBeamColumn {tag} {inode} {jnode} "
                    f"{_plain_number(section.area)} $E "
                    f"[expr ($n+1)/$n*{_plain_number(loads.beam_ei_ratio)}*"
                    f"{_plain_number(section.gross_inertia)}] 2;"
                )
                row_python.append(
                    f'ops.element("elasticBeamColumn", {tag}, {inode}, {jnode}, '
                    f"{_plain_number(section.area)}, E, "
                    f"(n+1)/n*{_plain_number(loads.beam_ei_ratio)}*"
                    f"{_plain_number(section.gross_inertia)}, 2)"
                )
                self.ele(inode, jnode, element_id=tag)
            self.write(*row_tcl)
            self.writepy(*row_python)
        self.write()
        self.writepy()

        self.write("# RC beam-column joints (nodes, material, and Joint2D element)")
        self.writepy("# RC beam-column joints (nodes, material, and Joint2D element)")
        if any(material.panel_model == "Pinching4" for material in frame.joint_materials.values()):
            self.write("# Pinching4 envelopes below were calculated from MCFT during generation")
            self.writepy("# Pinching4 envelopes below were calculated from MCFT during generation")
        for story in range(1, frame.N + 1):
            self._write_joint_row(story + 1, x_axis, y_floor)
        self.write()
        self.writepy()

        self.write("# RC beam IMK hinges")
        self.writepy("# RC beam IMK hinges")
        for floor in range(2, frame.N + 2):
            tcl_start, python_start = len(self.tcl_script), len(self.py_script)
            for bay, parameters in enumerate(frame.beam_hinges[floor], start=1):
                left_axis, right_axis = bay, bay + 1
                left_tag = self.get_id(10, floor, left_axis, 9)
                self._write_imk_hinge(
                    "RCHinge",
                    left_tag,
                    self.get_id(11, floor, left_axis, 4),
                    self.get_id(10, floor, left_axis, 4),
                    parameters,
                )
                right_tag = self.get_id(10, floor, right_axis, 10)
                self._write_imk_hinge(
                    "RCHinge",
                    right_tag,
                    self.get_id(10, floor, right_axis, 5),
                    self.get_id(11, floor, right_axis, 2),
                    parameters,
                    reverse=True,
                )
            tcl_row = self.tcl_script[tcl_start:]
            python_row = [line.removeprefix("    ") for line in self.py_script[python_start:]]
            del self.tcl_script[tcl_start:]
            del self.py_script[python_start:]
            self.write(*tcl_row)
            self.writepy(*python_row)
        self.write()
        self.writepy()

        self.write("# RC column IMK hinges")
        self.writepy("# RC column IMK hinges")
        for story in range(1, frame.N + 1):
            bottom_tcl = []
            bottom_python = []
            top_tcl = []
            top_python = []
            for axis, parameters in enumerate(frame.column_hinges[story], start=1):
                bottom_tag = self.get_id(10, story, axis, 7)
                inode_b = (
                    self.get_id(10, story, axis, 0)
                    if story == 1
                    else self.get_id(11, story, axis, 3)
                )
                jnode_b = self.get_id(10, story, axis, 1)
                if story == 1 and frame.connection_and_boundary.base_support == "Pinned":
                    bottom_tcl.append(f"Spring_Zero {bottom_tag} {inode_b} {jnode_b};")
                    bottom_python.append(f"Spring_Zero({bottom_tag}, {inode_b}, {jnode_b})")
                    self.zero_length(inode_b, jnode_b, element_id=bottom_tag)
                else:
                    start_tcl, start_python = len(self.tcl_script), len(self.py_script)
                    self._write_imk_hinge("RCHinge", bottom_tag, inode_b, jnode_b, parameters)
                    bottom_tcl.extend(self.tcl_script[start_tcl:])
                    bottom_python.extend(
                        line.removeprefix("    ") for line in self.py_script[start_python:]
                    )
                    del self.tcl_script[start_tcl:]
                    del self.py_script[start_python:]
                top_tag = self.get_id(10, story + 1, axis, 8)
                start_tcl, start_python = len(self.tcl_script), len(self.py_script)
                self._write_imk_hinge(
                    "RCHinge",
                    top_tag,
                    self.get_id(10, story + 1, axis, 2),
                    self.get_id(11, story + 1, axis, 1),
                    parameters,
                    reverse=True,
                )
                top_tcl.extend(self.tcl_script[start_tcl:])
                top_python.extend(
                    line.removeprefix("    ") for line in self.py_script[start_python:]
                )
                del self.tcl_script[start_tcl:]
                del self.py_script[start_python:]
            self.write(*bottom_tcl)
            self.writepy(*bottom_python)
            self.write(*top_tcl)
            self.writepy(*top_python)
        self.write()
        self.writepy()

        self.write("# Rigid links to leaning column")
        self.writepy("# Rigid links to leaning column")
        for floor in range(2, frame.N + 2):
            bay = frame.bays + 1
            tag = self.get_id(10, floor, bay, 4)
            inode = self.get_id(11, floor, frame.axis, 4)
            jnode = self.get_id(10, floor, frame.axis + 1, 0)
            self.write(f"element truss {tag} {inode} {jnode} $A_Stiff 99;")
            self.writepy(f'ops.element("truss", {tag}, {inode}, {jnode}, A_Stiff, 99)')
            self.ele(inode, jnode, element_id=tag)

        self.write()
        self.writepy()
        self.write("# Leaning column")
        self.writepy("# Leaning column")
        for story in range(1, frame.N + 1):
            axis = frame.axis + 1
            inode = self.get_id(10, story, axis, 0 if story == 1 else 1)
            jnode = self.get_id(10, story + 1, axis, 2)
            tag = self.get_id(10, story, axis, 1)
            self.write(f"element elasticBeamColumn {tag} {inode} {jnode} $A_Stiff $E $I_Stiff 2;")
            self.writepy(
                f'ops.element("elasticBeamColumn", {tag}, {inode}, {jnode}, A_Stiff, E, I_Stiff, 2)'
            )
            self.ele(inode, jnode, element_id=tag)
        for floor in range(2, frame.N + 2):
            axis = frame.axis + 1
            inode = self.get_id(10, floor, axis, 2)
            center = self.get_id(10, floor, axis, 0)
            top = self.get_id(10, floor, axis, 1)
            primary_tag = self.get_id(10, floor, axis, 8)
            secondary_tag = self.get_id(10, floor, axis, 7)
            self.write(f"Spring_Rigid {primary_tag} {inode} {center};")
            self.writepy(f"Spring_Rigid({primary_tag}, {inode}, {center})")
            self.zero_length(inode, center, element_id=primary_tag)
            if floor != frame.N + 1:
                self.write(f"Spring_Zero {secondary_tag} {center} {top};")
                self.writepy(f"Spring_Zero({secondary_tag}, {center}, {top})")
                self.zero_length(center, top, element_id=secondary_tag)
        self.write()
        self.writepy()

    def write_constraint(self):
        frame = self.frame
        title = " Constraints ".center(80, "-")
        self.write("# " + title)
        self.writepy("# " + title)
        self.write("# Support")
        self.writepy("# Support")
        for axis in range(1, frame.axis + 2):
            tag = self.get_id(10, 1, axis, 0)
            fixity = "1 1 0" if axis == frame.axis + 1 else "1 1 1"
            fixity_py = "1, 1, 0" if axis == frame.axis + 1 else "1, 1, 1"
            self.write(f"fix {tag} {fixity};")
            self.writepy(f"ops.fix({tag}, {fixity_py})")
        self.write()
        self.writepy()

        self.write("# Soil constraints")
        self.writepy("# Soil constraints")
        for floor in frame.connection_and_boundary.soil_constraint:
            self.write(f"fix {self.get_id(11, floor, 1, 2)} 1 0 0;")
            self.writepy(f"ops.fix({self.get_id(11, floor, 1, 2)}, 1, 0, 0)")
            self.write(f"fix {self.get_id(11, floor, frame.axis, 4)} 1 0 0;")
            self.writepy(f"ops.fix({self.get_id(11, floor, frame.axis, 4)}, 1, 0, 0)")
        self.write()
        self.writepy()

        self.write("# Rigid diaphragm on ordinary beam-end nodes")
        self.writepy("# Rigid diaphragm on ordinary beam-end nodes")
        master_axis = int((frame.axis + 1) / 2)
        self.control_nodes = []
        for floor in range(2, frame.N + 2):
            master_position = 4 if master_axis <= frame.bays else 5
            master = self.get_id(10, floor, master_axis, master_position)
            self.control_nodes.append(master)
            if frame.connection_and_boundary.rigid_diaphragm:
                for axis in range(1, frame.axis + 1):
                    if axis == master_axis:
                        continue
                    slave_position = 4 if axis <= frame.bays else 5
                    slave = self.get_id(10, floor, axis, slave_position)
                    self.write(f"equalDOF {master} {slave} 1;")
                    self.writepy(f"ops.equalDOF({master}, {slave}, 1)")
        self.master_axis = master_axis
        self.write()
        self.writepy()

    def write_recorders(self):
        tcl_start, py_start = len(self.tcl_script), len(self.py_script)
        super().write_recorders()
        for index in range(tcl_start, len(self.tcl_script)):
            if "PZ" in self.tcl_script[index]:
                self.tcl_script[index] = self.tcl_script[index].replace(
                    "material 1 stressStrain", "material 5 stressStrain"
                )
        for index in range(py_start, len(self.py_script)):
            if "PZ" in self.py_script[index]:
                self.py_script[index] = self.py_script[index].replace(
                    '"material", 1, "stressStrain"', '"material", 5, "stressStrain"'
                )

    def write_mass(self):
        frame = self.frame
        title = " Mass ".center(80, "-")
        self.write("# " + title)
        self.writepy("# " + title)
        self.write("set g 9810.0;")
        self.writepy("g = 9810.0")

        # Tcl resolves mass-vector length from each target node.
        self.write("# Moment frame mass")
        for floor in range(2, frame.N + 2):
            row_tcl = []
            for axis in range(1, frame.axis + 1):
                tag = self.get_id(11, floor, axis, 0)
                mass = frame.load_and_material.moment_frame_node_mass[floor][axis - 1]
                row_tcl.append(f"mass {tag} {_plain_number(mass)} 1.e-9 1.e-9 1.e-9;")
            self.write(*row_tcl)
        self.write()
        self.write("# Leaning column mass")
        for floor in range(2, frame.N + 2):
            tag = self.get_id(10, floor, frame.axis + 1, 0)
            mass = frame.load_and_material.leaning_column_node_mass[floor]
            self.write(f"mass {tag} {_plain_number(mass)} 1.e-9 1.e-9;")

        # OpenSeesPy 3.8 cannot assign mass to Joint2D's internally created
        # four-DOF center node while the frame BasicBuilder has three DOFs.
        # Place the same nodal masses on the adjacent ordinary beam nodes; the
        # stiff translational directions of the zeroLength hinge carry their
        # horizontal inertia into the corresponding joint.
        self.writepy("# Moment frame mass")
        for floor in range(2, frame.N + 2):
            row_python = []
            for axis in range(1, frame.axis + 1):
                position = 4 if axis <= frame.bays else 5
                tag = self.get_id(10, floor, axis, position)
                mass = frame.load_and_material.moment_frame_node_mass[floor][axis - 1]
                row_python.append(f"ops.mass({tag}, {_plain_number(mass)}, 1.e-9, 1.e-9)")
            self.writepy(";  ".join(row_python))
        self.writepy()
        self.writepy("# Leaning column mass")
        for floor in range(2, frame.N + 2):
            tag = self.get_id(10, floor, frame.axis + 1, 0)
            mass = frame.load_and_material.leaning_column_node_mass[floor]
            self.writepy(f"ops.mass({tag}, {_plain_number(mass)}, 1.e-9, 1.e-9)")
        self.write()
        self.writepy()

    def write_eigen(self):
        """Run eigen analysis only when TH damping needs it.

        OpenSeesPy's ARPACK implementation is unstable for Joint2D domains on
        Windows even when PO/CP do not need eigenvalues.  Static analyses use
        a deterministic height-proportional pattern; TH retains the ordinary
        eigen solution and its period/mode output.
        """
        py_start = len(self.py_script)
        super().write_eigen()
        block = self.py_script[py_start:]
        del self.py_script[py_start:]
        for index, line in enumerate(block):
            if "mode_list = mode.copy()" not in line:
                continue
            indentation = line[: len(line) - len(line.lstrip())]
            block[index : index + 1] = [
                f"{indentation}roof_component = mode[-1]",
                f"{indentation}if abs(roof_component) <= 1.e-12:",
                f'{indentation}    raise RuntimeError("RC first-mode roof component is zero")',
                f"{indentation}mode_list = [value / roof_component for value in mode]",
            ]
            break
        self.py_script.append('    if analysis_type == "TH":')
        self.py_script.extend("    " + line if line else "" for line in block)
        mode_values = ", ".join(f"Floor{floor} / HBuilding" for floor in range(2, self.frame.N + 2))
        self.py_script.extend(
            [
                "    else:",
                f"        mode_list = [{mode_values}]",
                "        for i in range(1, NStory + 1):",
                '            np.savetxt(MainFolder/SubFolder/f"mode{i}.out", mode_list)',
                f'        np.savetxt(MainFolder/SubFolder/"Period.out", [float("nan")] * {self.frame.N})',
                "",
            ]
        )

    def write_dynamic_analysis(self):
        tcl_start, py_start = len(self.tcl_script), len(self.py_script)
        super().write_dynamic_analysis()
        frame = self.frame
        damping_mode = min(3, frame.N)
        if damping_mode != 3:
            for index in range(tcl_start, len(self.tcl_script)):
                self.tcl_script[index] = self.tcl_script[index].replace("$w3", f"$w{damping_mode}")
            for index in range(py_start, len(self.py_script)):
                self.py_script[index] = self.py_script[index].replace("w3", f"w{damping_mode}")
        mass_ids = [
            self.get_id(11, floor, axis, 0)
            for floor in range(2, frame.N + 2)
            for axis in range(1, frame.axis + 1)
        ]
        mass_ids.extend(
            self.get_id(10, floor, frame.axis + 1, 0) for floor in range(2, frame.N + 2)
        )
        tcl_values = " ".join(str(value) for value in mass_ids)
        py_values = ", ".join(str(value) for value in mass_ids)
        for index, line in enumerate(self.tcl_script):
            if line.strip().startswith("set mass_Ids"):
                indentation = line[: len(line) - len(line.lstrip())]
                self.tcl_script[index] = f"{indentation}set mass_Ids [list {tcl_values}];"
        for index, line in enumerate(self.py_script):
            if line.strip().startswith("mass_Ids ="):
                indentation = line[: len(line) - len(line.lstrip())]
                self.py_script[index] = f"{indentation}mass_Ids = [{py_values}]"

    def _scale_lateral_pattern(self, tcl_start: int, py_start: int) -> None:
        """Convert modal mass loads from tonnes to the model's Newton units."""
        for index in range(tcl_start, len(self.tcl_script)):
            line = self.tcl_script[index]
            if line.strip().startswith("set F") and " * [lindex $mode_list" in line:
                self.tcl_script[index] = line.replace(
                    " * [lindex $mode_list", " * $g * [lindex $mode_list"
                )
        for index in range(py_start, len(self.py_script)):
            line = self.py_script[index]
            if line.strip().startswith("F") and " * mode_list[" in line:
                self.py_script[index] = line.replace(" * mode_list[", " * g * mode_list[")

    def write_pushover_analysis(self):
        tcl_start, py_start = len(self.tcl_script), len(self.py_script)
        super().write_pushover_analysis()
        self._scale_lateral_pattern(tcl_start, py_start)

    def write_cyclic_pushover(self):
        tcl_start, py_start = len(self.tcl_script), len(self.py_script)
        super().write_cyclic_pushover()
        self._scale_lateral_pattern(tcl_start, py_start)

    def save(self) -> dict[str, Path]:
        output = self.frame.output_path
        components = self.frame.structural_components
        if components.section_path is None:
            raise ValueError("RC script generation requires a source section CSV file")
        section_config = self.frame.dict_info["structural_components"]
        original_section_csv = section_config["section_csv"]
        try:
            serialized_csv = Path(os.path.relpath(components.section_path, output)).as_posix()
        except ValueError:
            # Windows cannot form a relative path across drive letters.
            serialized_csv = components.section_path.as_posix()
        section_config["section_csv"] = serialized_csv
        try:
            paths = super().save()
        finally:
            section_config["section_csv"] = original_section_csv
        return paths
