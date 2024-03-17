from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MRFHelper import Frame
from pathlib import Path
from tkinter import messagebox
import matplotlib.pyplot as plt
from typing import Dict, Tuple, Union, Type
import re


"""
Generate tcl script for time history and pushover analysis using OpenSees
Writen by: Wenchen Lie
2024-03-17
"""

class WriteScript:
    def __init__(self, frame: Frame) -> None:
        self.frame = frame
        self.tcl_script = []
        self.nodes_Id: Dict[int, Tuple[float, float]] = dict()  # {id: (x_coord, y_coord)}
        self.eles_Id: Dict[int, Tuple[int, int]] = dict()  # {id: (iNode, jNode)}
        self.Nlines = 0  # number of lines
        self.Nrecorder = 0  # number of recorders
        self.line_frag = dict()
        self.fig, self.ax = plt.subplots()
        self.write_script()
        self.write_nodes()
        self.write_elements()
        self.write_constraint()
        self.write_recorders()
        self.write_mass()
        self.write_user_comments()
        self.write_eigen()
        self.write_gravity()
        self.write_dynamic_analysis()
        self.write_pushover_analysis()
        self.write_info()
        self.save()

    def write(self, *text):
        """Write a line of text"""
        if len(text) == 1:
            text = str(text[0])
        else:
            text = [str(i) for i in text]
            text = '  '.join(text)
        self.tcl_script.append(text)
        self.Nlines += 1

    def write_script(self):
        frame = self.frame
        frame_name = frame.frame_name
        self.write('# ' + '-'*80)
        s = f' {frame_name} '.center(80, '-')
        self.write('# ' + s)
        self.write('# ' + '-'*80)
        self.write()
        self.write()
        self.write('wipe all;')
        self.write('model basic -ndm 2 -ndf 3;')
        self.write()
        self.write('# Basic model variables')
        self.write('set global RunTime;')
        self.write('set global StartTime;')
        self.write('set global MaxRunTime;')
        self.write('set MaxRunTime 600.0;')
        self.write('set StartTime [clock seconds];')
        self.write('set RunTime 0.0;')
        self.write('set  EQ 1;  # Regular expression anchor')
        self.write('set  PO 0;  # Regular expression anchor')
        self.write('set  ShowAnimation 1;')
        self.write()
        self.write('# Ground motion information')
        self.write('set MainFolder "H:/MRF_results/test/4SMRF";')
        line1 = self.Nlines
        self.write('set GMname "th5";')
        self.write('set SubFolder "th5";')
        self.write('set GMdt 0.01;')
        self.write('set GMpoints 5590;')
        self.write('set GMduration 55.89;')
        self.write('set FVduration 30;')
        self.write('set EqSF 2.0;')
        self.write('set GMFile "GMs/$GMname.th";')
        line2 = self.Nlines
        self.line_frag['gminfo'] = (line1, line2)
        self.write()
        self.write('# Sourcing subroutines')
        self.write('source DisplayModel3D.tcl;')
        self.write('source DisplayPlane.tcl;')
        self.write('source Spring_PZ.tcl;')
        self.write('source Spring_IMK.tcl;')
        self.write('source Spring_Zero.tcl;')
        self.write('source Spring_Rigid.tcl;')
        self.write('source ConstructPanel_Rectangle.tcl;')
        self.write('source DynamicAnalysisCollapseSolverX.tcl;')
        self.write('source PanelZone.tcl')
        self.write('source BeamHinge.tcl')
        self.write('source ColumnHinge.tcl')
        self.write('')
        self.write('# Results folders')
        self.write('file mkdir $MainFolder;')
        self.write('file mkdir $MainFolder/EigenAnalysis;')
        self.write('file mkdir $MainFolder/$SubFolder;')
        self.write()
        self.write('# Basic parameters')
        self.write(f'set NStory {frame.N};')
        self.write(f'set NBay {frame.bays};')
        self.write(f'set E {frame.LoadAndMaterial.E:.2f};')
        self.write(f'set mu {frame.LoadAndMaterial.miu};')
        self.write(f'set fy_beam {frame.LoadAndMaterial.fy_beam:.2f};')
        self.write(f'set fy_column {frame.LoadAndMaterial.fy_column:.2f};')
        self.write('uniaxialMaterial Elastic 9 1.e-9;')
        self.write('uniaxialMaterial Elastic 99 1.e12;')
        self.write('geomTransf Linear 1;')
        self.write('geomTransf PDelta 2;')
        self.write('geomTransf Corotational 3;')
        self.write('set A_Stiff 1.e8;')
        self.write('set I_Stiff 1.e13;')
        self.write('')
        self.write('# Building geometry')
        self.write('set Floor1 0.0;')
        for floor in range(2, frame.N + 2):
            heigth = float(sum(frame.BuildingGeometry.story_height[:floor-1]))
            self.write(f'set Floor{floor} {heigth};')
        self.write()
        self.write('set Axis1 0.0;')
        d = 0
        for i, l_bay in enumerate(frame.BuildingGeometry.bay_length):
            d += l_bay
            self.write(f'set Axis{i+2} {float(d)};')
        self.write(f'set Axis{i+3} {float(d + l_bay)};')
        self.write('')
        self.write(f'set HBuilding {float(frame.BuildingGeometry.building_height)};')
        self.write(f'variable HBuilding {float(frame.BuildingGeometry.building_height)};')
        self.write()
        self.write()


    def write_nodes(self):
        """Write nodes
        * x_axis: x-coords of axes (including leaning column axis)
        * y_floor: y-coords of floor
        """
        frame = self.frame
        x_axis = [0]  # x-coord of axes
        for bay in frame.BuildingGeometry.bay_length:
            x_axis.append(x_axis[-1] + bay)
        x_axis.append(x_axis[-1] + bay)
        y_floor = [0]
        for h in frame.BuildingGeometry.story_height:
            y_floor.append(y_floor[-1] + h)
        s = f' Nodes '.center(80, '-')
        self.write('# ' + s)
        self.write()

        # Support nodes
        self.write('# Support nodes')
        for AA in range(1, len(x_axis) + 1):
            FF = 1
            x = x_axis[AA - 1]
            y = 0
            Id = self.get_id(10, FF, AA, 00)
            self.write(f'node {Id} $Axis{AA} $Floor1;')
            self.node(x, y, Id=Id)
        self.write('')

        # Leaning column grid nodes
        self.write('# Leaning column grid nodes')
        for FF in range(2, self.frame.N + 2):
            AA = self.frame.axis + 1
            x = x_axis[-1]
            y = y_floor[FF - 1]
            Id = self.get_id(10, FF, AA, 00)
            self.write(f'node {Id} $Axis{AA} $Floor{FF};')
            self.node(x, y, Id=Id)
        self.write('')

        # Leaning column connected nodes
        self.write('# Leaning column connected nodes')
        for FF in range(2, self.frame.N + 2):
            AA = self.frame.axis + 1
            x = x_axis[-1]
            y = y_floor[FF - 1]
            Id_t = self.get_id(10, FF, AA, 1)
            Id_b = self.get_id(10, FF, AA, 2)
            if FF != self.frame.N + 1:  # not top floor
                self.write(f'node {Id_b} $Axis{AA} $Floor{FF};')
                self.write(f'node {Id_t} $Axis{AA} $Floor{FF};')
                self.node(x, y, Id=Id_b)
                self.node(x, y, Id=Id_t)
            else:  # top floor
                self.write(f'node {Id_b} $Axis{AA} $Floor{FF};')
                self.node(x, y, Id=Id_b)
        self.write('')
        
        # Moment frame column nodes
        self.write('# Moment frame column nodes')
        for FF in range(1, self.frame.N + 2):
            temp_all = []
            temp_all_b, temp_all_t = [], []
            if FF == 1:
                for AA in range(1, self.frame.axis + 1):
                    x, y = x_axis[AA - 1], 0
                    Id = self.get_id(10, FF, AA, 1)
                    temp_all.append(f'node {Id} $Axis{AA} $Floor{FF};')
                    self.node(x, y, Id=Id)
                self.write(*temp_all)
            elif FF == self.frame.N + 1:
                for AA in range(1, self.frame.axis + 1):
                    if AA == 1:
                        beam_h = self.frame.StructuralComponents.beam_properties[FF][0][1]
                    elif AA == self.frame.axis:
                        beam_h = self.frame.StructuralComponents.beam_properties[FF][-1][1]
                    else:
                        beam_h_left = self.frame.StructuralComponents.beam_properties[FF][AA-2][1]
                        beam_h_right = self.frame.StructuralComponents.beam_properties[FF][AA-1][1]
                        beam_h = (beam_h_left + beam_h_right) / 2
                    x, y = x_axis[AA - 1], y_floor[FF - 1] - beam_h / 2
                    Id = self.get_id(10, FF, AA, 2)
                    temp_all.append(f'node {Id} $Axis{AA} [expr $Floor{FF} - {beam_h:.2f}/2];')
                    self.node(x, y, Id=Id)
                self.write(*temp_all)
            else:
                for AA in range(1, self.frame.axis + 1):
                    if AA == 1:
                        beam_h = self.frame.StructuralComponents.beam_properties[FF][0][1]
                    elif AA == self.frame.axis:
                        beam_h = self.frame.StructuralComponents.beam_properties[FF][-1][1]
                    else:
                        beam_h_left = self.frame.StructuralComponents.beam_properties[FF][AA-2][1]
                        beam_h_right = self.frame.StructuralComponents.beam_properties[FF][AA-1][1]
                        beam_h = (beam_h_left + beam_h_right) / 2
                    x, y_b, y_t = x_axis[AA - 1], y_floor[FF - 1] - beam_h / 2, y_floor[FF - 1] + beam_h / 2
                    Id_b, Id_t = self.get_id(10, FF, AA, 2), self.get_id(10, FF, AA, 1)
                    temp_all_b.append(f'node {Id_b} $Axis{AA} [expr $Floor{FF} - {beam_h:.2f}/2];')
                    temp_all_t.append(f'node {Id_t} $Axis{AA} [expr $Floor{FF} + {beam_h:.2f}/2];')
                    self.node(x, y_b, Id=Id_b)
                    self.node(x, y_t, Id=Id_t)
                self.write(*temp_all_b)
                self.write(*temp_all_t)
        self.write('')

        # Moment frame beam nodes
        self.write('# Moment frame beam nodes')
        for FF in range(2, frame.N + 2):
            write_temp = []
            SS_b = FF - 1
            for BB in range(1, frame.bays + 1):
                h_col_l = frame.StructuralComponents.column_properties[SS_b][BB-1][1]
                h_col_r = frame.StructuralComponents.column_properties[SS_b][BB][1]
                if SS_b in frame.StructuralComponents.column_splice:
                    # If splice exists, column depth is obtained from the upper floor
                    h_col_l = frame.StructuralComponents.column_properties[SS_b+1][BB-1][1]
                    h_col_r = frame.StructuralComponents.column_properties[SS_b+1][BB][1]
                hinge_offset_l = h_col_l/2 + frame.StructuralComponents.RBS_length[FF][(BB-1)*2]
                hinge_offset_r = h_col_r/2 + frame.StructuralComponents.RBS_length[FF][(BB-1)*2+1]
                x_l, x_r, y = x_axis[BB-1]+hinge_offset_l, x_axis[BB]-hinge_offset_r, y_floor[FF-1]
                Id_l, Id_r = self.get_id(10, FF, BB, 4), self.get_id(10, FF, BB+1, 5)
                write_temp.append(f'node {Id_l} [expr $Axis{BB} + {hinge_offset_l:.2f}] $Floor{FF};')
                write_temp.append(f'node {Id_r} [expr $Axis{BB+1} - {hinge_offset_r:.2f}] $Floor{FF};')
                self.node(x_l, y, Id=Id_l)
                self.node(x_r, y, Id=Id_r)
            self.write(*write_temp)
        self.write('')

        # Beam spring nodes
        self.write('# Beam spring nodes (If RBS length equal zero, beam spring nodes will not be generated)')
        for FF in range(2, frame.N + 2):
            write_temp = []
            SS_b = FF - 1
            for BB in range(1, frame.bays + 1):
                h_col_l = frame.StructuralComponents.column_properties[SS_b][BB-1][1]
                h_col_r = frame.StructuralComponents.column_properties[SS_b][BB][1]
                if SS_b in frame.StructuralComponents.column_splice:
                    # If splice exists, column depth is obtained from the upper floor
                    h_col_l = frame.StructuralComponents.column_properties[SS_b+1][BB-1][1]
                    h_col_r = frame.StructuralComponents.column_properties[SS_b+1][BB][1]
                RBS_length_l = frame.StructuralComponents.RBS_length[FF][(BB-1)*2]
                RBS_length_r = frame.StructuralComponents.RBS_length[FF][(BB-1)*2+1]
                hinge_offset_l = h_col_l/2 + RBS_length_l
                hinge_offset_r = h_col_r/2 + RBS_length_r
                x_l, x_r, y = x_axis[BB-1]+hinge_offset_l, x_axis[BB]-hinge_offset_r, y_floor[FF-1]
                Id_l, Id_r = self.get_id(10, FF, BB, 3), self.get_id(10, FF, BB+1, 6)
                if RBS_length_l != 0:
                    write_temp.append(f'node {Id_l} [expr $Axis{BB} + {hinge_offset_l:.2f}] $Floor{FF};')
                    self.node(x_l, y, Id=Id_l)
                if RBS_length_r != 0:
                    write_temp.append(f'node {Id_r} [expr $Axis{BB+1} - {hinge_offset_r:.2f}] $Floor{FF};')
                    self.node(x_r, y, Id=Id_r)
            self.write(*write_temp)
        self.write('')

        # column splice ndoes
        self.write('# Column splice ndoes')
        for SS in range(1, frame.N + 1):
            if SS in frame.StructuralComponents.column_splice:
                write_temp = []
                for AA in range(1, frame.axis + 1):
                    story_height = (frame.BuildingGeometry.story_height[SS - 1])
                    x = x_axis[AA - 1]
                    y = y_floor[SS - 1] + story_height / 2
                    Id = self.get_id(10, SS, AA, 7)
                    write_temp.append(f'node {Id} $Axis{AA} [expr $Floor{SS} + 0.5 * {story_height:.2f}];')
                    self.node(x, y, Id=Id)
                self.write(*write_temp)
        self.write('')

        # beam splice ndoes
        self.write('# Beam splice ndoes')
        for FF in range(2, frame.N + 2):
            # if FF in frame.StructuralComponents.beam_splice:
            write_temp = []
            for BB in range(1, frame.bays + 1):
                if BB in frame.StructuralComponents.beam_splice:
                    x = (x_axis[BB - 1] + x_axis[BB]) / 2
                    y = y_floor[FF - 1]
                    Id = self.get_id(10, FF, BB, 8)
                    bay_length = frame.BuildingGeometry.bay_length[BB - 1]
                    write_temp.append(f'node {Id} [expr $Axis{BB} + {bay_length:.2f} / 2] $Floor{FF};')
                    self.node(x, y, Id=Id)
            self.write(*write_temp)
        self.write('') 
        self.write('')


    def write_elements(self):
        frame = self.frame
        x_axis = [0]  # x-coord of axes
        for bay in frame.BuildingGeometry.bay_length:
            x_axis.append(x_axis[-1] + bay)
        x_axis.append(x_axis[-1] + bay)
        y_floor = [0]  # y-coord of floors
        for h in frame.BuildingGeometry.story_height:
            y_floor.append(y_floor[-1] + h)
        s = f' Elements '.center(80, '-')
        self.write('# ' + s)
        self.write()

        # Stiffness modification
        self.write('set n 10.;')
        self.write()

        # Columns
        self.write('# Column elements')
        E = frame.LoadAndMaterial.E
        for SS in range(1, frame.N + 1):
            write_temp = []
            write_temp_b, write_temp_t = [], []
            for AA in range(1, frame.StructuralComponents.axis + 1):
                A = frame.StructuralComponents.column_properties[SS][AA-1][5]
                I = frame.StructuralComponents.column_properties[SS][AA-1][6]
                if SS not in frame.StructuralComponents.column_splice:
                    # no column splice in this story
                    inode = self.get_id(10, SS, AA, 1)
                    jnode = self.get_id(10, SS + 1, AA, 2)
                    Id = self.get_id(10, SS, AA, 1)
                    write_temp.append(f'element elasticBeamColumn {Id} {inode} {jnode} {A:.2f} $E [expr ($n+1)/$n*{I:.2f}] 2;')
                    self.ele(inode, jnode, 'blue', Id=Id)
                else:
                    # column splices exist in this story
                    inode = self.get_id(10, SS, AA, 1)
                    A_top = frame.StructuralComponents.column_properties[SS+1][AA-1][5]
                    I_top = frame.StructuralComponents.column_properties[SS+1][AA-1][6]
                    midnode = self.get_id(10, SS, AA, 7)
                    jnode = self.get_id(10, SS + 1, AA, 2)
                    Id_b = self.get_id(10, SS, AA, 2)
                    Id_t = self.get_id(10, SS, AA, 3)
                    write_temp_b.append(f'element elasticBeamColumn {Id_b} {inode} {midnode} {A:.2f} $E [expr ($n+1)/$n*{I:.2f}] 2;')
                    write_temp_t.append(f'element elasticBeamColumn {Id_t} {midnode} {jnode} {A_top:.2f} $E [expr ($n+1)/$n*{I_top:.2f}] 2;')
                    self.ele(inode, midnode,  Id=Id_b)
                    self.ele(midnode, jnode,  Id=Id_t)
            if write_temp:
                self.write(*write_temp)
            if write_temp_b:
                self.write(*write_temp_b)
                self.write(*write_temp_t)
        self.write('')

        # beam element
        self.write('# Beam elements')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for BB in range(1, frame.bays + 1):
                A = frame.StructuralComponents.beam_properties[FF][BB-1][5]
                I = frame.StructuralComponents.beam_properties[FF][BB-1][6]
                inode1 = self.get_id(10, FF, BB, 3)
                jnode1 = self.get_id(10, FF, BB + 1, 6)
                inode2 = self.get_id(10, FF, BB, 4)
                jnode2 = self.get_id(10, FF, BB + 1, 5)
                midnode = self.get_id(10, FF, BB, 8)
                if inode1 in self.nodes_Id.keys():
                    inode = inode1
                else:
                    inode = inode2
                if jnode1 in self.nodes_Id.keys():
                    jnode = jnode1
                else:
                    jnode = jnode2
                if int(midnode) in self.nodes_Id.keys():
                    # beam splice exists
                    Id_l = self.get_id(10, FF, BB, 11)
                    Id_r = self.get_id(10, FF, BB, 12)
                    write_temp.append(f'element elasticBeamColumn {Id_l} {inode} {midnode} {A:.2f} $E [expr ($n+1)/$n*{I:.2f}] 2;')
                    write_temp.append(f'element elasticBeamColumn {Id_r} {midnode} {jnode} {A:.2f} $E [expr ($n+1)/$n*{I:.2f}] 2;')
                    self.ele(inode, midnode, Id=Id_l)
                    self.ele(midnode, jnode, Id=Id_r)
                else:
                    # beam splice not exists
                    Id = self.get_id(10, FF, BB, 4)
                    write_temp.append(f'element elasticBeamColumn {Id} {inode} {jnode} {A:.2f} $E [expr ($n+1)/$n*{I:.2f}] 2;')
                    self.ele(inode, jnode, Id=Id)
            self.write(*write_temp)
        self.write('')

        # Panel zones
        self.write('# Panel zones')
        self.write('# PanelNone Floor Axis X Y E mu fy_column A_stiff I_stiff d_col d_beam tp tf bf transfTag type_ position check ""')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for AA in range(1, frame.axis + 1):
                SS = FF - 1
                X = x_axis[AA - 1]
                Y = y_floor[FF - 1]
                if AA == 1 and FF == frame.N + 1:
                    position = 'LT'
                elif AA == frame.axis and FF == frame.N + 1:
                    position = 'RT'
                elif AA == 1 and FF < frame.N + 1:
                    position = 'L'
                elif AA == frame.axis and FF < frame.N + 1:
                    position = 'R'
                elif 1<AA<frame.axis and FF == frame.N + 1:
                    position = 'T'
                else:
                    position = 'I'
                d_col = frame.StructuralComponents.column_properties[SS][AA-1][1]
                bf_col = frame.StructuralComponents.column_properties[SS][AA-1][0]
                tf_col = frame.StructuralComponents.column_properties[SS][AA-1][3]
                if SS in frame.StructuralComponents.column_splice:
                    d_col = frame.StructuralComponents.column_properties[SS+1][AA-1][1]
                    bf_col = frame.StructuralComponents.column_properties[SS+1][AA-1][0]
                    tf_col = frame.StructuralComponents.column_properties[SS+1][AA-1][3]
                if AA == 1:
                    d_beam = frame.StructuralComponents.beam_properties[FF][0][1]
                elif AA == frame.axis:
                    d_beam = frame.StructuralComponents.beam_properties[FF][-1][1]
                else:
                    d_beam_l = frame.StructuralComponents.beam_properties[FF][AA-2][1]
                    d_beam_r = frame.StructuralComponents.beam_properties[FF][AA-1][1]
                    d_beam = (d_beam_l + d_beam_r) / 2
                tp = frame.StructuralComponents.pz_thickness[FF][AA-1]
                type_ = 1 if frame.ConnectionAndBoundary.panel_zone_deformation else 2
                self.add_panel_zone(FF, AA, X, Y, d_col, d_beam, type_, position)
                write_temp.append(f'PanelZone {FF} {AA} $Axis{AA} $Floor{FF} $E $mu $fy_column $A_Stiff $I_Stiff {d_col:.2f} {d_beam:.2f} {tp:.2f} {tf_col:.2f} {bf_col:.2f} 2 {type_} "{position}";')
            self.write(*write_temp)
        self.write()

        # RBS element
        self.write('# RBS elements (If RBS length equal zero, RBS element will not be generated)')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for BB in range(1, frame.bays + 1):
                AA_l, AA_r = BB, BB + 1
                A = frame.StructuralComponents.beam_properties[FF][BB-1][5]
                I = frame.StructuralComponents.beam_properties[FF][BB-1][6]
                # bay left
                inode = self.get_id(11, FF, AA_l, 4)
                jnode = self.get_id(10, FF, AA_l, 3)
                if jnode in self.nodes_Id.keys():
                    Id = self.get_id(10, FF, BB, 5)
                    write_temp.append(f'element elasticBeamColumn {Id} {inode} {jnode} {A:.2f} $E {I:.2f} 2;')
                    self.ele(inode, jnode, Id=Id)
                # right bay
                inode = self.get_id(10, FF, AA_r, 6)
                jnode = self.get_id(11, FF, AA_r, 2)
                if inode in self.nodes_Id.keys():
                    Id = self.get_id(10, FF, BB, 6)
                    write_temp.append(f'element elasticBeamColumn {Id} {inode} {jnode} {A:.2f} $E {I:.2f} 2;')
                    self.ele(inode, jnode, Id=Id)
            self.write(*write_temp)
        self.write()

        # Beam hinge
        self.write('# Beam hinges')
        self.write('# BeamHinge SpringID NodeI NodeJ E fy_beam Ix d htw bftf ry L Ls Lb My type_ {check ""}')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for BB in range(1, frame.bays + 1):
                AA_l, AA_r = BB, BB + 1
                SS_b, SS_t = FF - 1, FF
                Ix = frame.StructuralComponents.beam_properties[FF][BB-1][6]
                d = frame.StructuralComponents.beam_properties[FF][BB-1][1]
                tw = frame.StructuralComponents.beam_properties[FF][BB-1][2]
                h = frame.StructuralComponents.beam_properties[FF][BB-1][8]
                htw = h / tw
                bf = frame.StructuralComponents.beam_properties[FF][BB-1][0]
                tf = frame.StructuralComponents.beam_properties[FF][BB-1][3]
                bftf = bf / (2 * tf)
                ry = frame.StructuralComponents.beam_properties[FF][BB-1][4]
                d_col_l = frame.StructuralComponents.column_properties[SS_b][AA_l-1][1]
                d_col_r = frame.StructuralComponents.column_properties[SS_b][AA_r-1][1]
                if SS_b in frame.StructuralComponents.column_splice:
                    d_col_l = frame.StructuralComponents.column_properties[SS_t][AA_l-1][1]
                    d_col_r = frame.StructuralComponents.column_properties[SS_t][AA_r-1][1]
                bay_length = frame.BuildingGeometry.bay_length[BB-1]
                L = bay_length - (d_col_l + d_col_r) / 2
                Ls, Lb = L / 2, L / 2
                My = frame.StructuralComponents.beam_properties[FF][BB-1][7]
                if frame.ConnectionAndBoundary.beam_column_connection == 'Full':
                    type_ = 2
                elif frame.ConnectionAndBoundary.beam_column_connection == 'RBS':
                    type_ = 1
                elif frame.ConnectionAndBoundary.beam_column_connection == 'Hinged':
                    type_ = 3
                # left hinge
                Id = self.get_id(10, FF, AA_l, 9)
                inode1 = self.get_id(11, FF, AA_l, 4)
                inode2 = self.get_id(10, FF, AA_l, 3)
                if inode2 in self.nodes_Id.keys():
                    # RBS
                    inode = inode2
                else:
                    # Other than RBS
                    inode = inode1
                jnode = self.get_id(10, FF, AA_l, 4)
                write_temp.append(f'BeamHinge {Id} {inode} {jnode} $E $fy_beam {Ix:.2f} {d:.2f} {htw:.2f} {bftf:.2f} {ry:.2f} {L:.1f} {Ls:.1f} {Lb:.1f} {My:.2f} {type_};')
                self.zero_length(inode, jnode, Id=Id)
                # right hinge
                Id = self.get_id(10, FF, AA_r, 10)
                inode = self.get_id(10, FF, AA_r, 5)
                jnode1 = self.get_id(10, FF, AA_r, 6)
                jnode2 = self.get_id(11, FF, AA_r, 2)
                if jnode1 in self.nodes_Id.keys():
                    # RBS
                    jnode = jnode1
                else:
                    # Other than RBS
                    jnode = jnode2
                write_temp.append(f'BeamHinge {Id} {inode} {jnode} $E $fy_beam {Ix:.2f} {d:.2f} {htw:.2f} {bftf:.2f} {ry:.2f} {L:.1f} {Ls:.1f} {Lb:.1f} {My:.2f} {type_};')
                self.zero_length(inode, jnode, Id=Id)
            self.write(*write_temp)
        self.write()

        # column hinges
        self.write('# Column hinges')
        self.write('# Column SpringID NodeI NodeJ E Ix d htw ry L Lb My PPy SF_PPy pinned check ""')
        for SS in range(1, frame.N + 1):
            write_temp_b = []
            write_temp_t = []
            for AA in range(1, frame.axis + 1):
                FF_b, FF_t = SS, SS + 1
                BB_l, BB_r = AA - 1, AA
                Ix_b = frame.StructuralComponents.column_properties[SS][AA-1][6]
                d_b = frame.StructuralComponents.column_properties[SS][AA-1][1]
                tw_b = frame.StructuralComponents.column_properties[SS][AA-1][2]
                h_b = frame.StructuralComponents.column_properties[SS][AA-1][8]
                htw_b = h_b / tw_b
                ry_b = frame.StructuralComponents.column_properties[SS][AA-1][4]
                if SS in frame.StructuralComponents.column_splice:
                    Ix_t = frame.StructuralComponents.column_properties[SS+1][AA-1][6]
                    d_t = frame.StructuralComponents.column_properties[SS+1][AA-1][1]
                    tw_t = frame.StructuralComponents.column_properties[SS+1][AA-1][2]
                    h_t = frame.StructuralComponents.column_properties[SS+1][AA-1][8]
                    htw_t = h_t / tw_t
                    ry_t = frame.StructuralComponents.column_properties[SS+1][AA-1][4]
                else:
                    Ix_t = Ix_b
                    d_t = d_b
                    tw_t = tw_b
                    h_t = h_b
                    htw_t = htw_b
                    ry_t = ry_b
                if FF_b == 1:
                    d_beam_b_l = 0
                    d_beam_b_r = 0
                else:
                    if AA == 1:
                        d_beam_b_l = frame.StructuralComponents.beam_properties[FF_b][0][1]
                        d_beam_b_r = frame.StructuralComponents.beam_properties[FF_b][0][1]
                    elif AA == frame.axis:
                        d_beam_b_l = frame.StructuralComponents.beam_properties[FF_b][-1][1]
                        d_beam_b_r = frame.StructuralComponents.beam_properties[FF_b][-1][1]
                    else:
                        d_beam_b_l = frame.StructuralComponents.beam_properties[FF_b][BB_l-1][1]
                        d_beam_b_r = frame.StructuralComponents.beam_properties[FF_b][BB_r-1][1]
                if AA == 1:
                    d_beam_t_l = frame.StructuralComponents.beam_properties[FF_t][0][1]
                    d_beam_t_r = frame.StructuralComponents.beam_properties[FF_t][0][1]
                elif AA == frame.axis:
                    d_beam_t_l = frame.StructuralComponents.beam_properties[FF_t][-1][1]
                    d_beam_t_r = frame.StructuralComponents.beam_properties[FF_t][-1][1]
                else:
                    d_beam_t_l = frame.StructuralComponents.beam_properties[FF_t][BB_l-1][1]
                    d_beam_t_r = frame.StructuralComponents.beam_properties[FF_t][BB_r-1][1]
                L0 = frame.BuildingGeometry.story_height[SS-1]
                L = L0 - (d_beam_b_l+d_beam_b_r)/4 - (d_beam_t_l+d_beam_t_r)/4
                Lb = L
                My_b = frame.StructuralComponents.column_properties[SS][AA-1][7]
                if SS not in frame.StructuralComponents.column_splice:
                    My_t = My_b
                else:
                    My_t = frame.StructuralComponents.column_properties[SS+1][AA-1][7]
                PPy_b = frame.LoadAndMaterial.PPy[f'{SS}b'][AA-1]
                PPy_t = frame.LoadAndMaterial.PPy[f'{SS}t'][AA-1]
                SF_PPy = frame.LoadAndMaterial.PPy_scale
                Id_b = self.get_id(10, FF_b, AA, 7)
                Id_t = self.get_id(10, FF_t, AA, 8)
                if SS == 1:
                    inode_b = self.get_id(10, FF_b, AA, 0)
                else:
                    inode_b = self.get_id(11, FF_b, AA, 3)
                jnode_b = self.get_id(10, FF_b, AA, 1)
                inode_t = self.get_id(10, FF_t, AA, 2)
                jnode_t = self.get_id(11, FF_t, AA, 1)
                pinned = 1
                if FF_b == 1 and frame.ConnectionAndBoundary.base_support == 'Pinned':
                    pinned = 2
                write_temp_b.append(f'ColumnHinge {Id_b} {inode_b} {jnode_b} $E {Ix_b:.2f} {d_b:.2f} {htw_b:.2f} {ry_b:.2f} {L:.2f} {Lb:.2f} {My_b:.2f} {PPy_b:.4f} {SF_PPy} {pinned};')
                write_temp_t.append(f'ColumnHinge {Id_t} {inode_t} {jnode_t} $E {Ix_t:.2f} {d_t:.2f} {htw_t:.2f} {ry_t:.2f} {L:.2f} {Lb:.2f} {My_t:.2f} {PPy_t:.4f} {SF_PPy} 1;')
                self.zero_length(inode_b, jnode_b, Id=Id_b)
                self.zero_length(inode_t, jnode_t, Id=Id_t)
            self.write(*write_temp_b)
            self.write(*write_temp_t)
        self.write()
                
        # Rigid link
        self.write('# Rigid links')
        for FF in range(2, frame.N + 2):
            BB = frame.bays + 1
            AA_l, AA_r = BB, BB + 1
            Id = self.get_id(10, FF, BB, 4)
            inode = self.get_id(11, FF, AA_l, 4)
            jnode = self.get_id(10, FF, AA_r, 0)
            self.write(f'element truss {Id} {inode} {jnode} $A_Stiff 99;')
            self.ele(inode, jnode, Id=Id)
        self.write()
        
        # Leaning column
        self.write('# Leaning column')
        for SS in range(1, frame.N + 1):
            FF_b, FF_t = SS, SS + 1
            AA = frame.axis + 1
            if SS == 1:
                inode = self.get_id(10, FF_b, AA, 0)
            else:
                inode = self.get_id(10, FF_b, AA, 1)
            jnode = self.get_id(10, FF_t, AA, 2)
            Id = self.get_id(10, SS, AA, 1)
            self.write(f'element elasticBeamColumn {Id} {inode} {jnode} $A_Stiff $E $I_Stiff 2;')
            self.ele(inode, jnode, Id=Id)
        self.write()

        # Leaning column hinges
        self.write('# Leaning column hinges')
        for FF in range(2, frame.N + 2):
            AA = frame.axis + 1
            inode = self.get_id(10, FF, AA, 2)
            jnode = self.get_id(10, FF, AA, 0)
            knode = self.get_id(10, FF, AA, 1)
            Id1 = self.get_id(10, FF, AA, 8)
            Id2 = self.get_id(10, FF, AA, 7)
            self.write(f'Spring_Rigid {Id1} {inode} {jnode};')
            self.ele(inode, jnode, Id=Id1)
            if FF != frame.N + 1:
                self.write(f'Spring_Zero {Id2} {jnode} {knode};')
                self.ele(jnode, knode, Id=Id2)
        self.write()


    def write_constraint(self):
        frame = self.frame
        s = f' Constraints '.center(80, '-')
        self.write('# ' + s)
        self.write()

        # Support
        self.write('# Support')
        for AA in range(1, frame.axis + 2):
            Id = self.get_id(10, 1, AA, 0)
            if AA != frame.axis + 1:
                self.write(f'fix {Id} 1 1 1;')
            else:
                self.write(f'fix {Id} 1 1 0;')
        self.write()

        # soil constraint
        self.write('# Soil constraint')
        if not frame.ConnectionAndBoundary.soil_constraint:
            self.write('# (No soil constraint)')
        for AA in range(1, frame.axis + 1):
            if (AA != 1) and (AA != frame.axis):
                continue
            for FF in frame.ConnectionAndBoundary.soil_constraint:
                if frame.ConnectionAndBoundary.panel_zone_deformation:
                    if AA == 1:
                        Id = self.get_id(11, FF, AA, 2)
                    else:
                        Id = self.get_id(11, FF, AA, 4)
                else:
                    Id = self.get_id(11, FF, AA, 0)
                self.write(f'fix {Id} 1 0 0;')
        self.write()

        # Rigig diaphragm
        self.write('# Rigid diaphragm')
        if not frame.ConnectionAndBoundary.rigid_disphragm:
            self.write('# (Rigid diaphragm was not considered)')
        AA_master = int((frame.axis + 1) / 2)
        AA_slave = []
        for AA in range(1, frame.axis + 1):
            if AA != AA_master:
                AA_slave.append(AA)
        self.control_nodes = []
        for FF in range(2, frame.N + 2):
            write_temp = []
            for AA in AA_slave:
                if frame.ConnectionAndBoundary.panel_zone_deformation == True:
                    inode = self.get_id(11, FF, AA_master, 4)
                    jnode = self.get_id(11, FF, AA, 4)
                else:
                    inode = self.get_id(11, FF, AA_master, 0)
                    jnode = self.get_id(11, FF, AA, 0)
                write_temp.append(f'equalDOF {inode} {jnode} 1;')
            self.control_nodes.append(inode)
            if frame.ConnectionAndBoundary.rigid_disphragm:
                self.write(*write_temp)
        self.write()
        self.AA_master = AA_master  # control axes

    def write_recorders(self):
        frame = self.frame
        s = f' Recorders '.center(80, '-')
        self.write('# ' + s)
        self.write()
        self.write('# Mode properties')
        s = ' '.join([str(i) for i in self.control_nodes])
        for FF in range(2, frame.N + 2):
            self.write(f'recorder Node -file $MainFolder/EigenAnalysis/EigenVectorsMode{FF-1}.out -node {s} -dof 1 "eigen {FF-1}";')
            self.add_recorder()
        self.write()
        self.write('# Time')
        self.write('recorder Node -file $MainFolder/$SubFolder/Time.out -time -node 10010100 -dof 1 disp;')
        self.write()
        self.write('# Support reactions')
        for AA in range(1, frame.axis + 2):
            Id = self.get_id(10, 1, AA, 0)
            if frame.recorders['Reactions']:
                self.write(f'recorder Node -file $MainFolder/$SubFolder/Support{AA}.out -node {Id} -dof 1 2 3 reaction;')
                self.add_recorder()
        self.write()
        self.write('# Story drift ratio')
        for SS in range(1, frame.N + 1):
            if SS == 1:
                inode = 10010100
            else:
                inode = self.control_nodes[SS - 2]
            jnode = self.control_nodes[SS - 1]
            if frame.recorders['Drift']:
                self.write(f'recorder Drift -file $MainFolder/$SubFolder/SDR{SS}_MF.out -iNode {inode} -jNode {jnode} -dof 1 -perpDirn 2;')
                self.add_recorder()
        if frame.recorders['Drift']:
            self.write(f'recorder Drift -file $MainFolder/$SubFolder/SDRALL_MF.out -iNode 10010100 -jNode {jnode} -dof 1 -perpDirn 2;')
            self.add_recorder()
        self.write()
        self.write('# Floor acceleration')
        for FF in range(1, frame.N + 2):
            if FF == 1:
                inode = 10010100
            else:
                inode = self.control_nodes[FF - 2]
            if frame.recorders['FloorAccel']:
                self.write(f'recorder Node -file $MainFolder/$SubFolder/RFA{FF}_MF.out -node {inode} -dof 1 accel;')
                self.add_recorder()
        self.write()
        self.write('# Floor velocity')
        for FF in range(1, frame.N + 2):
            if FF == 1:
                inode = 10010100
            else:
                inode = self.control_nodes[FF - 2]
            if frame.recorders['FloorVel']:
                self.write(f'recorder Node -file $MainFolder/$SubFolder/RFV{FF}_MF.out -node {inode} -dof 1 vel;')
                self.add_recorder()
        self.write()
        self.write('# Floor displacement')
        for FF in range(1, frame.N + 2):
            if FF == 1:
                inode = 10010100
            else:
                inode = self.control_nodes[FF - 2]
            if frame.recorders['FloorDisp']:
                self.write(f'recorder Node -file $MainFolder/$SubFolder/Disp{FF}_MF.out -node {inode} -dof 1 disp;')
                self.add_recorder()
        self.write()
        self.write('# Column forces')
        for SS in range(1, frame.N + 1):
            write_temp = []
            for AA in range(1, frame.axis + 1):
                Id = self.get_id(10, SS, AA, 1)
                if not Id in self.eles_Id.keys():
                    Id = self.get_id(10, SS, AA, 2)
                if frame.recorders['ColumnForce']:
                    write_temp.append(f'recorder Element -file $MainFolder/$SubFolder/Column{SS}{AA}.out -ele {Id} force;')
                    self.add_recorder()
            self.write(*write_temp)
        self.write()
        self.write('# Column springs forces')
        for SS in range(1, frame.N + 1):
            write_temp_b, write_temp_t = [], []
            FF_b, FF_t = SS, SS + 1
            for AA in range(1, frame.axis + 1):
                Id_b = self.get_id(10, FF_b, AA, 7)
                Id_t = self.get_id(10, FF_t, AA, 8)
                if frame.recorders['ColumnHinge']:
                    write_temp_b.append(f'recorder Element -file $MainFolder/$SubFolder/ColSpring{FF_b}{AA}T_F.out -ele {Id_b} force;')
                    write_temp_t.append(f'recorder Element -file $MainFolder/$SubFolder/ColSpring{FF_t}{AA}B_F.out -ele {Id_t} force;')
                    self.add_recorder()
                    self.add_recorder()
            self.write(*write_temp_b)
            self.write(*write_temp_t)
        self.write()
        self.write('# Column springs rotations')
        for SS in range(1, frame.N + 1):
            write_temp_b, write_temp_t = [], []
            FF_b, FF_t = SS, SS + 1
            for AA in range(1, frame.axis + 1):
                Id_b = self.get_id(10, FF_b, AA, 7)
                Id_t = self.get_id(10, FF_t, AA, 8)
                if frame.recorders['ColumnHinge']:
                    write_temp_b.append(f'recorder Element -file $MainFolder/$SubFolder/ColSpring{FF_b}{AA}T_D.out -ele {Id_b} deformation;')
                    write_temp_t.append(f'recorder Element -file $MainFolder/$SubFolder/ColSpring{FF_t}{AA}B_D.out -ele {Id_t} deformation;')
                    self.add_recorder()
                    self.add_recorder()
            self.write(*write_temp_b)
            self.write(*write_temp_t)
        self.write()
        self.write('# Beam springs forces')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for BB in range(1, frame.bays + 1):
                AA_l, AA_r = BB, BB + 1
                Id_l = self.get_id(10, FF, AA_l, 9)
                Id_r = self.get_id(10, FF, AA_r, 10)
                if frame.recorders['BeamHinge']:
                    write_temp.append(f'recorder Element -file $MainFolder/$SubFolder/BeamSpring{FF}{AA_l}R_F.out -ele {Id_l} force;')
                    write_temp.append(f'recorder Element -file $MainFolder/$SubFolder/BeamSpring{FF}{AA_r}L_F.out -ele {Id_r} force;')
                    self.add_recorder()
                    self.add_recorder()
            self.write(*write_temp)
        self.write()
        self.write('# Beam springs rotations')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for BB in range(1, frame.bays + 1):
                AA_l, AA_r = BB, BB + 1
                Id_l = self.get_id(10, FF, AA_l, 9)
                Id_r = self.get_id(10, FF, AA_r, 10)
                if frame.recorders['BeamHinge']:
                    write_temp.append(f'recorder Element -file $MainFolder/$SubFolder/BeamSpring{FF}{AA_l}R_D.out -ele {Id_l} deformation;')
                    write_temp.append(f'recorder Element -file $MainFolder/$SubFolder/BeamSpring{FF}{AA_r}L_D.out -ele {Id_r} deformation;')
                    self.add_recorder()
                    self.add_recorder()
            self.write(*write_temp)
        self.write()
        self.write('# Panel zone spring forces (if any)')
        for FF in range(2, frame.N + 2):
            if not frame.ConnectionAndBoundary.panel_zone_deformation:
                break
            write_temp = []
            for AA in range(1, frame.axis + 1):
                Id = self.get_id(11, FF, AA, 0)
                if frame.recorders['PanelZone']:
                    write_temp.append(f'recorder Element -file $MainFolder/$SubFolder/PZ{FF}{AA}_F.out -ele {Id} force;')
                    self.add_recorder()
            self.write(*write_temp)
        self.write()
        self.write('# Panel zone spring deforamtions (if any)')
        for FF in range(2, frame.N + 2):
            if not frame.ConnectionAndBoundary.panel_zone_deformation:
                break
            write_temp = []
            for AA in range(1, frame.axis + 1):
                Id = self.get_id(11, FF, AA, 0)
                if frame.recorders['PanelZone']:
                    write_temp.append(f'recorder Element -file $MainFolder/$SubFolder/PZ{FF}{AA}_D.out -ele {Id} deformation;')
                    self.add_recorder()
            self.write(*write_temp)
        self.write()


    def write_mass(self):
        frame = self.frame
        s = f' Mass '.center(80, '-')
        self.write('# ' + s)
        self.write()
        self.write('# Moment frame mass')
        self.write('set g 9810.0;')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for AA in range(1, frame.axis + 1):
                if frame.ConnectionAndBoundary.panel_zone_deformation == True:
                    Id = self.get_id(11, FF, AA, 4)
                else:
                    Id = self.get_id(11, FF, AA, 0)
                mass = frame.LoadAndMaterial.mass_node[FF][AA-1]
                write_temp.append(f'mass {Id} {mass:.3f} 1.e-9 1.e-9;')
            self.write(*write_temp)
        self.write()
        self.write('# Leaning column mass')
        for FF in range(2, frame.N + 2):
            AA = frame.axis + 1
            Id = self.get_id(10, FF, AA, 0)
            mass = frame.LoadAndMaterial.mass_grav[FF]
            self.write(f'mass {Id} {mass:.3f} 1.e-9 1.e-9;')
        self.write()
        self.write()


    def write_user_comments(self):
        uesr_commands = self.frame.UserComment.additional_commands
        if not uesr_commands:
            return
        s = f' User comments '.center(80, '-')
        self.write('# ' + s)
        self.write()
        for command in uesr_commands:
            type_ = list(command.keys())[0]
            if type_ == 'node':
                paras = command['node'].strip(';').split(' ')
                Id, x, y = int(paras[1]), float(paras[2]), float(paras[3])
                if Id in self.nodes_Id.keys():
                    print(f'User command warning: node {Id} was already existed')
                self.node(x, y, Id=Id, c='orange')
                self.write(command['node'])
            elif type_ == 'mat':
                self.write(command['mat'])
            elif type_ == 'ele':
                paras = command['ele'].strip(';').split(' ')
                Id, inode, jnode = int(paras[2]), int(paras[3]), int(paras[4])
                if Id in self.eles_Id.keys():
                    print(f'User command warning: element {Id} was already existed')
                self.ele(inode, jnode, Id=Id, c='orange')
                self.write(command['ele'])
            elif type_ == 'any':
                self.write(command['any'])
        self.write()


    def write_eigen(self):
        frame = self.frame
        s = f' Eigen analysis '.center(80, '-')
        self.write('# ' + s)
        self.write()
        self.write('set pi [expr 2.0*asin(1.0)];')
        self.write(f'set nEigen {frame.N}')
        self.write(f'set lambdaN [eigen [expr $nEigen]];')
        for SS in range(1, frame.N + 1):
            self.write(f'set lambda{SS} [lindex $lambdaN {SS-1}];')
        for SS in range(1, frame.N + 1):
            self.write(f'set w{SS} [expr pow($lambda{SS}, 0.5)];')
        for SS in range(1, frame.N + 1):
            self.write(f'set T{SS} [expr round(2.0*$pi/$w{SS} *1000.)/1000.];')
        for SS in range(1, frame.N + 1):
            self.write(f'puts "T{SS} = $T{SS} s";')
            if SS == 3:
                break
        self.write()
        self.write('set fileX [open "$MainFolder/EigenAnalysis/EigenPeriod.out" w];')
        for SS in range(1, frame.N + 1):
            self.write(f'puts $fileX $T{SS};')
        self.write('close $fileX;')
        self.write()
        self.write()

    def write_gravity(self):
        frame = self.frame
        s = f' Static gravity analysis '.center(80, '-')
        self.write('# ' + s)
        self.write()
        self.write('pattern Plain 100 Linear {')
        self.write()
        self.write('    # Moment frame loads')
        for FF in range(2, frame.N + 2):
            write_temp = []
            for AA in range(1, frame.axis + 1):
                load = -frame.LoadAndMaterial.F_node[FF][AA-1]
                Id = self.get_id(11, FF, AA, 1)
                write_temp.append(f'    load {Id} 0. {load:.1f} 0.;')
            self.write(*write_temp)
        self.write()
        self.write('    # gravity frame loads')
        for FF in range(2, frame.N + 2):
            load = -frame.LoadAndMaterial.F_grav[FF]
            AA = frame.axis + 1
            Id = self.get_id(10 , FF, AA, 0)
            self.write(f'    load {Id} 0. {load:.1f} 0.;')
        self.write()
        self.write('}')
        self.write()
        self.write('constraints Plain;')
        self.write('numberer RCM;')
        self.write('system BandGeneral;')
        self.write('test NormDispIncr 1.0e-5 60;')
        self.write('algorithm Newton;')
        self.write('integrator LoadControl 0.1;')
        self.write('analysis Static;')
        self.write('analyze 10;')
        self.write('loadConst -time 0.0;')
        self.write()
        self.write()


    def write_dynamic_analysis(self):
        frame = self.frame
        s = f' Time history analysis '.center(80, '-')
        self.write('# ' + s)
        self.write()
        self.write('if {$ShowAnimation == 1} {DisplayModel3D DeformedShape 5.00 100 100 1600 1000};')
        self.write()
        self.write('if {$EQ == 1} {')
        self.write('')
        self.write('    # Rayleigh damping')
        self.write('    set zeta 0.02;')
        self.write('    set a0 [expr $zeta*2.0*$w1*$w3/($w1 + $w3)];')
        self.write('    set a1 [expr $zeta*2.0/($w1 + $w3)];')
        self.write('    set a1_mod [expr $a1*(1.0+$n)/$n];')
        beam_Ids = []
        for FF in range(2, frame.N + 2):
            for BB in range(1, frame.bays + 1):
                Id = self.get_id(10, FF, BB, 4)
                if Id in self.eles_Id.keys():
                    beam_Ids.append(str(Id))
                else:
                    Id_l = self.get_id(10, FF, BB, 11)
                    Id_r = self.get_id(10, FF, BB, 12)
                    beam_Ids.append(str(Id_l))
                    beam_Ids.append(str(Id_r))
        beam_Ids = ' '.join(beam_Ids)
        self.write(f'    set beam_Ids [list {beam_Ids}];')
        col_Ids = []
        for SS in range(1, frame.N + 1):
            for AA in range(1, frame.axis + 1):
                Id = self.get_id(10, SS, AA, 1)
                if Id in self.eles_Id.keys():
                    col_Ids.append(str(Id))
                else:
                    Id_b = self.get_id(10, SS, AA, 2)
                    Id_t = self.get_id(10, SS, AA, 3)
                    col_Ids.append(str(Id_b))
                    col_Ids.append(str(Id_t))
        col_Ids = ' '.join(col_Ids)
        self.write(f'    set column_Ids [list {col_Ids}];')
        mass_Ids = []
        for FF in range(2, frame.N + 2):
            for AA in range(1, frame.N + 1):
                if frame.ConnectionAndBoundary.panel_zone_deformation == True:
                    Id = self.get_id(11, FF, AA, 4)
                else:
                    Id = self.get_id(11, FF, AA, 0)
                mass_Ids.append(str(Id))
        for FF in range(2, frame.N + 2):
            Id = self.get_id(10, FF, frame.axis + 1, 0)
            mass_Ids.append(str(Id))
        mass_Ids = ' '.join(mass_Ids)
        self.write(f'    set mass_Ids [list {mass_Ids}];')
        self.write('    # region 1 -ele {*}$beam_Ids -rayleigh 0.0 0.0 $a1_mod 0.0;')
        self.write('    # region 2 -ele {*}$column_Ids -rayleigh 0.0 0.0 $a1_mod 0.0;')
        self.write('    # region 3 -ele {*}$mass_Ids -rayleigh $a0 0.0 0.0 0.0;')
        self.write('    rayleigh $a0 0.0 $a1 0.0;')
        self.write('')
        self.write('    # Ground motion acceleration file input')
        self.write('    set AccelSeries "Series -dt $GMdt -filePath $GMFile -factor [expr $EqSF * $g]";')
        self.write('    pattern UniformExcitation 200 1 -accel $AccelSeries;')
        MF_nodes = ' '.join([str(i) for i in self.control_nodes])
        self.write(f'    set MF_FloorNodes [list {MF_nodes}];')
        self.write('    set GMduration [expr $GMdt*$GMpoints];')
        self.write('    set NumSteps [expr round(($GMduration + $FVduration)/$GMdt)];')
        self.write('    set totTime [expr $GMdt*$NumSteps]; ')
        self.write('    set dtAnalysis [expr 1.0*$GMdt]; ')
        story_1, story_typ = frame.BuildingGeometry.story_height[0], frame.BuildingGeometry.story_height[1]
        self.write(f'    DynamicAnalysisCollapseSolverX $GMdt $dtAnalysis $totTime $NStory 0.15 $MF_FloorNodes $MF_FloorNodes {story_1:.1f} {story_typ:.1f} 1 $StartTime $MaxRunTime $GMname;')
        self.write('')
        self.write('}')
        self.write('')
        self.write('')


    def write_pushover_analysis(self):
        frame = self.frame
        s = f' Pushover analysis '.center(80, '-')
        self.write('# ' + s)
        self.write()
        self.write('if {$PO == 1} {')
        self.write()
        for FF in range(2, frame.N + 2):
            mass = sum(frame.LoadAndMaterial.mass_node[FF])
            mass += frame.LoadAndMaterial.mass_grav[FF]
            self.write(f'    set m{FF} {mass:.3f};')
        self.write()
        self.write('    set file [open "$MainFolder/EigenAnalysis/EigenVectorsMode1.out" r];')
        self.write('    set first_line [gets $file];')
        self.write('    close $file')
        self.write('    set mode_list [split $first_line];')
        for FF in range(2, frame.N + 2):
            self.write(f'    set F{FF} [expr $m{FF} * [lindex $mode_list {FF-2}]];')
        self.write('    pattern Plain 222 Linear {')
        for FF in range(2, frame.N + 2):
            Id = self.control_nodes[FF - 2]
            self.write(f'        load {Id} $F{FF} 0.0 0.0;')
        self.write('    };')
        self.write(f'    set CtrlNode {self.control_nodes[-1]};')
        self.write('    set CtrlDOF 1;')
        self.write(f'    set Dmax [expr 0.100*$Floor{frame.N+1}];')
        self.write('    set Dincr [expr 0.5];')
        self.write('    set Nsteps [expr int($Dmax/$Dincr)];')
        self.write('    set ok 0;')
        self.write('    set controlDisp 0.0;')
        self.write('    source LibAnalysisStaticParameters.tcl;')
        self.write('    source SolutionAlgorithm.tcl;')
        self.write()
        self.write('}')
        self.write()
        self.write('wipe all;')
        

    def write_info(self):
        frame = self.frame
        self.write()
        s = f' Building information '.center(80, '-')
        self.write('# ' + s)
        self.write('#')
        text = frame.builiding_info
        lines = text.split('\n')
        for line in lines:
            self.write('# ' + line)
        self.write()
        self.write()


    def add_panel_zone(self, Floor, Axis, X, Y, d_col, d_beam, type_, position):
        """Construct panel zone model"""
        # node ID
        node_C = 11000000 + Floor*10000 + Axis*100  # 11FFAA01
        node_B = node_C + 1  # 11FFAA01
        node_L = node_C + 2  # 11FFAA02
        node_T = node_C + 3  # 11FFAA03
        node_R = node_C + 4  # 11FFAA04
        node_BL = node_C + 5  # 11FFAA05
        node_LB = node_C + 6  # 11FFAA06
        node_LT = node_C + 7  # 11FFAA07
        node_TL = node_C + 8  # 11FFAA08
        node_TR = node_C + 9  # 11FFAA09
        node_RT = node_C + 10  # 11FFAA10
        node_RB = node_C + 11  # 11FFAA11
        node_BR = node_C + 12  # 11FFAA12
        # Construct nodes
        c = 'green'
        if type_ == 1:
            self.node(X, Y-0.5*d_beam, c, Id=node_B)
            self.node(X+0.5*d_col, Y, c, Id=node_R)
            self.node(X, Y+0.5*d_beam, c, Id=node_T)
            self.node(X-0.5*d_col, Y, c, Id=node_L)
        elif type_ == 2:
            self.node(X, Y-0.5*d_beam, c, Id=node_B)
            self.node(X+0.5*d_col, Y, c, Id=node_R)
            if position != "L" and position != "LT":
                self.node(X-0.5*d_col, Y, c, Id=node_L)
            if position != "T" and position != "LT" and position != "RT":
                self.node(X, Y+0.5*d_beam, c, Id=node_T)
        if type_ == 1:
            self.node(X - 0.5 * d_col, Y - 0.5 * d_beam, c, node_BL)
            self.node(X - 0.5 * d_col, Y - 0.5 * d_beam, c, node_LB)
            self.node(X - 0.5 * d_col, Y + 0.5 * d_beam, c, node_LT)
            self.node(X - 0.5 * d_col, Y + 0.5 * d_beam, c, node_TL)
            self.node(X + 0.5 * d_col, Y + 0.5 * d_beam, 'red', node_TR)
            self.node(X + 0.5 * d_col, Y + 0.5 * d_beam, 'red', node_RT)
            self.node(X + 0.5 * d_col, Y - 0.5 * d_beam, c, node_RB)
            self.node(X + 0.5 * d_col, Y - 0.5 * d_beam, c, node_BR)
        elif type_ == 2:
            self.node(X, Y, c, node_C)
        # Rigid elements ID
        ele_B = 11000000 + Floor * 10000 + Axis * 100 + 1
        ele_L = ele_B + 1
        ele_T = ele_B + 2
        ele_R = ele_B + 3
        ele_BL = 11000000 + Floor * 10000 + Axis * 100 + 1
        ele_LB = ele_BL + 1
        ele_LT = ele_BL + 2
        ele_TL = ele_BL + 3
        ele_TR = ele_BL + 4
        ele_RT = ele_BL + 5
        ele_RB = ele_BL + 6
        ele_BR = ele_BL + 7
        # Construct rigid elements
        if type_ == 1:
            self.ele(node_B, node_BL, c, ele_BL)
            self.ele(node_LB, node_L, c, ele_LB)
            self.ele(node_L, node_LT, c, ele_LT)
            self.ele(node_TL, node_T, c, ele_TL)
            self.ele(node_T, node_TR, c, ele_TR)
            self.ele(node_RT, node_R, c, ele_RT)
            self.ele(node_R, node_BR, c, ele_RB)
            self.ele(node_BR, node_B, c, ele_BR)
        elif type_ == 2:
            self.ele(node_C, node_B, c, ele_B)
            self.ele(node_C, node_R, c, ele_R)
            if position != "L" and position != "LT":
                self.ele(node_C, node_L, c, ele_L)
            if position != "T" and position != "LT" and position != "RT":
                self.ele(node_C, node_T, c, ele_T)
        # panel zone spring
        if type_ == 1:
            Id = 11000000 + Floor * 10000 + Axis * 100
            self.zero_length(node_TR, node_RT, 'red', Id)


    def get_id(self, *aa: int):
        """Get ndoe or element id by combined the number"""
        res = ''
        for a in aa:
            if a < 10:
                a = f'0{a}'
            else:
                a = str(a)
            res += a
        return int(res)

    def node(self, x: float | int, y: float | int, c: str='black', Id: int=None, size=2):
        self.ax.plot(x, y, 'o', color=c, markersize=size)
        if Id:
            if Id in self.nodes_Id.keys():
                print('----- Waring -----')
                print(f'Node id {Id} already exists')
            else:
                self.nodes_Id[int(Id)] = (x, y)
    
    def ele(self, iNode: int, jNode: int, c: str='blue', Id: int=None):
        xi, yi = self.get_coord(iNode)
        xj, yj = self.get_coord(jNode)
        self.ax.plot([xi, xj], [yi, yj], color=c, lw=1)
        if Id:
            if Id in self.eles_Id.keys():
                print('----- Waring -----')
                print(f'Element id {Id} already exists')
            else:
                self.eles_Id[Id] = (iNode, jNode)

    def zero_length(self, iNode: int, jNode: int, c: str='red', Id: int=None, size=7):
        xi, yi = self.get_coord(iNode)
        xj, yj = self.get_coord(jNode)
        if (xi != xj) or (yi != yj):
            raise ValueError(f'[Error 2] Coordinates of zero length element node are different\n{iNode}: ({xi}, {yi})\n{jNode}: ({xj}, {yj})')
        self.ax.plot(xi, yi, color=c, markersize=size, zorder=99999)
        self.ax.plot(xj, yj, color=c, markersize=size, zorder=99999)
        if Id:
            if Id in self.eles_Id.keys():
                print('----- Waring -----')
                print(f'Element id {Id} already exists')
            else:
                self.eles_Id[Id] = (iNode, jNode)


    def get_coord(self, Id: int) -> Tuple[float, float]:
        """get note coordinate through a given node Id"""
        Id = int(Id)
        if not Id in self.nodes_Id.keys():
            print('----- Waring -----')
            print(f'Node id {Id} not exists')
            raise ValueError(f'Node id {Id} not exists')
        return self.nodes_Id[int(Id)]

    def add_recorder(self):
        self.Nrecorder += 1

    def save(self):
        model_name = self.frame.frame_name
        plt.savefig(f'{model_name}.png', dpi=1200)
        plt.show()
        # TODO
        # if Path(f'{model_name}.tcl').exists:
        #     res = messagebox.askquestion('Warnning', f'"{model_name}.tcl" already exists. Do you want to overwrite it?')
        #     if res == 'yes':
        #         pass
        #     else:
        #         print('The tcl script was not generated!')
        #         return
        text_to_write = '\n'.join(self.tcl_script)
        with open(f'{model_name}.tcl', 'w') as f:
            f.write(text_to_write)
        if self.Nrecorder < 512:
            print('\n----------------- Success -----------------------')
        else:
            print('\n----------------- Warning -----------------------')
        print('The tcl script was generated successfully')
        if self.Nrecorder >= 512:
            print(f'----- However, the number of recorders ({self.Nrecorder}) exceed the limit of operating system,')
            print('      which may result in the inability to read ground motion files.')
            print('      It suggested to cancel the defination of some unimportant recorders.')
        line1 = self.line_frag['gminfo'][0]
        line2 = self.line_frag['gminfo'][1]
        print(f'The user still need to modify lines {line1} - {line2} to difine the ground motion information')
        print('The generated files as follow:')
        path_ = Path(f'{model_name}.tcl').absolute()
        print(f'{path_}')
        path_ = Path(f'{model_name}.png').absolute()
        print(f'{path_}')
        path_ = path_.parent / 'Model Information.txt'
        print(f'{path_}')
        print('-------------------------------------------------\n')


