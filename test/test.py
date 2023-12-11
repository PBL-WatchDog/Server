from influxdb_client import InfluxDBClient, Point, WriteOptions

# InfluxDB 설정
url = "http://localhost:8086"  # InfluxDB 서버 URL
token = "1cDBU-BVSjJ0emb2KmZjgOhGNs3V1-cW60aqfMHoaeyndLVVdFfIo_Gp81OZn1iZ6gCHUvTjoi2rheflojizOg=="  # InfluxDB 토큰
org = "Brighten"  # 조직 이름
bucket = "smarthome"  # 버킷 이름

# 클라이언트 생성
client = InfluxDBClient(url=url, token=token, org=org)

# 쿼리
query = '''
from(bucket: "smarthome")
  |> range(start: 2023-01-01T00:00:00Z)
  |> filter(fn: (r) => r["_measurement"] == "SensorData")
  |> filter(fn: (r) => r["mac_address"] == "W220_818FB4")
  |> filter(fn: (r) => r["Device"] == "0x8015")
  |> filter(fn: (r) => r["_field"] == "Contact")
'''

# 데이터 로드
# tables = client.query_api().query(query, org=org)
tables = client.query_api().query_data_frame(query)

print("\nDB에서 문 열림 센서 데이터 불러오기")
print(tables.head())
print()

# 데이터 처리
# 문이 열리고 닫힌 시간 차이를 계산하여, 3분이 넘어가면 그대로 두고, 3분 이내라면 데이터를 삭제
import pandas as pd

# 시간을 pandas의 datetime 형식으로 변환
tables['_time'] = pd.to_datetime(tables['_time'])

# 데이터를 시간 순으로 정렬
tables.sort_values(by='_time', inplace=True)

print("시간 순으로 정렬")
print(tables.head())
print()

time_diffs = []     # 시간 차이를 계산한 이벤트 리스트
valid_indices = []  # 3분 이상 차이가 나는 이벤트 리스트

# 문 열림(1)과 문 닫힘(0)의 시간 차이를 순차적으로 계산
# time_diffs = tables[tables['_value'] == '0']['_time'].values - tables[tables['_value'] == '1']['_time'].values
for i in range(len(tables) - 1):
    if tables.iloc[i]['_value'] == '1' and tables.iloc[i + 1]['_value'] == '0':
        open_time = tables.iloc[i]['_time']
        close_time = tables.iloc[i + 1]['_time']
        time_diff = close_time - open_time
        # 3분 이상 차이가 나는 이벤트만 추가
        if time_diff >= pd.Timedelta(minutes=3):
            valid_indices.extend([i, i + 1])

# 3분 이상 차이가 나는 이벤트만 남기기
# valid_indices = [i for i, diff in enumerate(time_diffs) if diff >= pd.Timedelta(minutes=3)]

# 유효한 이벤트에 해당하는 데이터만 필터링
# valid_tables = tables.iloc[sum([[i, i+1] for i in valid_indices], [])]
valid_tables = tables.iloc[valid_indices]

# 인덱스 재설정(0부터 오름차순)
valid_tables.reset_index(drop=True, inplace=True)

# 디바이스 ID 설정
valid_tables['Device'] = '0x2BD2'

# 결과 확인
print("\n결과 확인")
print(valid_tables)
print()

# InfluxDB에 데이터 쓰기
from influxdb_client.client.write_api import SYNCHRONOUS

# 쓰기 API 생성
write_api = client.write_api(write_options=SYNCHRONOUS)

# DataFrame을 순회하면서 데이터를 InfluxDB Point 객체로 변환
# for index, row in valid_tables.iterrows():
#     point = Point("SensorData") \
#         .tag("Device", row["Device"]) \
#         .tag("mac_address", row["mac_address"]) \
#         .field("Contact", int(row["_value"])) \
#         .time(row["_time"])
    
#     # Point 객체를 InfluxDB에 쓰기
#     write_api.write(bucket=bucket, org=org, record=point)

client.close()