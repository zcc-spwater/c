from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)

# --- 美化回傳頁面模板 ---
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
                margin: 0; padding: 0; display: flex; justify-content: center; align-items: center;
                height: 100vh; background-color: #1a1a1a;
                background-image: url('https://images.unsplash.com/photo-1519681393784-d120267933ba');
                background-size: cover; background-position: center;
                font-family: 'Microsoft JhengHei', sans-serif; color: white;
            }}
            .card {{
                background: rgba(30, 30, 30, 0.85); backdrop-filter: blur(15px);
                padding: 40px 20px; border-radius: 25px; border: 2px solid {color};
                text-align: center; box-shadow: 0 0 30px rgba(0,0,0,0.5); width: 85%; max-width: 500px;
            }}
            .icon {{ font-size: 80px; margin-bottom: 20px; }}
            .msg {{ font-size: 26px; font-weight: bold; line-height: 1.6; color: white; }}
            .btn {{
                margin-top: 30px; padding: 12px 40px; background: {color}; color: white;
                border: none; border-radius: 50px; font-size: 18px; cursor: pointer;
                text-decoration: none; display: inline-block; font-weight: bold;
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

        # --- 合計每個人積分邏輯 (更強大的容錯版) ---
        summary = {} 
        for row in all_records:
            # 取得學號並去除前後空格
            sid = str(row.get('學號', '')).strip()
            # 如果學號這格是空的，就跳過這一行
            if not sid: continue 
            
            name = str(row.get('姓名', '未知')).strip()
            
            # 安全轉換積分：處理空格、None 或非數字文字
            raw_score = row.get('積分', 0)
            try:
                # 拿掉所有空格後轉數字，若轉失敗就給 0
                score_str = str(raw_score).strip()
                score = int(score_str) if score_str else 0
            except:
                score = 0
            
            if sid in summary:
                summary[sid]['積分'] += score
            else:
                summary[sid] = {'姓名': name, '積分': score}

        # 整理成清單並按積分排序
        leaderboard_data = [{'姓名': info['姓名'], '積分': info['積分']} for info in summary.values()]
        sorted_data = sorted(leaderboard_data, key=lambda x: x['積分'], reverse=True)
        
        return render_template("index.html", leaderboard=sorted_data[:10])
    except Exception as e:
        return f"讀取排行榜失敗：{e}"

@app.route("/submit", methods=["POST"])
def submit():
    try:
        s_lat = float(request.form.get("latitude", 0))
        s_lon = float(request.form.get("longitude", 0))
        dist = haversine(s_lon, s_lat, 120.202575, 22.981225)
        if dist > 150: # 測試時可以把 150 改成更大的數字
            return render_result(f"距離學校約 {int(dist)} 公尺，太遠囉！", False)
    except:
        return render_result("座標錯誤，請確認 GPS 已開啟。", False)

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('credentials.json', scopes=score)
    client = gspread.authorize(creds)
    sheet = client.open("myproject").sheet1
    
    sid = request.form.get("student_id")
    sname = request.form.get("name")
    sdate = request.form.get("date")
    speriod = request.form.get("period")
    sstatus = request.form.get("status")
    
    # 根據簽到狀態自動給分
    status_scores = {"出席": 10, "遲到": 5, "公假": 10}
    current_score = status_scores.get(sstatus, 0)

    # 同一天、同一節次重複簽到檢查
    all_data = sheet.get_all_records()
    for r in all_data:
        if str(r.get('學號')).strip() == sid and str(r.get('日期')).strip() == sdate and str(r.get('節次')).strip() == speriod:
            return render_result(f"學號 {sid} 在這節課已經簽過到囉！", False)

    # 寫入包含積分欄位的資料
    sheet.append_row([sid, sname, sdate, speriod, sstatus, current_score])
    return render_result(f"簽到成功！✨<br>學號：{sid}<br>獲得積分：{current_score}", True)

if __name__ == "__main__":
    app.run(debug=True)