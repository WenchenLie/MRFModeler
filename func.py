def check_int(value: int, min_max: list=None, pos=True, isNone=False, name=''):
    """check if a value is of the 'int' type and optionally within a given range"""
    name_ = f' `{name}`' if name else ''
    if not isNone and value is None:
        raise ValueError(f'Variable{name_} should not be of "None"')
    if isNone and value is None:
        return
    if not isinstance(value, int):
        raise ValueError(f'Variable{name_} should be of "int" type')
    if min_max:
        min_val, max_val = min_max
        if not min_val <= value <= max_val:
            raise ValueError(f'Variable{name_} should be within the range of [{min_val}, {max_val}]')
    if pos and value < 0:
        raise ValueError(f'The variable{name_} should be larger than 0')


def check_int_float(value: int | float, min_max: list=None, pos=True, isNone=False, name=''):
    """check if a value is of the 'int' or 'float' type and optionally within a given range"""
    name_ = f' `{name}`' if name else ''
    if not isNone and value is None:
        raise ValueError(f'Variable{name_} should not be of "None"')
    if isNone and value is None:
        return
    if not isinstance(value, (int, float)):
        raise ValueError(f'Variable{name_} should be of "int" or "float" type')
    if min_max:
        min_val, max_val = min_max
        if not min_val <= value <= max_val:
            raise ValueError(f'Variable{name_} should be within the range of [{min_val}, {max_val}]')
    if pos and value < 0:
        raise ValueError(f'The variable{name_} should be larger than 0')


def check_boolean(value: bool, isNone=False, name=''):
    """check if a value is of the 'boolean' type"""
    name_ = f' `{name}`' if name else ''
    if not isNone and value is None:
        raise ValueError(f'Variable{name_} should not be of "None"')
    if isNone and value is None:
        return
    if not isinstance(value, bool):
        raise ValueError(f'Variable{name_} should be of "bool" type')
    

def check_string(value: str, options: list=None, isNone=False, name=''):
    """check if a value is of the 'str' type"""
    name_ = f' `{name}`' if name else ''
    if not isNone and value is None:
        raise ValueError(f'Variable{name_} should not be of "None"')
    if isNone and value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f'Variable{name_} should be of "str" type')
    if options and value not in options:
        raise ValueError(f'Variable{name_} should be within {options}')


def check_tuple(value: tuple, length=None, min_length=None, max_length=None, pos=True, isNone=False, name=''):
    """check if a value is of the 'tuple' type"""
    name_ = f' `{name}`' if name else ''
    if not isNone and value is None:
        raise ValueError(f'Variable{name_} should not be of "None"')
    if isNone and value is None:
        return
    if not isinstance(value, tuple):
        raise ValueError(f'The variable{name_} should be of "int" or "float" type')
    if length and len(value) != length:
        raise ValueError(f'The length of the tuple{name_} should be {length}')
    if min_length and len(value) < min_length:
        raise ValueError(f'The minimum length of the tuple{name_} should be {min_length}')
    if max_length and len(value) > max_length:
        raise ValueError(f'The maxmum length of the tuple{name_} should be {max_length}')
    if pos:
        for val in value:
            if val < 0:
                raise ValueError(f'The variable{name_} should be larger than 0')


def check_list(value: list, length=None, min_length=None, max_length=None, pos=True, isNone=False, name=''):
    """check if a value is of the 'list' type"""
    name_ = f' `{name}`' if name else ''
    if not isNone and value is None:
        raise ValueError(f'Variable{name_} should not be of "None"')
    if isNone and value is None:
        return
    if not isinstance(value, list):
        raise ValueError(f'The variable{name_} should be of "int" or "float" type')
    if length and len(value) != length:
        raise ValueError(f'The length of the list{name_} should be {length}')
    if min_length and len(value) < min_length:
        raise ValueError(f'The minimum length of the list{name_} should be {min_length}')
    if max_length and len(value) > max_length:
        raise ValueError(f'The maxmum length of the list{name_} should be {max_length}')
    if pos:
        for val in value:
            if val < 0:
                raise ValueError(f'The variable{name_} should be larger than 0')


def check_dict(value: dict, isNone=False, name=''):
    """check if a value is of the 'dict' type"""
    name_ = f' `{name}`' if name else ''
    if not isNone and value is None:
        raise ValueError(f'Variable{name_} should not be of "None"')
    if isNone and value is None:
        return
    if not isinstance(value, dict):
        raise ValueError(f'The variable{name_} should be of "int" or "float" type')



if __name__ == "__main__":
    a = None
    check_tuple(a, isNone=True, name='a')