from MRFHelper import MRFhelper


frame = MRFhelper.from_json(r'C:\Users\admin\Desktop\MRF4S_AS.json')
frame.generate_tcl_script('output')

