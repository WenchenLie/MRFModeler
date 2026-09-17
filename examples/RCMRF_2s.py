"""Two-story, two-bay RC frame example using N, mm, and t units."""

from pathlib import Path

from MRFHelper import RCFrame

root = Path.cwd()
name = "RC_2S2B"
frame = RCFrame(name, notes="Two-story RC frame")

geometry = frame.building_geometry
geometry.story_height = [3600, 3300]
geometry.bay_length = [6000, 6000]
geometry.plane_dimensions = (12000, 6000)
geometry.mf_number = 2
geometry.exterior_column_tributary_area = (3000, 3000)
geometry.interior_column_tributary_area = (6000, 3000)
frame.finish_building_geometry()

components = frame.structural_components
components.load_sections_csv(root / "examples/RCMRF_2s_sections.csv")
components.set_beams(2, ["S250x500", "S250x500"])
components.set_beams(3, ["S250x500", "S250x500"])
components.set_columns(1, ["S350x350", "S350x350", "S350x350"])
components.set_columns(2, ["S300x300", "S300x300", "S300x300"])
frame.finish_structural_components()

loads = frame.load_and_material
loads.set_masses(
    moment_frame=[[7.4847, 14.9694, 7.4847], [6.9337, 13.8673, 6.9337]],
    leaning_column=[2.1122, 1.0102],
)
loads.set_loads(
    moment_frame=[[73350, 146700, 73350], [67950, 135900, 67950]],
    leaning_column=[20700, 9900],
)
loads.set_axial_load_ratio_amplification_factor(1.25)
loads.set_material(fc_expected=40, ec=30000, fy_expected=460, es=200000, poisson_ratio=0.2)
frame.finish_load_and_material()

frame.connection_and_boundary.set_base_support("Fixed")
frame.connection_and_boundary.set_joint_panel_model("Rigid")
frame.finish_connection_and_boundary()
frame.finalize()
frame.generate_scripts(root / f"output/{name}", show_plot=True)
