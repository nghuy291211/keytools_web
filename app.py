import sqlite3
import datetime
import uuid
import functools
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me_in_production"

DATABASE = "key_system.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # Bảng Tài khoản Admin
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_super INTEGER DEFAULT 0
        )
    ''')
    # Bảng Key
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT UNIQUE NOT NULL,
            max_devices INTEGER DEFAULT 1,
            used_devices INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            ip_logs TEXT DEFAULT '',
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Tạo tài khoản cấp cao nhất mặc định nếu chưa có
    super_admin = cursor.execute("SELECT * FROM admin_users WHERE username = ?", ("nghuy291211",)).fetchone()
    if not super_admin:
        hashed_pw = generate_password_hash("Huy@29122011@")
        cursor.execute("INSERT INTO admin_users (username, password, is_super) VALUES (?, ?, 1)",
                       ("nghuy291211", hashed_pw))
        conn.commit()
    conn.close()

init_db()

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== WEB DASHBOARD (ADMIN) ====================

HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Đăng nhập Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
        .card { background: #1e1e1e; padding: 30px; border-radius: 8px; width: 300px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        input, button { width: 100%; padding: 10px; margin: 10px 0; border-radius: 4px; border: 1px solid #333; box-sizing: border-box; }
        input { background: #2a2a2a; color: #fff; }
        button { background: #007bff; color: white; border: none; cursor: pointer; font-weight: bold; }
        .error { color: #ff4d4d; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Đăng Nhập Quản Trị</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Tên đăng nhập" required>
            <input type="password" name="password" placeholder="Mật khẩu" required>
            <button type="submit">Đăng nhập</button>
        </form>
    </div>
</body>
</html>
"""

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Quản Lý Key</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; margin: 20px; }
        h2, h3 { color: #00e676; }
        .container { max-width: 1100px; margin: auto; }
        .card { background: #1e1e1e; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #333; padding: 10px; text-align: left; }
        th { background: #2a2a2a; }
        input, select, button { padding: 8px; margin: 5px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff; }
        button { background: #00e676; color: #000; font-weight: bold; cursor: pointer; border: none; }
        .btn-danger { background: #ff5252; color: #fff; }
        .header { display: flex; justify-content: space-between; align-items: center; }
        a.logout { color: #ff5252; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Hệ Thống Quản Lý Key</h2>
            <p>Xin chào, <b>{{ session['admin'] }}</b> | <a class="logout" href="/logout">Đăng xuất</a></p>
        </div>

        <!-- Tạo Key Mới -->
        <div class="card">
            <h3>Tạo Key Mới</h3>
            <form action="/create-key" method="POST">
                <label>Thời hạn (Giờ):</label>
                <input type="number" name="hours" value="24" required min="1">
                <label>Số thiết bị (IP tối đa):</label>
                <input type="number" name="max_devices" value="1" required min="1">
                <button type="submit">Tạo Key</button>
            </form>
        </div>

        <!-- Danh sách Key -->
        <div class="card">
            <h3>Danh Sách Key</h3>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Mã Key</th>
                    <th>Thiết bị (Đã dùng/Tối đa)</th>
                    <th>Trạng thái</th>
                    <th>IP Đã Dùng</th>
                    <th>Hết Hạn Lúc</th>
                    <th>Hành Động</th>
                </tr>
                {% for k in keys %}
                <tr>
                    <td>{{ k['id'] }}</td>
                    <td><b>{{ k['key_code'] }}</b></td>
                    <td>{{ k['used_devices'] }} / {{ k['max_devices'] }}</td>
                    <td>
                        {% if k['status'] == 'active' %}
                            <span style="color:#00e676">Hoạt động</span>
                        {% else %}
                            <span style="color:#ff5252">Vô hiệu</span>
                        {% endif %}
                    </td>
                    <td><small>{{ k['ip_logs'] or 'Chưa có' }}</small></td>
                    <td>{{ k['expires_at'] }}</td>
                    <td>
                        <a href="/delete-key/{{ k['id'] }}"><button class="btn-danger">Xóa</button></a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <!-- Quản lý Admin -->
        <div class="card">
            <h3>Tạo Tài Khoản Admin Chi Nhánh</h3>
            <form action="/create-admin" method="POST">
                <input type="text" name="username" placeholder="Tên đăng nhập" required>
                <input type="password" name="password" placeholder="Mật khẩu" required>
                <button type="submit">Tạo Admin</button>
            </form>

            <h4 style="margin-top: 20px;">Danh Sách Admin</h4>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Tên Admin</th>
                    <th>Cấp độ</th>
                    <th>Hành Động</th>
                </tr>
                {% for a in admins %}
                <tr>
                    <td>{{ a['id'] }}</td>
                    <td>{{ a['username'] }}</td>
                    <td>{% if a['is_super'] == 1 %}<b style="color:#00e676">SUPER ADMIN</b>{% else %}Admin{% endif %}</td>
                    <td>
                        {% if is_super_admin and a['is_super'] == 0 %}
                            <a href="/delete-admin/{{ a['id'] }}"><button class="btn-danger">Xóa Admin</button></a>
                        {% else %}
                            <i>Không thể xóa</i>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['admin'] = user['username']
            session['is_super'] = user['is_super']
            return redirect(url_for('dashboard'))
        else:
            error = "Tài khoản hoặc mật khẩu không chính xác!"
            
    return render_template_string(HTML_LOGIN, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    keys = conn.execute("SELECT * FROM keys ORDER BY id DESC").fetchall()
    admins = conn.execute("SELECT * FROM admin_users ORDER BY id ASC").fetchall()
    conn.close()
    return render_template_string(HTML_DASHBOARD, keys=keys, admins=admins, is_super_admin=(session.get('is_super') == 1))

@app.route('/create-key', methods=['POST'])
@login_required
def create_key():
    hours = int(request.form.get('hours', 24))
    max_devices = int(request.form.get('max_devices', 1))
    
    key_code = "KEY-" + str(uuid.uuid4()).upper()[:12]
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=hours)
    
    conn = get_db()
    conn.execute("INSERT INTO keys (key_code, max_devices, expires_at) VALUES (?, ?, ?)",
                 (key_code, max_devices, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete-key/<int:key_id>')
@login_required
def delete_key(key_id):
    conn = get_db()
    conn.execute("DELETE FROM keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/create-admin', methods=['POST'])
@login_required
def create_admin():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db()
    try:
        hashed_pw = generate_password_hash(password)
        conn.execute("INSERT INTO admin_users (username, password, is_super) VALUES (?, ?, 0)", (username, hashed_pw))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete-admin/<int:admin_id>')
@login_required
def delete_admin(admin_id):
    # Chỉ Super Admin mới được xóa Admin
    if session.get('is_super') == 1:
        conn = get_db()
        conn.execute("DELETE FROM admin_users WHERE id = ? AND is_super = 0", (admin_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('dashboard'))

# ==================== API DÀNH CHO TOOL CLIENT ====================

@app.route('/api/verify-key', methods=['POST'])
def api_verify_key():
    data = request.get_json() or {}
    key_code = data.get('key', '').strip()
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if not key_code:
        return jsonify({"valid": False, "message": "Key không được để trống!"}), 400

    conn = get_db()
    key_data = conn.execute("SELECT * FROM keys WHERE key_code = ?", (key_code,)).fetchone()

    if not key_data:
        conn.close()
        return jsonify({"valid": False, "message": "Key không tồn tại trên hệ thống!"})

    # Kiểm tra hết hạn
    expires_at = datetime.datetime.strptime(key_data['expires_at'], '%Y-%m-%d %H:%M:%S')
    if datetime.datetime.now() > expires_at:
        conn.close()
        return jsonify({"valid": False, "message": "Key này đã hết hạn sử dụng!"})

    # Kiểm tra IP/Thiết bị
    ip_list = [ip.strip() for ip in key_data['ip_logs'].split(',') if ip.strip()]
    
    if client_ip not in ip_list:
        if len(ip_list) >= key_data['max_devices']:
            conn.close()
            return jsonify({"valid": False, "message": f"Key đã đạt giới hạn tối đa ({key_data['max_devices']}) thiết bị!"})
        
        # Thêm IP mới
        ip_list.append(client_ip)
        new_ip_logs = ",".join(ip_list)
        new_used_devices = len(ip_list)
        
        conn.execute("UPDATE keys SET ip_logs = ?, used_devices = ? WHERE id = ?",
                     (new_ip_logs, new_used_devices, key_data['id']))
        conn.commit()

    conn.close()
    return jsonify({
        "valid": True,
        "message": "Xác thực thành công!",
        "expires_at": key_data['expires_at'],
        "client_ip": client_ip
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

