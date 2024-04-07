from MRFHelper import MRFhelper


# frame = MRFhelper.Repository('3S_Benchmark')
# frame.generate_tcl_script('output')


frame = MRFhelper.Repository('4SMRF_AE')
# frame.StructuralComponents.set_beam_splice(1, 2, 3)

frame.generate_tcl_script('test')


