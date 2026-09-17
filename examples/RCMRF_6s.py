from pathlib import Path

from MRFHelper import RCFrame

root = Path.cwd()
name = "RC_6S3B"
frame = RCFrame(name, notes="Six-story RC frame")

geometry = frame.building_geometry
geometry.story_height = [4300, 4000, 4000, 4000, 4000, 4000]
geometry.bay_length = [6000, 3000, 6000]
frame.finish_building_geometry()

components = frame.structural_components
components.load_sections_csv(root / "examples/RCMRF_6s_sections.csv")
components.set_beams(2, ["beam_out", "beam_in", "beam_out"])
components.set_beams(3, ["beam_out", "beam_in", "beam_out"])
components.set_beams(4, ["beam_out", "beam_in", "beam_out"])
components.set_beams(5, ["beam_out", "beam_in", "beam_out"])
components.set_beams(6, ["beam_out", "beam_in", "beam_out"])
components.set_beams(7, ["beam_out", "beam_in", "beam_out"])
components.set_columns(1, ["col1-3", "col1-3", "col1-3", "col1-3"])
components.set_columns(2, ["col1-3", "col1-3", "col1-3", "col1-3"])
components.set_columns(3, ["col1-3", "col1-3", "col1-3", "col1-3"])
components.set_columns(4, ["col4-6", "col4-6", "col4-6", "col4-6"])
components.set_columns(5, ["col4-6", "col4-6", "col4-6", "col4-6"])
components.set_columns(6, ["col4-6", "col4-6", "col4-6", "col4-6"])
frame.finish_structural_components()

loads = frame.load_and_material
loads.set_masses(
    moment_frame=[
        [14.1276, 21.1913, 21.1913, 14.1276],
        [14.0816, 21.1224, 21.1224, 14.0816],
        [14.0816, 21.1224, 21.1224, 14.0816],
        [14.0816, 21.1224, 21.1224, 14.0816],
        [14.0816, 21.1224, 21.1224, 14.0816],
        [13.4694, 20.2041, 20.2041, 13.4694],
    ],
    leaning_column=[6.0612, 5.5102, 5.5102, 5.5102, 5.5102, 0.0],
)
loads.set_loads(
    moment_frame=[
        [138450, 207675, 207675, 138450],
        [138000, 207000, 207000, 138000],
        [138000, 207000, 207000, 138000],
        [138000, 207000, 207000, 138000],
        [138000, 207000, 207000, 138000],
        [132000, 198000, 198000, 132000],
    ],
    leaning_column=[59400, 54000, 54000, 54000, 54000, 0],
)
loads.set_axial_load_ratio_amplification_factor(1.25)
loads.set_material(fc_expected=26.8, ec=32500, fy_expected=400, es=200000, poisson_ratio=0.2)
frame.finish_load_and_material()

frame.connection_and_boundary.set_base_support("Fixed")
frame.connection_and_boundary.set_joint_panel_model("Elastic")
frame.finish_connection_and_boundary()
frame.finalize()
frame.generate_scripts(root / f"output/{name}", show_plot=True)
