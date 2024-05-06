from MRFHelper import MRFhelper


frame = MRFhelper.load_example('MRF4S_AS')
frame.StructuralComponents.set_beam_splice(1, 3)
frame.generate_tcl_script('output')


