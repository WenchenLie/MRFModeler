from . import validation


class BuildingGeometry:
    def __init__(self):
        """Step-1:
        Building geometry parameters

        Properties:
            * story_height (tuple):  Story_height
            * bay_length (tuple): Bay_length
            * plan_dimensions (tuple): (main direction, secondary direction)
            * mf_number (int): Number of moment frames
            * exterior_column_tributary_area (tuple): (x, y), area = x * y
            * interior_column_tributary_area (tuple): (x, y), area = x * y
        """
        self.story_height = None
        self.bay_length = None
        self.plane_dimensions = None
        self.exterior_column_tributary_area = None
        self.interior_column_tributary_area = None
        self.mf_number = None

    def _check(self):
        validation.check_list(self.story_height, min_length=1, max_length=98, name="story_height")
        validation.check_list(self.bay_length, min_length=1, max_length=98, name="bay_length")
        validation.check_tuple(self.plane_dimensions, 2, name="plane_dimensions")
        validation.check_int(self.mf_number, [1, 99], name="mf_number")
        validation.check_tuple(
            self.exterior_column_tributary_area,
            2,
            name="exterior_column_tributary_area",
        )
        validation.check_tuple(
            self.interior_column_tributary_area,
            2,
            name="interior_column_tributary_area",
        )

    def _finish(self):
        """Complete the definition of building geometry parameters"""
        self._check()
        self.N = len(self.story_height)
        self.bays = len(self.bay_length)
        self.axis = self.bays + 1
        self.building_height = sum(self.story_height)
