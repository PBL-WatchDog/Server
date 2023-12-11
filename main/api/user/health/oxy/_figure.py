def figure(spo2):
    """https://udiportal.mfds.go.kr/brd/view/MNU10034?&ntceSn=114"""
    result = ''

    if spo2:
        try:
            spo2 = float(spo2)

            if spo2 >= 95 and spo2 <= 100: result = "정상"
            elif spo2 > 90 and spo2 < 95: result = "저산소증주의"
            elif spo2 > 80 and spo2 <= 90: result = "저산소증위험" 
            elif spo2 <= 80: result = "매우위험"
            else: result = "측정오류"
        except: pass
    return result