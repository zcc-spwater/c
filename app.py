from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# 分數規則：簽到時自動寫入的值
SCORES_CONFIG = {"出席": 10, "公假": 10, "遲到": 5, "缺席": 0}

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371 * 1000 

@app.route("/")
def index():
    try:
        # 連結 Google 試算表
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        all_records = sheet.get_all_records()

        # --- 核心：統計與加總邏輯 ---
        summary = {} 
        for row in all_records:
            # 1. 取得學號並徹底去除空格 (避免同一個人被分開統計)
            sid = str(row.get('學號', '')).strip()
            if not sid: continue 
            
            name = str(row.get('姓名', '未知')).strip()
            
            # 2. 超強防呆積分處理：解決你遇到的 ValueError
            raw_val = row.get('積分', 0)
            try:
                # 即使 F5 是空的，也會自動轉為 0，不會崩潰
                val_str = str(raw_val).strip()
                score = int(val_str) if val_str else 0
            except:
                score = 0
            
            # 3. 根據學號加總分數
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 將統計結果轉為列表，並依分數從高到低排序
        leaderboard = sorted(summary.values(), key=lambda x: x['積分'], reverse=True)
        
        # 傳送到網頁，只取前 10 名
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

        # 座標驗證
        dist = haversine(lon, lat, 120.202575, 22.981225)
        if dist > 150:
            return f"簽到失敗！距離太遠 ({int(dist)}公尺)"

        # 根據狀態給分
        this_score = SCORES_CONFIG.get(status, 0)
        sheet.append_row([sid, name, sdate, period, status, this_score])
        return f"簽到成功！獲得 {this_score} 分"
        
    except Exception as e:
        return f"系統錯誤：{e}"

if __name__ == "__main__":
    app.run(debug=True)