import mysql.connector.pooling
from main.config.config import MARIADB_PASSWORD

# Connection Pool 설정
dbconfig = {
    "host": "127.0.0.1",
    "user": "root",
    "password": MARIADB_PASSWORD,
    "database": "smarthome",
    "port": 3306,
    "charset" : "utf8"
}

# Pool 생성
conn_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",
                                                        pool_size=10,
                                                        **dbconfig)

def sql_execute(query, params=None, dictionary=False):
    conn = conn_pool.get_connection()
    cursor = conn.cursor(dictionary=dictionary)

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    
    if cursor.with_rows:  # SELECT 문의 경우
        results = cursor.fetchall()
        results = results if results != [] else None    # select 문에 해당하는 행이 없으면 None으로 설정
    else:  # INSERT, UPDATE 또는 DELETE 문의 경우
        conn.commit()  # 쿼리를 커밋합니다.
        results = None  # 또는 영향받은 행의 수를 반환하려면 cursor.rowcount를 사용
    
    cursor.close()
    conn.close()

    return results

# class SqlInstance:
#     def __init__(self, dictionary = False):
#         self.__dictionary = dictionary

#     def __enter__(self) -> "SqlInstance":
#         self.connector = conn_pool.get_connection()
#         self.cursor = self.connector.cursor(dictionary=self.__dictionary)
#         return self
    
#     def __exit__(self, exc_type, exc_value, traceback):
#         self.cursor.close()
#         self.connector.close()
