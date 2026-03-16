from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# --- 工具函數：美化回傳畫面 (置中大字) ---
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
            body {{
                margin: 0; padding: 0;
                display: flex; justify-content: center; align-items: center;
                height: 100vh; background-color: #1a1a1a;
                background-image: url('https://images.unsplash.com/photo-1519681393784-d120267933ba');
                background-size: cover; background-position: center;
                font-family: 'Microsoft JhengHei', sans-serif; color: white;
            }}
            .card {{
                background: rgba(30, 30, 30, 0.85);
                backdrop-filter: blur(15px);
                padding: 40px 20px;
                border-radius: 25px;
                border: 2px solid {color};
                text-align: center;
                box-shadow: 0 0 30px rgba(0,0,0,0.5);
                width: 85%; max-width: 500px;
            }}
            .icon {{ font-size: 80px; margin-bottom: 20px; }}
            .msg {{ font-size: 26px; font-weight: bold; line-height: 1.6; color: white; }}
            .btn {{
                margin-top: 30px; padding: 12px 40px;
                background: {color}; color: white;
                border: none; border-radius: 50px;
                font-size: 18px; cursor: pointer; text-decoration: none;
                display: inline-block; font-weight: bold;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">{icon}</div>
            <div class="msg">{message}</div>
            <a href="/" class="btn">返回首頁</a>
        </div>
    </body>
    </html>
    """

# --- 工具函數：計算距離 ---
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371 * 1000 

# --- 路由：首頁排行榜 ---
@app.route("/")
def index():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        data = sheet.get_all_records()
        # 依積分排序
        sorted_data = sorted(data, key=lambda x: int(x.get('積分', 0)) if str(x.get('積分', 0)).isdigit() else 0, reverse=True)
        return render_template("index.html", leaderboard=sorted_data[:10])
    except Exception as e:
        return f"讀取排行榜失敗: {e}"

# --- 路由：處理簽到 ---
@app.route("/submit", methods=["POST"])
def submit():
    # 1. 定位驗證
    try:
        s_lat = float(request.form.get("latitude", 0))
        s_lon = float(request.form.get("longitude", 0))
        dist = haversine(s_lon, s_lat, 120.202575, 22.981225)
        if dist > 10000:
            return render_result(f"簽到失敗！<br>你距離學校約 {int(dist)} 公尺，太遠囉！", False)
    except:
        return render_result("座標錯誤，請確認手機 GPS 已開啟並允許定位。", False)

    # 2. 連接試算表
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("myproject").sheet1
        
        sid = request.form.get("student_id")
        sname = request.form.get("name")
        sdate = request.form.get("date")
        speriod = request.form.get("period")
        sstatus = request.form.get("status")
        
        # 3. 重複簽到檢查 (同一天 + 同一節 + 同一人)
        all_data = sheet.get_all_records()
        for r in all_data:
            if str(r.get('學號')) == sid and str(r.get('日期')) == sdate and str(r.get('節次')) == speriod:
                return render_result(f"注意！<br>學號 {sid} 在這節課已經簽過到囉！", False)

        # 4. 寫入資料
        new_row = [sid, sname, sdate, speriod, sstatus]
        sheet.append_row(new_row)
        return render_result(f"簽到成功！✨<br>學號：{sid}<br>紀錄已存入雲端。", True)
        
    except Exception as e:
        return render_result(f"系統發生錯誤：{e}", False)

if __name__ == "__main__":
    app.run(debug=True)