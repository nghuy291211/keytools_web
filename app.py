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
            plain_password TEXT DEFAULT '',
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
        cursor.execute("INSERT INTO admin_users (username, password, plain_password, is_super) VALUES (?, ?, ?, ?)",
                       ("nghuy291211", hashed_pw, "Huy@29122011@", 1))
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #fff; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; padding: 15px; }
        .card { background: #1e1e1e; padding: 25px; border-radius: 12px; width: 100%; max-width: 350px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid #2a2a2a; }
        h2 { color: #00e676; text-align: center; margin-top: 0; font-size: 20px; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 6px; border: 1px solid #333; outline: none; }
        input { background: #2a2a2a; color: #fff; font-size: 14px; }
        button { background: #00e676; color: #000; font-weight: bold; cursor: pointer; border: none; font-size: 15px; }
        .error { color: #ff5252; font-size: 13px; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>ĐĂNG NHẬP QUẢN TRỊ</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Tên đăng nhập" required>
            <input type="password" name="password" placeholder="Mật khẩu" required>
            <button type="submit">Đăng Nhập</button>
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 12px; }
        h2, h3, h4 { color: #00e676; margin-top: 0; }
        .container { max-width: 1000px; margin: auto; }
        .card { background: #1e1e1e; padding: 16px; margin-bottom: 16px; border-radius: 10px; border: 1px solid #2d2d2d; }
        
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; margin-bottom: 5px; font-size: 13px; color: #bbb; }
        input { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #3d3d3d; background: #2a2a2a; color: #fff; font-size: 14px; }
        
        .btn { padding: 10px 16px; border-radius: 6px; border: none; font-weight: bold; cursor: pointer; font-size: 14px; width: 100%; margin-top: 5px; }
        .btn-success { background: #00e676; color: #000; }
        .btn-warning { background: #ffb300; color: #000; }
        .btn-danger { background: #ff5252; color: #fff; padding: 6px 10px; font-size: 12px; width: auto; }
        .btn-copy { background: #00e676; color: #000; padding: 4px 8px; font-size: 12px; border-radius: 4px; border: none; font-weight: bold; cursor: pointer; margin-left: 6px; }
        
        .table-responsive { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 6px; border: 1px solid #333; }
        table { width: 100%; border-collapse: collapse; min-width: 600px; white-space: nowrap; }
        th, td { border: 1px solid #333; padding: 10px; text-align: left; font-size: 13px; }
        th { background: #2a2a2a; color: #00e676; }
        tr:nth-child(even) { background: #242424; }
        
        .header { display: flex; flex-direction: column; gap: 8px; margin-bottom: 15px; border-bottom: 1px solid #333; padding-bottom: 10px; }
        a.logout { color: #ff5252; text-decoration: none; font-weight: bold; }
        .alert { padding: 10px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; }
        .alert-success { background: #1b5e20; color: #81c784; }
        .alert-danger { background: #b71c1c; color: #e57373; }
        
        @media (min-width: 600px) {
            .header { flex-direction: row; justify-content: space-between; align-items: center; }
            .btn { width: auto; }
            .form-row { display: flex; gap: 10px; align-items: flex-end; }
            .form-row .form-group { flex: 1; margin-bottom: 0; }
        }
    </style>
    <script>
        function copyToClipboard(text) {
            if (!text) {
                alert('Không có nội dung để sao chép!');
                return;
            }
            navigator.clipboard.writeText(text).then(function() {
                alert('Đã sao chép thành công: ' + text);
            }, function(err) {
                alert('Lỗi sao chép: ' + err);
            });
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Hệ Thống Quản Lý Key</h2>
            <div>Xin chào, <b>{{ session['admin'] }}</b> | <a class="logout" href="/logout">Đăng xuất</a></div>
        </div>

        {% if msg %}
            <div class="alert alert-success">{{ msg }}</div>
        {% endif %}
        {% if err %}
            <div class="alert alert-danger">{{ err }}</div>
        {% endif %}

        <!-- Form Đổi Mật Khẩu -->
        <div class="card">
            <h3>Đổi Mật Khẩu Tài Khoản</h3>
            <form action="/change-password" method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <label>Mật khẩu cũ:</label>
                        <input type="password" name="old_password" required placeholder="Nhập mật khẩu hiện tại">
                    </div>
                    <div class="form-group">
                        <label>Mật khẩu mới:</label>
                        <input type="password" name="new_password" required placeholder="Nhập mật khẩu mới">
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn btn-warning">Đổi Mật Khẩu</button>
                    </div>
                </div>
            </form>
        </div>

        <!-- Form Tạo Key -->
        <div class="card">
            <h3>Tạo Key Mới</h3>
            <form action="/create-key" method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <label>Tên Key Custom (Để trống để tự tạo):</label>
                        <input type="text" name="custom_key" placeholder="Ví dụ: HUYTOOL2026">
                    </div>
                    <div class="form-group">
                        <label>Thời hạn (Giờ):</label>
                        <input type="number" name="hours" value="24" required min="1">
                    </div>
                    <div class="form-group">
                        <label>Số thiết bị (IP tối đa):</label>
                        <input type="number" name="max_devices" value="1" required min="1">
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn btn-success">Tạo Key</button>
                    </div>
                </div>
            </form>
        </div>

        <!-- Danh sách Key -->
        <div class="card">
            <h3>Danh Sách Key</h3>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Mã Key</th>
                            <th>Thiết bị (Dùng/Tối đa)</th>
                            <th>Trạng thái</th>
                            <th>IP Đã Dùng</th>
                            <th>Hết Hạn Lúc</th>
                            <th>Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for k in keys %}
                        <tr>
                            <td>{{ k['id'] }}</td>
                            <td>
                                <b style="color:#00e676;">{{ k['key_code'] }}</b>
                                <button class="btn-copy" onclick="copyToClipboard('{{ k['key_code'] }}')">Sao chép Key</button>
                            </td>
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
                                <a href="/delete-key/{{ k['id'] }}" onclick="return confirm('Bạn có chắc chắn muốn xóa key này?')">
                                    <button class="btn btn-danger">Xóa</button>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Quản lý Admin (Chỉ Super Admin mới xem và thực hiện được) -->
        {% if is_super_admin %}
        <div class="card">
            <h3>Tạo Tài Khoản Admin Chi Nhánh</h3>
            <form action="/create-admin" method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <input type="text" name="username" placeholder="Tên đăng nhập" required>
                    </div>
                    <div class="form-group">
                        <input type="password" name="password" placeholder="Mật khẩu" required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn btn-success">Tạo Admin</button>
                    </div>
                </div>
            </form>

            <h4 style="margin-top: 20px;">Danh Sách Admin</h4>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Tên Admin</th>
                            <th>Mật Khẩu</th>
                            <th>Cấp độ</th>
                            <th>Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for a in admins %}
                        <tr>
                            <td>{{ a['id'] }}</td>
                            <td>
                                <b>{{ a['username'] }}</b>
                                {% if a['is_super'] == 0 %}
                                    <button class="btn-copy" onclick="copyToClipboard('{{ a['username'] }}')">Copy TK</button>
                                {% endif %}
                            </td>
                            <td>
                                {% if a['is_super'] == 0 %}
                                    <span>{{ a['plain_password'] or '******' }}</span>
                                    <button class="btn-copy" onclick="copyToClipboard('{{ a['plain_password'] }}')">Copy MK</button>
                                {% else %}
                                    <i>Mật Khẩu Gốc</i>
                                {% endif %}
                            </td>
                            <td>{% if a['is_super'] == 1 %}<b style="color:#00e676">SUPER ADMIN</b>{% else %}Admin{% endif %}</td>
                            <td>
                                {% if a['is_super'] == 0 %}
                                    <a href="/delete-admin/{{ a['id'] }}" onclick="return confirm('Xóa tài khoản Admin này?')">
                                        <button class="btn btn-danger">Xóa Admin</button>
                                    </a>
                                {% else %}
                                    <i style="color:#777;">Không thể thao tác</i>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}
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
    msg = request.args.get('msg')
    err = request.args.get('err')
    conn = get_db()
    keys = conn.execute("SELECT * FROM keys ORDER BY id DESC").fetchall()
    admins = conn.execute("SELECT * FROM admin_users ORDER BY id ASC").fetchall()
    conn.close()
    return render_template_string(HTML_DASHBOARD, keys=keys, admins=admins, is_super_admin=(session.get('is_super') == 1), msg=msg, err=err)

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    current_username = session['admin']

    conn = get_db()
    user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (current_username,)).fetchone()

    if not user or not check_password_hash(user['password'], old_password):
        conn.close()
        return redirect(url_for('dashboard', err="Mật khẩu cũ không chính xác!"))

    new_hashed_pw = generate_password_hash(new_password)
    conn.execute("UPDATE admin_users SET password = ?, plain_password = ? WHERE username = ?", 
                 (new_hashed_pw, new_password, current_username))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard', msg="Đổi mật khẩu thành công!"))

@app.route('/create-key', methods=['POST'])
@login_required
def create_key():
    custom_key = request.form.get('custom_key', '').strip()
    hours = int(request.form.get('hours', 24))
    max_devices = int(request.form.get('max_devices', 1))
    
    if custom_key:
        key_code = custom_key
    else:
        key_code = "KEY-" + str(uuid.uuid4()).upper()[:12]
        
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=hours)
    
    conn = get_db()
    try:
        conn.execute("INSERT INTO keys (key_code, max_devices, expires_at) VALUES (?, ?, ?)",
                     (key_code, max_devices, expires_at.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
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
    # Kiểm tra phân quyền: Chỉ Super Admin mới được tạo tài khoản
    if session.get('is_super') != 1:
        return redirect(url_for('dashboard', err="Bạn không có quyền thực hiện chức năng này!"))
        
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    
    if not username or not password:
        return redirect(url_for('dashboard', err="Tài khoản và mật khẩu không được trống!"))

    conn = get_db()
    try:
        hashed_pw = generate_password_hash(password)
        conn.execute("INSERT INTO admin_users (username, password, plain_password, is_super) VALUES (?, ?, ?, 0)", 
                     (username, hashed_pw, password))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', msg=f"Tạo tài khoản {username} thành công!"))
    except sqlite3.IntegrityError:
        conn.close()
        return redirect(url_for('dashboard', err="Tên đăng nhập đã tồn tại!"))

@app.route('/delete-admin/<int:admin_id>')
@login_required
def delete_admin(admin_id):
    # Kiểm tra phân quyền: Chỉ Super Admin mới được xóa tài khoản
    if session.get('is_super') == 1:
        conn = get_db()
        conn.execute("DELETE FROM admin_users WHERE id = ? AND is_super = 0", (admin_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', msg="Đã xóa tài khoản Admin!"))
    return redirect(url_for('dashboard', err="Bạn không có quyền thực hiện chức năng này!"))

# ==================== API DÀNH CHO TOOL CLIENT ====================

@app.route('/api/verify-key', methods=['POST'])
def api_verify_key():
    data = request.get_json() or {}
    key_code = data.get('key', '').strip()

    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        client_ip = request.remote_addr.strip()

    if not key_code:
        return jsonify({"valid": False, "message": "Key không được để trống!"}), 400

    conn = get_db()
    key_data = conn.execute("SELECT * FROM keys WHERE key_code = ?", (key_code,)).fetchone()

    if not key_data:
        conn.close()
        return jsonify({"valid": False, "message": "Key không tồn tại trên hệ thống!"})

    expires_at = datetime.datetime.strptime(key_data['expires_at'], '%Y-%m-%d %H:%M:%S')
    if datetime.datetime.now() > expires_at:
        conn.close()
        return jsonify({"valid": False, "message": "Key này đã hết hạn sử dụng!"})

    raw_ip_logs = key_data['ip_logs'] or ''
    ip_list = [ip.strip() for ip in raw_ip_logs.split(',') if ip.strip()]

    if client_ip not in ip_list:
        if len(ip_list) >= key_data['max_devices']:
            conn.close()
            return jsonify({
                "valid": False, 
                "message": f"Key đã đạt giới hạn tối đa ({key_data['max_devices']}) thiết bị!"
            })
        
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
