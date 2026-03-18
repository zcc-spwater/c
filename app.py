from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# --- 1. 設定分數規則 (確保簽到時會寫入積分) ---
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

        # --- 2. 核心統計邏輯：把同一個人的積分加起來 ---
        summary = {} 
        for row in all_records:
            sid = str(row.get('學號', '')).strip()
            if not sid: continue 
            
            name = str(row.get('姓名', '未知')).strip()
            
            # 讀取積分，如果是空的就給 0，避免 ValueError
            raw_val = row.get('積分', 0)
            try:
                score = int(str(raw_val).strip()) if str(raw_val).strip() else 0
            except:
                score = 0
            
            # 加總：如果學號一樣，就把分數累加上去
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 排序並取前10名
        leaderboard = sorted(summary.values(), key=lambda x: x['積分'], reverse=True)
        return render_template("index.html", leaderboard=leaderboard[:10])
    except Exception as e:
        return f"讀取排行榜失敗：{e}"

@app.route("/submit", methods=["POST"])
def submit():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        
        sid = request.form.get("student_id").strip()
        name = request.form.get("name").strip()
        sdate = request.form.get("date")
        period = request.form.get("period")
        status = request.form.get("status")
        lat = float(request.form.get("latitude", 0))
        lon = float(request.form.get("longitude", 0))

        dist = haversine(lon, lat, 120.202575, 22.981225)
        if dist > 150: return f"簽到失敗！距離太遠 ({int(dist)}m)"

        # --- 3. 關鍵修正：簽到成功時，根據狀態自動決定積分並寫入 ---
        this_score = SCORES_CONFIG.get(status, 0)
        
        # 依照順序寫入：學號, 姓名, 日期, 節次, 狀態, 積分
        sheet.append_row([sid, name, sdate, period, status, this_score])
        
        return f"簽到成功！獲得 {this_score} 積分"
        
    except Exception as e:
        return f"錯誤：{e}"

if __name__ == "__main__":
    app.run(debug=True)