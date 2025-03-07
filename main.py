from MRFHelper import MRFhelper


frame = MRFhelper.from_json(r'test\MRF4S.json')
frame.generate_tcl_script('output')

