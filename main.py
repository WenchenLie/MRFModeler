from MRFHelper import MRFhelper


frame = MRFhelper.from_json(r'test\3SRockingFrame.json')
frame.generate_tcl_script('output')

