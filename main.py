from MRFHelper import from_json

frame = from_json(r"test\MRF4S.json")
frame.generate_scripts("output")
