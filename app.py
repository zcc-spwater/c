from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# 狀態積分設定
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
        data = sheet.get_all_records()

        # --- 資料合計邏輯：把同一個人的積分加起來 ---
        summary = {} 
        for row in data:
            sid = str(row.get('學號', '')).strip()
            if not sid: continue
            
            name = str(row.get('姓名', '未知')).strip()
            raw_val = row.get('積分', 0)
            
            # 防呆：處理 image_953ae6.png 提到的 int() 轉換錯誤
            try:
                score_str = "".join(filter(str.isdigit, str(raw_val)))
                score = int(score_str) if score_str else 0
            except:
                score = 0
            
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 排序並格式化
        leaderboard = [{'姓名': v['姓名'], '積分': v['積分']} for v in summary.values()]
        leaderboard = sorted(leaderboard, key=lambda x: x['積分'], reverse=True)
        
        return render_template("index.html", leaderboard=leaderboard[:10])
    except Exception as e:
        return f"讀取排行榜失敗，錯誤原因：{e}"

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

        # 距離驗證 (測試時可改為 100000)
        dist = haversine(lon, lat, 120.202575, 22.981225)
        if dist > 150:
            return f"簽到失敗！距離太遠 ({int(dist)}m)"

        # 自動計算積分
        this_score = SCORES_CONFIG.get(status, 0)

        # 寫入試算表
        sheet.append_row([sid, name, sdate, period, status, this_score])
        return f"簽到成功！狀態：{status}，獲得 {this_score} 分"
        
    except Exception as e:
        return f"系統錯誤：{e}"

if __name__ == "__main__":
    app.run(debug=True)