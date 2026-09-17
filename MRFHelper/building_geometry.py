from . import validation


class BuildingGeometry:
    def __init__(self):
        """Step-1:
        Building geometry parameters

        Properties:
            * story_height (tuple):  Story_height
            * bay_length (tuple): Bay_length
        """
        self.story_height = None
        self.bay_length = None

    def _check(self):
        validation.check_list(self.story_height, min_length=1, max_length=98, name="story_height")
        validation.check_list(self.bay_length, min_length=1, max_length=98, name="bay_length")

    def _finish(self):
        """Complete the definition of building geometry parameters"""
        self._check()
        self.N = len(self.story_height)
        self.bays = len(self.bay_length)
        self.axis = self.bays + 1
        self.building_height = sum(self.story_height)
