def figure(systolic, diastolic):
    """ https://health.amc.seoul.kr/health/personal/checkInformation.do?checkno=44 """
    result = ''

    if systolic and diastolic:
        try:
            systolic = float(systolic)
            diastolic = float(diastolic)

            if systolic < 90 and diastolic < 60: result = "저혈압"
            elif systolic < 120 and diastolic < 80: result = "정상"
            elif systolic >= 120 and systolic < 130 and diastolic < 80: result = "주의"
            elif systolic >= 130 and systolic < 140 and diastolic >= 80 and diastolic < 90: result = "고혈압전"
            elif systolic >= 140 and diastolic < 90: result = "수축기단독고혈압"
            elif systolic >= 140 and systolic < 160 and diastolic >= 90 and diastolic < 100: result = "1기고혈압"
            elif systolic >= 160 and diastolic >= 100: result = "2기고혈압"
            else: result = "정상"
        
        except:
            pass

    return result