from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MRFHelper import Frame
import datetime
import pandas as pd


def write_info(frame: Frame, file_name='Model Information') -> str:

    text = f'Moment resisting frame model information\n'
    text += f'Frame name: {frame.frame_name}\n'
    text += f'Generation time: {datetime.datetime.now()}\n'
    if frame.notes:
        text += f'Notes: {frame.notes}'
    text += 'All units are in [N, mm, t]\n\n\n'

    # 1 building geometry
    text += '-'*15 + ' 1. Building Geometry ' + '-'*15 + '\n\n'
    text += f'Building height: {frame.BuildingGeometry.building_height}\n'
    text += f'Number of story: {frame.N}\n'
    text += f'Number of bays: {frame.bays}\n'
    text += f'Plane dimensions [mm]: {frame.BuildingGeometry.plane_dimensions[0]} x {frame.BuildingGeometry.plane_dimensions[1]}\n'
    text += f'Number of moment frames: {frame.BuildingGeometry.MF_number}\n'
    text += f'External column tributary area [mm]: {frame.BuildingGeometry.exterior_column_tributary_area[0]} x {frame.BuildingGeometry.exterior_column_tributary_area[1]}\n'
    text += f'Internal column tributary area [mm]: {frame.BuildingGeometry.interior_column_tributary_area[0]} x {frame.BuildingGeometry.interior_column_tributary_area[1]}\n\n\n'

    # 2 structural components
    text += '-'*15 + ' 2. Structural Components ' + '-'*15 + '\n\n'
    text += 'Beam sections:\n'
    beam_sections = frame.StructuralComponents.beams
    df_beam = pd.DataFrame.from_dict(beam_sections, orient='index', columns=[f'Bay-{i}' for i in range(1, frame.bays+1)])
    df_beam.insert(0, 'Floor', range(2, frame.N+2))
    text += f'{df_beam.to_string(index=False)}\n\n'
    text += 'Column sections:\n'
    col_sections = frame.StructuralComponents.columns
    df_col = pd.DataFrame.from_dict(col_sections, orient='index', columns=[f'Axis-{i}' for i in range(1, frame.bays+2)])
    df_col.insert(0, 'Story', range(1, frame.N+1))
    text += f'{df_col.to_string(index=False)}\n\n'
    text += f'Stories with column splices: '
    if len(frame.StructuralComponents.column_splice) == 0:
        text += 'None\n\n'
    else:
        splices = ', '.join([str(i) for i in list(frame.StructuralComponents.column_splice)]) + '\n\n'
        text += splices
    text += 'Doubler plate thickness [mm]:\n'
    doubler_plate = frame.StructuralComponents.doubler_plate
    df_dp = pd.DataFrame.from_dict(doubler_plate, orient='index', columns=[f'Axis-{i}' for i in range(1, frame.bays+2)])
    df_dp.insert(0, 'Floor', range(2, frame.N+2))
    text += f'{df_dp.to_string(index=False)}\n\n\n'

    # 3 load and material
    text += '-'*15 + ' 3. Load and Material ' + '-'*15 + '\n\n'
    text += 'Material properties:\n'
    text += f"\tYoung's modulus [MPa]: {frame.LoadAndMaterial.E}\n"
    text += f"\tNominal yield strength of beams [MPa]: {frame.LoadAndMaterial.fy_beam}\n"
    text += f"\tNominal yield strength of columns [MPa]: {frame.LoadAndMaterial.fy_column}\n"
    text += f"\tPossion ratio: {frame.LoadAndMaterial.miu}\n\n"
    text += 'Load [MPa]:\n'
    story_floor = [f'{i-1}/{i}' for i in range(2, frame.N + 2)]
    df = pd.DataFrame(story_floor, columns=['Story/Floor'])
    DL, LL, CL = [], [], []
    for floor in range(2, frame.N + 2):
        story = floor - 1
        DL.append(frame.LoadAndMaterial.dead_load[floor])
        LL.append(frame.LoadAndMaterial.live_load[floor])
        CL.append(frame.LoadAndMaterial.cladding_load[story])
    df['Dead'] = DL
    df['Live'] = LL
    df['Cladding'] = CL
    text += f'{df.to_string(index=False)}\n\n'
    text += 'Load and mass combination coefficients:\n'
    df = pd.DataFrame()
    df['Dead'] = [frame.LoadAndMaterial.cc_weight['Dead'], frame.LoadAndMaterial.cc_mass['Dead']]
    df['Live'] = [frame.LoadAndMaterial.cc_weight['Live'], frame.LoadAndMaterial.cc_mass['Live']]
    df['Cladding'] = [frame.LoadAndMaterial.cc_weight['Cladding'], frame.LoadAndMaterial.cc_mass['Cladding']]
    df.index = ['Weight', 'Mass']
    text += f'{df.to_string()}\n\n'
    text +='Axial compressive ratio of columns:\n'
    df= pd.DataFrame.from_dict(frame.LoadAndMaterial.PPy, orient='index', columns=[f'Axis-{i}' for i in range(1, frame.bays+2)])
    df_col = []
    for i in range(1, frame.N + 1):
        df_col.append(f'{i}b')
        df_col.append(f'{i}t')
    df.insert(0, 'Story', df_col)
    text += f'{df.to_string(index=False)}\n\n'
    total_weight, total_mass = 0, 0
    for floor in range(2, frame.N + 2):
        for axis in range(1, frame.axis + 1):
            id_axis = axis - 1
            total_weight += frame.LoadAndMaterial.F_node[floor][id_axis]
            total_mass += frame.LoadAndMaterial.mass_node[floor][id_axis]
        total_weight += frame.LoadAndMaterial.F_grav[floor]
        total_mass += frame.LoadAndMaterial.mass_grav[floor]
    text += f'Seiemic weight of considered 2D frame: {total_weight/1000:.2f} kN\n'
    text += f'Seiemic mass of considered 2D frame: {total_mass:.2f} t\n\n\n'

    # 4 Connection and boundary condition
    text += '-'*15 + ' 4. Connection and Boundary Condition ' + '-'*15 + '\n\n'
    text += f'Base support: {frame.ConnectionAndBoundary.base_support}\n'
    BC = frame.ConnectionAndBoundary.beam_column_connection
    if BC == 'Full':
        s = 'Fully constrained connection'
    elif BC == 'RBS':
        s = 'Reduced beam section (RBS)'
    elif BC == 'Hinged':
        s = 'Hinged connection'
    text += f'Beam-to-column connection: {s}\n'
    a, b, c = frame.ConnectionAndBoundary.RBS_paras
    if frame.ConnectionAndBoundary.beam_column_connection == 'RBS':
        text += f'Reduced beam section (RBS) parameters: {a}, {b}, {c}\n'
    s = 'Yes (Parallelogram)' if frame.ConnectionAndBoundary.panel_zone_deformation else 'No (Cruciform)'
    text += f'Consider panel zone deformation: {s}\n'

    with open(file_name+'.txt', 'w') as f:
        f.write(text)
    # print(text)
    return text


if __name__ == "__main__":
    print(datetime.datetime.now())

