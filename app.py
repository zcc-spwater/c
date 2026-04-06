from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# --- 1. 設定分數對照表 ---
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
            # 取得學號並徹底去除所有空格
            sid = str(row.get('學號', '')).replace(" ", "").strip()
            if not sid: continue 
            
            name = str(row.get('姓名', '未知')).strip()
            
            # 讀取積分，防呆處理（確保是數字）
            raw_val = row.get('積分', 0)
            try:
                # 只保留數字部分
                clean_val = "".join(filter(str.isdigit, str(raw_val)))
                score = int(clean_val) if clean_val else 0
            except:
                score = 0
            
            # 加總邏輯
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

        # 距離驗證
        dist = haversine(lon, lat, 120.202575, 22.981225)
        if dist > 150:
            return f"簽到失敗！距離太遠 ({int(dist)}公尺)"

        # --- 3. 自動決定寫入的分數 ---
        this_score = SCORES_CONFIG.get(status, 0)

        # 修正：確保這行開頭沒有多餘空格！
        row_data = [sid, name, sdate, period, status, this_score]
        sheet.append_row(row_data)
        
        return f"簽到成功！{name} 已獲得 {this_score} 分"
        
    except Exception as e:
        return f"簽到系統出錯：{e}"

if __name__ == "__main__":
    app.run(debug=True)