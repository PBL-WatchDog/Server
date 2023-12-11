def figure(bld_sugar):
    """https://www.kslm.org/sub01/sub03.html"""
    result = ''
    if bld_sugar:
        try:
            bld_sugar = float(bld_sugar)

            if bld_sugar >= 70 and bld_sugar < 100: result = "정상"
            elif bld_sugar >= 100 and bld_sugar <= 125: result = "공복혈당장애"
            elif bld_sugar > 125: result = "당뇨병의심"
            else: result = "저혈당증상"
        except: pass

    return result