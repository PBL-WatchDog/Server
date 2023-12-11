def check_int_format(num : str):
    """정수형 문자열인지 확인"""
    if not num or type(num) is not str: return False

    isSign = num[0] in ['+', '-']

    return num[1:].isdigit() if isSign else num.isdigit()

def to_int(num):
    if type(num) in [int, float]:
        return int(num)
    elif check_int_format(num):
        return int(num)

    return None