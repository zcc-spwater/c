from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# 簽到分數配置
SCORES_CONFIG = {"出席": 10, "公假": 10, "遲到": 5, "缺席": 0}

# 距離計算函數
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371 * 1000 

@app.route("/")
def index():
    try:
        # 連接 Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        all_records = sheet.get_all_records()

        # --- 關鍵：資料統計與累加邏輯 ---
        summary = {} 
        for row in all_records:
            # 1. 取得學號並徹底去除空格 (確保同一個人不會因為空格被分開)
            sid = str(row.get('學號', '')).replace(" ", "").strip()
            if not sid: continue 
            
            # 2. 取得姓名
            name = str(row.get('姓名', '未知')).strip()
            
            # 3. 積分防呆：解決 ValueError (即使格子是空的也能跑)
            raw_val = row.get('積分', 0)
            try:
                # 只保留數字，如果是空字串就給 0
                clean_val = "".join(filter(str.isdigit, str(raw_val)))
                score = int(clean_val) if clean_val else 0
            except:
                score = 0
            
            # 4. 根據學號進行加總
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 5. 轉回列表並排序 (從高分到低分)
        leaderboard = sorted(summary.values(), key=lambda x: x['積分'], reverse=True)
        
        # 傳送到網頁，變數名稱為 leaderboard
        return render_template("index.html", leaderboard=leaderboard[:10])
    except Exception as e:
        return f"排行榜讀取失敗，原因：{e}"

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

        # 定位驗證 (150公尺)
        dist = haversine(lon, lat, 120.202575, 22.981225)
        if dist > 150:
            return f"簽到失敗！距離太遠 ({int(dist)}公尺)"

        # 自動計算本次給分
        this_score = SCORES_CONFIG.get(status, 0)

        # 寫入試算表
        sheet.append_row([sid, name, sdate, period, status, this_score])
        return f"簽到成功！獲得 {this_score} 分"
        
    except Exception as e:
        return f"簽到系統出錯：{e}"

if __name__ == "__main__":
    app.run(debug=True)