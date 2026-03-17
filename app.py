from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# 狀態對應的積分設定
SCORES_CONFIG = {
    "出席": 10,
    "公假": 10,
    "遲到": 5,
    "缺席": 0
}

def render_result(message, is_success):
    color = "#00aaff" if is_success else "#ff4444"
    icon = "✅" if is_success else "❌"
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #1a1a1a; font-family: sans-serif; color: white; }}
            .card {{ background: rgba(30, 30, 30, 0.9); padding: 40px; border-radius: 20px; border: 2px solid {color}; text-align: center; width: 80%; max-width: 400px; }}
            .msg {{ font-size: 24px; font-weight: bold; margin: 20px 0; }}
            .btn {{ padding: 10px 30px; background: {color}; color: white; border-radius: 10px; text-decoration: none; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div style="font-size:60px">{icon}</div>
            <div class="msg">{message}</div>
            <a href="/" class="btn">返回首頁</a>
        </div>
    </body>
    </html>
    """

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

        # --- 核心：累加每個人積分 ---
        summary = {} 
        for row in data:
            sid = str(row.get('學號', '')).strip()
            if not sid: continue # 跳過空白行
            
            name = str(row.get('姓名', '未知')).strip()
            # 取得該行積分，如果沒這欄或格式不對就當作 0
            raw_val = row.get('積分', 0)
            try:
                # 只提取數字，避免空格造成 ValueError
                score_str = "".join(filter(str.isdigit, str(raw_val)))
                score = int(score_str) if score_str else 0
            except:
                score = 0
            
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 轉換為清單並排序
        leaderboard = [{'姓名': v['姓名'], '積分': v['積分']} for v in summary.values()]
        leaderboard = sorted(leaderboard, key=lambda x: x['積分'], reverse=True)
        
        return render_template("index.html", leaderboard=leaderboard[:10])
    except Exception as e:
        return f"排行榜讀取失敗，請確認試算表是否有「積分」欄位。錯誤：{e}"

@app.route("/submit", methods=["POST"])
def submit():
    try:
        # 1. 定位驗證 (暫時設為 100 公里方便你測試)
        lat, lon = float(request.form.get("latitude", 0)), float(request.form.get("longitude", 0))
        dist = haversine(lon, lat, 120.202575, 22.981225)
        if dist > 100000: # 測試用，正式時改回 150
             return render_result(f"距離太遠 ({int(dist)}m)", False)

        # 2. 連接試算表
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        
        sid = request.form.get("student_id")
        name = request.form.get("name")
        sdate = request.form.get("date")
        period = request.form.get("period")
        status = request.form.get("status")
        
        # 3. 自動判斷這一次簽到該給幾分
        this_score = SCORES_CONFIG.get(status, 0)

        # 4. 重複簽到檢查
        all_data = sheet.get_all_records()
        if any(str(r.get('學號')) == sid and str(r.get('日期')) == sdate and str(r.get('節次')) == period for r in all_data):
            return render_result("你這節課已經簽過到囉！", False)

        # 5. 寫入新資料 (包含自動計算的積分)
        sheet.append_row([sid, name, sdate, period, status, this_score])
        return render_result(f"簽到成功！<br>狀態：{status}<br>獲得積分：{this_score}", True)
        
    except Exception as e:
        return render_result(f"系統錯誤：{e}", False)

if __name__ == "__main__":
    app.run(debug=True)