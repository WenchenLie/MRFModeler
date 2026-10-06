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
        [18.087020, 27.130530, 27.130530, 18.087020],
        [17.869908, 26.804861, 26.804861, 17.869908],
        [17.635373, 26.453059, 26.453059, 17.635373],
        [17.400838, 26.101257, 26.101257, 17.400838],
        [17.400838, 26.101257, 26.101257, 17.400838],
        [15.301679, 22.952519, 22.952519, 15.301679],
    ],
    leaning_column=[0, 0, 0, 0, 0, 0],
)
loads.set_loads(
    moment_frame=[
        [177.373071e3,266.059607e3, 266.059607e3, 177.373071e3],
        [175.243929e3,262.865893e3, 262.865893e3, 175.243929e3],
        [172.943929e3,259.415893e3, 259.415893e3, 172.943929e3],
        [170.643929e3,255.965893e3, 255.965893e3, 170.643929e3],
        [170.643929e3,255.965893e3, 255.965893e3, 170.643929e3],
        [150.058214e3,225.087321e3, 225.087321e3, 150.058214e3],
    ],
    leaning_column=[0, 0, 0, 0, 0, 0],
)
loads.set_axial_load_ratio_amplification_factor(1.25)
loads.set_material(fc_expected=26.8, ec=32500, fy_expected=400, es=200000, poisson_ratio=0.2)
loads.set_damping_ratio(0.05)
frame.finish_load_and_material()

frame.connection_and_boundary.set_base_support("Fixed")
frame.connection_and_boundary.set_joint_panel_model("Elastic")
frame.finish_connection_and_boundary()
frame.finalize()
frame.generate_scripts(root / f"output/{name}", show_plot=True)
