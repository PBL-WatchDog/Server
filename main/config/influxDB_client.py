import influxdb_client
import csv, io
from main.config.config import INFLUXDB_TOKEN
#from influxdb_client import InfluxDBClient, Point, WritePrecision
#from influxdb_client.client.write_api import SYNCHRONOUS

'''
token = "RptXOiMCz2Fs9vV66Gz1Xnyptdy3J6kMMnPP89JcEgn8REXmExFw9w6EWjbbVoHpl7VoRsVnB6sdIKUJVUBYiA=="
org = "Brighten"
url = "http://210.123.135.176:8086"
'''


# new influxDB connection
token = INFLUXDB_TOKEN
org = "Brighten"
url = "http://localhost:8086"



client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

def fastQuery(query):
    """query_api.query()의 대용량 데이터 처리속도가 처참해서 query_raw로 기본 골자만 받고 수동으로 dict로 리턴해주는 함수"""
    query_api = client.query_api()
    httpResponse  = query_api.query_raw(query, org="Brighten")

    result = []

    csvResult = httpResponse.data.decode('utf-8')
    tables = csvResult.split('\r\n\r\n') # table은 두번의 개행으로 구분

    for table in tables:
        if not table.strip():
            continue
        
        rows = list(csv.DictReader(filter(lambda row: row[0]!='#', io.StringIO(table))))

        result.extend(rows)

    return result