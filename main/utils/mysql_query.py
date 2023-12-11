from main.config import mysql_connector

def get_gateway_id_by_user_id(user_id, mngr_id = None):
    """user_id를 통해 gateway_id를 리턴
       mngr_id가 있으면 해당 mngr에 대한 user의 gateway_id를 리턴"""
    if mngr_id:
         result = mysql_connector.sql_execute("select gateway_id from User where user_id = %s and %s in (select user_id from User where admin = %s)", (user_id, user_id, mngr_id))
    else:
        result = mysql_connector.sql_execute("select gateway_id from User where user_id = %s", (user_id,))
    if result:
        if result[0]:
            return result[0][0]
    return None

# gateway_id 값을 이용해 Device table에 등록된 모든 디바이스 id + type 반환
def get_deviceInfo_by_gatewwayId(gateway_id, device_type=None, dictionary = None):
    if not device_type:
        params = (gateway_id, )
        sql = "select device_id, device_type from Device where gateway_id = %s"
    else:
        params = (gateway_id, device_type)
        sql = "select device_id, install_location from Device where gateway_id = %s and device_type = %s"
    return mysql_connector.sql_execute(sql, params, dictionary or False)

def get_deviceInfo_by_gatewwayIdList(gateway_id_list, device_type_list, dictionary = False):
    gateway_format_strings = ','.join(['%s'] * len(gateway_id_list))
    device_format_strings = ','.join(['%s'] * len(device_type_list))
    params = tuple(gateway_id_list) + tuple(device_type_list)
    sql = f"select device_id, gateway_id, device_type, install_location from Device where gateway_id in ({gateway_format_strings}) and device_type in ({device_format_strings})"
    return mysql_connector.sql_execute(sql, params, dictionary)


'''
print(get_deviceInfo_by_gatewwayId("W220_D6FC80"))
print(get_deviceInfo_by_gatewwayId("W220_D6FC80", "door"))

Result Ex1
[
    ('0x5722', 'door'), ('0x838A', 'door'), ('0xA9BC', 'gas'), 
    ('0xC5FF', 'door'), ('0xCC80', 'plug'), ('0xF26E', 'motion'), 
    ('0xF872', 'leak'), ('0xFB80', 'switch')
]

Result Ex2
[
    '0x5722', '0x838A', '0xC5FF'
]
'''
