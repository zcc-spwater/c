from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# --- 1. 設定分數對照表 (這就是自動給分的依據) ---
SCORES_CONFIG = {"出席": 10, "公假": 10, "遲到": 5, "缺席": 0}

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
        all_records = sheet.get_all_records()

        # --- 2. 核心統計邏輯：根據學號自動累加分數 ---
        summary = {} 
        for row in all_records:
            sid = str(row.get('學號', '')).strip()
            if not sid: continue 
            
            name = str(row.get('姓名', '未知')).strip()
            
            # 讀取積分，如果是空的就自動當作 0，避免報錯
            raw_val = row.get('積分', 0)
            try:
                score = int(str(raw_val).strip()) if str(raw_val).strip() else 0
            except:
                score = 0
            
            # 如果學號重複，就分數相加
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 排序並傳回網頁
        leaderboard = sorted(summary.values(), key=lambda x: x['積分'], reverse=True)
        return render_template("index.html", leaderboard=leaderboard[:10])
    except Exception as e:
        return f"排行榜讀取失敗：{e}"

@app.route("/submit", methods=["POST"])
def submit():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        
        sid = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        sdate = request.form.get("date")
        period = request.form.get("period")
        status = request.form.get("status")
        lat = float(request.form.get("latitude", 0))
        lon = float(request.form.get("longitude", 0))

        # 距離驗證 (150公尺)
        dist = haversine(lon, lat, 120.202575, 22.981225)
        if dist > 150:
            return f"簽到失敗！距離太遠 ({int(dist)}公尺)"

        # --- 3. 關鍵修正：自動決定要寫入的分數 ---
        # 如果 status 是 "出席"，this_score 就會是 10
        this_score = SCORES_CONFIG.get(status, 0)

        # 按照順序寫入試算表：學號, 姓名, 日期, 節次, 狀態, 積分
        # 這是讓積分自動寫入 F 欄的關鍵
        row_data = [sid, name, sdate, period, status, this_score]
          sheet.append_row(row_data)
        return f"簽到成功！{name} 已獲得 {this_score} 分"
        
    except Exception as e:
        return f"簽到系統出錯：{e}"

if __name__ == "__main__":
    app.run(debug=True)