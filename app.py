from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# 地球距離計算
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371 * 1000 

@app.route("/")
def index():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    # 這裡請改成你的試算表名稱
    sheet = client.open("myproject").sheet1
    data = sheet.get_all_records()
    # 排序排行榜 (依積分從大到小)
    sorted_data = sorted(data, key=lambda x: int(x.get('積分', 0)), reverse=True)
    return render_template("index.html", leaderboard=sorted_data[:10])

@app.route("/submit", methods=["POST"])
def submit():
    # 1. 定位驗證 (台南高商座標)
    try:
        s_lat, s_lon = float(request.form.get("latitude", 0)), float(request.form.get("longitude", 0))
        dist = haversine(s_lon, s_lat, 120.202575, 22.981225)
        if dist > 150: # 設定 150 公尺誤差
            return f"❌ 簽到失敗！你距離學校 {int(dist)} 公尺，太遠囉！"
    except:
        return "❌ 座標錯誤，請重新定位。"

    # 2. 寫入試算表 & 重複檢查
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("myproject").sheet1
    
    sid = request.form.get("student_id")
    sdate = request.form.get("date")
    
    # 檢查是否已存在 (同天同人)
    all_data = sheet.get_all_records()
    if any(str(r.get('學號')) == sid and str(r.get('日期')) == sdate for r in all_data):
        return "❌ 你今天已經簽到過囉！"

    # 寫入新資料
    row = [sid, request.form.get("name"), sdate, request.form.get("period"), request.form.get("status")]
    sheet.append_row(row)
    return "✅ 簽到成功！座標已驗證。"

if __name__ == "__main__":
    app.run(debug=True)
    from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# 計算距離函數
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371 * 1000 

@app.route("/")
def index():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        data = sheet.get_all_records()
        # 依積分排序
        sorted_data = sorted(data, key=lambda x: int(x.get('積分', 0)), reverse=True)
        return render_template("index.html", leaderboard=sorted_data[:10])
    except Exception as e:
        return f"讀取排行榜失敗: {e}"

@app.route("/submit", methods=["POST"])
def submit():
    # 1. 定位驗證 (台南高商 22.981225, 120.202575)
    try:
        s_lat = float(request.form.get("latitude", 0))
        s_lon = float(request.form.get("longitude", 0))
        dist = haversine(s_lon, s_lat, 120.202575, 22.981225)
        if dist > 150: # 150公尺誤差範圍
            return f"❌ 簽到失敗！你距離學校約 {int(dist)} 公尺，太遠囉！"
    except:
        return "❌ 座標錯誤，請確認 GPS 已開啟。"

    # 2. 連接試算表
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("myproject").sheet1
    
    sid = request.form.get("student_id")
    sdate = request.form.get("date")
    speriod = request.form.get("period") # 取得節次
    
    # 3. 重複簽到檢查 (同一天 + 同一節 + 同一人)
    all_data = sheet.get_all_records()
    for row in all_data:
        if str(row.get('學號')) == sid and str(row.get('日期')) == sdate and str(row.get('節次')) == speriod:
            return f"❌ 簽到失敗：學號 {sid} 在 {sdate} 的 {speriod} 已經簽過名了！"

    # 4. 寫入資料
    new_row = [sid, request.form.get("name"), sdate, speriod, request.form.get("status")]
    sheet.append_row(new_row)
    return "✅ 簽到成功！座標已驗證，資料已存入。"

if __name__ == "__main__":
    app.run(debug=True)