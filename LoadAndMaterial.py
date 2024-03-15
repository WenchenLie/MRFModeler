from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MRFHelper import Frame
import numpy as np
import func


class LoadAndMaterial:
    g = 9800

    def __init__(self, frame: Frame) -> None:
        self.N = frame.N
        self.bays = frame.bays
        self.axis = frame.axis
        self.dead_load = dict()  # Necessary
        self.live_load = dict()  # Necessary
        self.cladding_load = dict()  # Unnecessary
        self.E = None  # Necessary
        self.fy = None  # Necessary
        self.miu = 0.3  # Unnecessary
        self.cc_weight = dict()  # Combination coefficients of seismic weight, necessary
        self.cc_mass = dict()  # Combination coefficients of seismic mass, necessary


    def set_dead_load(self, floor: list[int], load_per_area: list[int | float]):
        """Step-3:
        Set dead load for each floor

        Args:
            floor (list[int]): Numbers of floor
            load_per_area (list[int | float]): Values of dead load (surface load)
        """
        func.check_list(floor, length=self.N, name='floor')
        for val in floor:
            func.check_int(val, [2, self.N + 1], name='floor')
        func.check_list(load_per_area, length=self.N, name='load_per_area')
        for _, (a, b) in enumerate(zip(floor, load_per_area)):
            self.dead_load[a] = b


    def set_live_load(self, floor: list[int], load_per_area: list[int | float]):
        """Set live load for each floor

        Args:
            floor (list[int]): Numbers of floor
            load_per_area (list[int | float]): Values of live load (surface load)
        """
        func.check_list(floor, length=self.N, name='floor')
        for val in floor:
            func.check_int(val, [2, self.N + 1], name='floor')
        func.check_list(load_per_area, length=self.N, name='load')
        for _, (a, b) in enumerate(zip(floor, load_per_area)):
            self.live_load[a] = b


    def set_cladding_load(self, story: list[int], load_per_area: list[int | float]):
        """Set cladding load for each story

        Args:
            story (list[int]): Numbers of story
            load_per_area (list[int | float]): Values of cladding load (surface load)
        """
        func.check_list(story, length=self.N, name='story')
        for val in story:
            func.check_int(val, [1, self.N], name='story')
        func.check_list(load_per_area, length=self.N, name='load')
        for _, (a, b) in enumerate(zip(story, load_per_area)):
            self.cladding_load[a] = b


    def set_material(self, youngs_modulus: int | float, nominal_strength: int | float, miu: float=0.3):
        """Set material properties for all steel components

        Args:
            youngs_modulus (int | float): Youngs modulus
            nominal_strength (int | float): Nominal yield strength
            miu (float, optional): possion ratio
        """
        func.check_int_float(youngs_modulus, name='youngs_modulus')
        func.check_int_float(nominal_strength, name='nominal_strength')
        func.check_int_float(miu, [0, 0.5], name='miu')
        self.E = youngs_modulus
        self.fy = nominal_strength
        self.miu = miu


    def set_weight_combination_coefficients(self, coefficients: dict):
        """Set seicmic weight combination coefficients  
        Note: Load type should be within ['Dead', 'Live', 'Cladding']

        Args:
            coefficients (dict): {load type: combination coefficient}
        """
        func.check_dict(coefficients, name='coefficients')
        for key, val in coefficients.items():
            if not key in ['Dead', 'Live', 'Cladding']:
                raise ValueError("Load type should be within ['Dead', 'Live', 'Cladding']")
            func.check_int_float(val, name='coefficient')
            self.cc_weight[key] = val


    def set_mass_combination_coefficients(self, coefficients: dict):
        """Set seicmic mass combination coefficients  
        Note: Load type should be within ['Dead', 'Live', 'Cladding']

        Args:
            coefficients (dict): {load type: combination coefficient}
        """
        func.check_dict(coefficients, name='coefficients')
        for key, val in coefficients.items():
            if not key in ['Dead', 'Live', 'Cladding']:
                raise ValueError("Load type should be within ['Dead', 'Live', 'Cladding']")
            func.check_int_float(val, name='coefficient')
            self.cc_mass[key] = val


    def _finished(self):
        if self.E is None:
            raise ValueError("Young's modulus has not been difined")
        if self.fy is None:
            raise ValueError("Nominal yield strength has not been difined")
        if not self.cc_weight:
            raise ValueError("Combination coefficients of seismic weight have not been difined")
        if not self.cc_mass:
            raise ValueError("Combination coefficients of seismic mass have not been difined")
        floor_set = set([2 + i for i in range(self.N)])
        floor_defined_dead = set(self.dead_load.keys())
        floor_defined_live = set(self.live_load.keys())
        if floor_set == floor_defined_dead:
            return
        if floor_set - floor_defined_dead:
            raise ValueError(f'Dead load for floor {floor_set - floor_defined_dead} have not been defined')
        if floor_defined_dead - floor_set:
            raise ValueError(f'Floor {floor_defined_dead - floor_set} are not existed')
        if floor_set - floor_defined_live:
            raise ValueError(f'Dead load for floor {floor_set - floor_defined_live} have not been defined')
        if floor_defined_live - floor_set:
            raise ValueError(f'Floor {floor_defined_live - floor_set} are not existed')
        self._calculate_load()
        

    def _calculate_load(self, frame: Frame):
        """Calculate load and mass
        * F_node (dict): Beam-column joint force ({floor: force})
        * F_grav (dect): Leaning column joint force ({floor: force})
        * mass_node (dict): Beam-column joint mass ({floor: mass})
        * mass_grav (dect): Leaning column joint mass ({floor: mass})
        """
        plane_dimensions = frame.BuildingGeometry.plane_dimensions
        N_MF = frame.BuildingGeometry.MF_number
        area_ex = frame.BuildingGeometry.exterior_column_tributary_area
        area_in = frame.BuildingGeometry.interior_column_tributary_area
        h_list = frame.BuildingGeometry.story_height
        # dead load
        DL_node = dict()
        DL_grav = dict()
        S_3D = plane_dimensions[0] * plane_dimensions[1]  # area of 3D building plane
        for floor, DL_value in self.dead_load.items():
            DL_3D = S_3D * DL_value  # Dead load (N) for each floor of the 3D building
            DL = DL_3D / N_MF  # Dead load (N) for each floor of the 2D considered frame
            r_rest = 1
            DL_floor = []
            for id_axis in range(self.axis):
                if id_axis == 0 or id_axis == self.axis - 1:
                    r = area_ex[0] * area_ex[1] / (S_3D / N_MF)  # area ratio for external columns
                else:
                    r = area_in[0] * area_in[1] / (S_3D / N_MF)  # area ratio for internal columns
                r_rest -= r
                DL_floor.append(DL * r)
            DL_grav[floor] = DL * r_rest
            DL_node[floor] = DL_floor
        # live load (same as the dead load)
        LL_node = dict()
        LL_grav = dict()
        S_3D = plane_dimensions[0] * plane_dimensions[1]  # area of 3D building plane
        for floor, LL_value in self.live_load.items():
            LL_3D = S_3D * LL_value  # Dead load (N) for each floor of the 3D building
            LL = LL_3D / N_MF  # Dead load (N) for each floor of the 2D considered frame
            r_rest = 1
            LL_floor = []
            for id_axis in range(self.axis):
                if id_axis == 0 or id_axis == self.axis - 1:
                    r = area_ex[0] * area_ex[1] / (S_3D / N_MF)  # area ratio for external columns
                else:
                    r = area_in[0] * area_in[1] / (S_3D / N_MF)  # area ratio for internal columns
                r_rest -= r
                LL_floor.append(LL * r)
            LL_grav[floor] = LL * r_rest
            LL_node[floor] = LL_floor
        # cladding load
        CL_node = dict()
        CL_grav = dict()
        for story, CL_value in self.cladding_load.items():
            floor = story + 1
            story_b, story_t = floor - 1, floor  # story number
            CL_floor = []
            h = h_list[story_b-1]/2 if floor==self.N+1 else (h_list[story_b-1] + h_list[story_t-1])/2  # tributary heigth of each floor
            S_rest = plane_dimensions[0] * h
            for id_axis in range(self.axis):
                if id_axis == 0 or id_axis == self.axis - 1:  # if external node
                    if floor == self.N + 1:  # if top floor
                        S_node = area_ex[0] * h_list[story_b-1] / 2  # Node tributary facade area
                    else:
                        S_node = area_ex[0] * (h_list[story_b-1] + h_list[story_t-1]) / 2  # Node tributary facade area
                else:
                    if floor == self.N + 1:  # if top floor
                        S_node = area_in[0] * h_list[story_b-1] / 2  # Node tributary facade area
                    else:
                        S_node = area_in[0] * (h_list[story_b-1] + h_list[story_t-1]) / 2  # Node tributary facade area
                S_rest -= S_node
                CL_floor.append(S_node * CL_value)
            CL_node[floor] = CL_floor
            CL_grav[floor] = S_rest * CL_value + plane_dimensions[1] * h * CL_value  # Consider the Y-direction cladding load
            # CL_grav[floor] = S_rest * CL_value   # TODO Did not consider the Y-direction cladding load
        # node force
        F_node = dict()
        F_grav = dict()
        mass_node = dict()
        mass_grav = dict()
        for floor in range(2, 2 + self.N):
            DL_floor = np.array(DL_node[floor])
            LL_floor = np.array(LL_node[floor])
            CL_floor = np.array(CL_node[floor])
            F_floor = DL_floor * self.cc_weight['Dead'] + LL_floor * self.cc_weight['Live'] + CL_floor + self.cc_weight['Cladding']
            mass_floor = (DL_floor * self.cc_mass['Dead'] + LL_floor * self.cc_mass['Live'] + CL_floor + self.cc_mass['Cladding']) / self.g
            F_floor = list(F_floor)
            mass_floor = list(mass_floor)
            F_node[floor] = F_floor
            mass_node[floor] = mass_floor
            F_grav[floor] = DL_grav[floor] * self.cc_weight['Dead'] + LL_grav[floor] * self.cc_weight['Live'] + CL_grav[floor] * self.cc_weight['Cladding']
            mass_grav[floor] = (DL_grav[floor] * self.cc_mass['Dead'] + LL_grav[floor] * self.cc_mass['Live'] + CL_grav[floor] * self.cc_mass['Cladding']) / self.g
        # TODO Beam and column component masses have not been considered, but FM2D also did not consider.
        self.F_node, self.F_grav, self.mass_node, self.mass_grav = F_node, F_grav, mass_node, mass_grav
            

    def _calculate_PPy(self, frame: Frame, PPy_scale: float=1.25):
        """Calculate the axial compression ratio of columns
        * PPy (dict): Compression ratio ({story: ratio})
        * PPy_scale (float): Scale factor of compression ratio to consider the overturning effect,
        defaults to 1.25

        Args:
            PPy_scale (float, optional): Scale factor of compression ratio, defaults to 1.25.
        """
        props_col = frame.StructuralComponents.column_properties
        P_col = dict()  # Axial forces of columns
        P_temp = np.zeros(self.axis)
        for story in list(1+i for i in range(self.N))[::-1]:
            floor = story + 1
            P_temp += np.array(self.F_node[floor])
            P_col[story] = P_temp.tolist()
        PPy = dict()  # Column axial compression ratio
        for story in range(1, self.N + 1):
            prop_floor = props_col[story]  # column properties for each story
            PPy_story_b, PPy_story_t = [], []
            for axis in range(1, self.axis + 1):
                id_axis = axis - 1
                A = prop_floor[id_axis][5]  # Cross section aera of column
                P = P_col[story][id_axis]  # Axial force of column
                PPy_story_b.append(P / (A * self.fy))  # Axial compression ratio of columns on the story
                if story not in frame.StructuralComponents.column_splice:
                    PPy_story_t.append(P / (A * self.fy))  # Axial compression ratio of columns on the story
                else:
                    A_t = props_col[story+1][id_axis][5]  # Cross section aera of column
                    PPy_story_t.append(P / (A_t * self.fy))  # Axial compression ratio of columns on the story
            PPy[f'{story}b'] = PPy_story_b
            PPy[f'{story}t'] = PPy_story_t
        self.PPy, self.PPy_scale = PPy, PPy_scale

                

