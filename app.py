import sqlite3
import datetime
import uuid
import functools
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me_in_production"
app.permanent_session_lifetime = datetime.timedelta(days=30)

DATABASE = "key_system.db"

# ==================== CẤU HÌNH MÚI GIỜ VIỆT NAM (UTC+7) ====================
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))

def get_vn_now():
    """Lấy thời gian hiện tại chuẩn giờ Việt Nam (UTC+7)"""
    return datetime.datetime.now(VN_TZ)

def get_vn_now_str():
    """Trả về chuỗi thời gian Việt Nam dạng YYYY-MM-DD HH:MM:SS"""
    return get_vn_now().strftime('%Y-%m-%d %H:%M:%S')

# ==================== KẾT NỐI DATABASE ====================
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
            is_super INTEGER DEFAULT 0,
            last_login DATETIME,
            last_active DATETIME
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
            created_by TEXT DEFAULT 'Hệ thống',
            expires_at DATETIME NOT NULL,
            created_at DATETIME
        )
    ''')
    
    # Cập nhật cấu trúc bảng nếu nâng cấp từ DB cũ
    try:
        cursor.execute("ALTER TABLE keys ADD COLUMN created_by TEXT DEFAULT 'Hệ thống'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN last_login DATETIME")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN last_active DATETIME")
    except sqlite3.OperationalError:
        pass

    conn.commit()

    # Tạo tài khoản Super Admin mặc định
    super_admin = cursor.execute("SELECT * FROM admin_users WHERE username = ?", ("nghuy291211",)).fetchone()
    if not super_admin:
        hashed_pw = generate_password_hash("Huy@29122011@")
        cursor.execute("INSERT INTO admin_users (username, password, plain_password, is_super) VALUES (?, ?, ?, ?)",
                       ("nghuy291211", hashed_pw, "Huy@29122011@", 1))
        conn.commit()
    conn.close()

init_db()

def update_last_active():
    if 'admin' in session:
        conn = get_db()
        conn.execute("UPDATE admin_users SET last_active = ? WHERE username = ?", (get_vn_now_str(), session['admin']))
        conn.commit()
        conn.close()

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('login'))
        update_last_active()
        return f(*args, **kwargs)
    return decorated_function

# ==================== STYLES & TEMPLATES ====================

COMMON_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&display=swap');
    
    * { box-sizing: border-box; transition: all 0.25s ease-in-out; }
    body { 
        font-family: 'Rajdhani', -apple-system, sans-serif; 
        background: linear-gradient(135deg, #0a0a16 0%, #1a0933 50%, #0d1b2a 100%);
        background-attachment: fixed;
        color: #e0e6ed; 
        margin: 0; 
        padding: 15px; 
        min-height: 100vh;
    }
    
    h1, h2, h3, h4 { font-family: 'Orbitron', sans-serif; letter-spacing: 1px; }
    .neon-title { color: #00f3ff; text-shadow: 0 0 10px rgba(0,243,255,0.7), 0 0 20px rgba(0,243,255,0.4); }
    .neon-pink { color: #ff007f; text-shadow: 0 0 10px rgba(255,0,127,0.7); }
    .neon-purple { color: #b500ff; text-shadow: 0 0 10px rgba(181,0,255,0.7); }
    
    .card { 
        background: rgba(20, 24, 45, 0.75); 
        backdrop-filter: blur(12px);
        padding: 22px; 
        margin-bottom: 20px; 
        border-radius: 16px; 
        border: 1px solid rgba(0, 243, 255, 0.2); 
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5), inset 0 0 15px rgba(0, 243, 255, 0.05);
    }
    .card:hover {
        border-color: rgba(255, 0, 127, 0.4);
        box-shadow: 0 8px 32px 0 rgba(255, 0, 127, 0.2);
    }
    
    .form-group { margin-bottom: 12px; }
    .form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: #00f3ff; font-weight: 600; }
    input[type="text"], input[type="password"], input[type="number"] { 
        width: 100%; 
        padding: 12px 14px; 
        border-radius: 8px; 
        border: 1px solid #2a3b5c; 
        background: rgba(10, 14, 30, 0.8); 
        color: #fff; 
        font-size: 15px;
        outline: none;
    }
    input:focus { border-color: #ff007f; box-shadow: 0 0 12px rgba(255,0,127,0.5); }
    
    .btn { 
        padding: 10px 18px; 
        border-radius: 8px; 
        border: none; 
        font-weight: bold; 
        cursor: pointer; 
        font-size: 14px; 
        font-family: 'Orbitron', sans-serif;
        display: inline-block;
        text-align: center;
        text-decoration: none;
        text-transform: uppercase;
    }
    .btn-glow-green { background: linear-gradient(45deg, #00e676, #00b0ff); color: #000; box-shadow: 0 0 15px rgba(0,230,118,0.4); }
    .btn-glow-green:hover { box-shadow: 0 0 25px rgba(0,230,118,0.8); transform: translateY(-2px); }
    
    .btn-glow-pink { background: linear-gradient(45deg, #ff007f, #7928ca); color: #fff; box-shadow: 0 0 15px rgba(255,0,127,0.4); }
    .btn-glow-pink:hover { box-shadow: 0 0 25px rgba(255,0,127,0.8); transform: translateY(-2px); }
    
    .btn-danger { background: #ff1744; color: #fff; padding: 6px 12px; font-size: 12px; box-shadow: 0 0 10px rgba(255,23,68,0.4); }
    .btn-danger:hover { background: #d50000; box-shadow: 0 0 18px rgba(255,23,68,0.8); }
    
    .btn-copy { background: rgba(0, 243, 255, 0.15); color: #00f3ff; border: 1px solid #00f3ff; padding: 4px 10px; font-size: 11px; border-radius: 6px; cursor: pointer; font-weight: bold; margin-left: 6px; }
    .btn-copy:hover { background: #00f3ff; color: #000; box-shadow: 0 0 10px #00f3ff; }
    
    .table-responsive { width: 100%; overflow-x: auto; border-radius: 10px; border: 1px solid rgba(0, 243, 255, 0.2); }
    table { width: 100%; border-collapse: collapse; min-width: 650px; white-space: nowrap; }
    th, td { border-bottom: 1px solid rgba(255,255,255,0.08); padding: 12px 15px; text-align: left; font-size: 14px; }
    th { background: rgba(0, 243, 255, 0.1); color: #00f3ff; font-family: 'Orbitron', sans-serif; font-size: 12px; }
    tr:hover { background: rgba(255, 0, 127, 0.08); }
    
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }
    .badge-online { background: rgba(0,230,118,0.2); color: #00e676; border: 1px solid #00e676; box-shadow: 0 0 8px rgba(0,230,118,0.5); }
    .badge-offline { background: rgba(158,158,158,0.2); color: #9e9e9e; border: 1px solid #757575; }
    
    .container { max-width: 1100px; margin: auto; }
    .header { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; border-bottom: 2px solid rgba(0,243,255,0.3); padding-bottom: 15px; }
    .nav-links a { color: #00f3ff; text-decoration: none; font-weight: bold; margin-left: 12px; font-size: 14px; }
    .nav-links a:hover { color: #ff007f; text-shadow: 0 0 8px #ff007f; }
    
    .alert { padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; border: 1px solid; }
    .alert-success { background: rgba(0, 230, 118, 0.15); border-color: #00e676; color: #69f0ae; }
    .alert-danger { background: rgba(255, 23, 68, 0.15); border-color: #ff1744; color: #ff8a80; }
    
    .checkbox-container { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #bbb; cursor: pointer; margin: 10px 0; }
    .checkbox-container input { width: 16px; height: 16px; accent-color: #ff007f; cursor: pointer; }

    @media (min-width: 600px) {
        .header { flex-direction: row; justify-content: space-between; align-items: center; }
        .form-row { display: flex; gap: 12px; align-items: flex-end; }
        .form-row .form-group { flex: 1; margin-bottom: 0; }
    }
</style>
"""

HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Đăng nhập Admin Cyber</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """ + COMMON_CSS + """
    <style>
        body { display:flex; justify-content:center; align-items:center; height:100vh; }
        .login-card { width: 100%; max-width: 380px; border: 1px solid rgba(255,0,127,0.4); box-shadow: 0 0 25px rgba(255,0,127,0.2); }
    </style>
</head>
<body>
    <div class="card login-card">
        <h2 class="neon-title" style="text-align: center; margin-top:0;">SYSTEM LOGIN</h2>
        {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group">
                <label>TÊN ĐĂNG NHẬP</label>
                <input type="text" name="username" placeholder="Nhập username..." required>
            </div>
            <div class="form-group">
                <label>MẬT KHẨU</label>
                <input type="password" name="password" placeholder="Nhập password..." required>
            </div>
            
            <label class="checkbox-container">
                <input type="checkbox" name="remember" value="yes">
                Ghi nhớ đăng nhập (30 ngày)
            </label>
            
            <button type="submit" class="btn btn-glow-pink" style="width:100%; margin-top:15px;">ĐĂNG NHẬP</button>
        </form>
    </div>
</body>
</html>
"""

HTML_CHANGE_PASSWORD = """
<!DOCTYPE html>
<html>
<head>
    <title>Đổi Mật Khẩu</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """ + COMMON_CSS + """
</head>
<body>
    <div class="container" style="max-width: 500px; margin-top: 50px;">
        <div class="card">
            <h2 class="neon-pink" style="margin-top:0; text-align:center;">ĐỔI MẬT KHẨU</h2>
            
            {% if msg %}<div class="alert alert-success">{{ msg }}</div>{% endif %}
            {% if err %}<div class="alert alert-danger">{{ err }}</div>{% endif %}

            <form action="/change-password" method="POST">
                <div class="form-group">
                    <label>Mật khẩu hiện tại:</label>
                    <input type="password" name="old_password" required placeholder="Nhập mật khẩu cũ">
                </div>
                <div class="form-group">
                    <label>Mật khẩu mới:</label>
                    <input type="password" name="new_password" required placeholder="Nhập mật khẩu mới">
                </div>
                <div style="display:flex; gap:10px; margin-top: 20px;">
                    <a href="/" class="btn" style="background:#333; color:#fff; flex:1;">QUAY LẠI</a>
                    <button type="submit" class="btn btn-glow-pink" style="flex:1;">CẬP NHẬT</button>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
"""

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Cyber Key Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """ + COMMON_CSS + """
    <script>
        function copyToClipboard(text) {
            if (!text) return alert('Không có nội dung!');
            navigator.clipboard.writeText(text).then(function() {
                alert('Đã sao chép: ' + text);
            }, function(err) {
                alert('Lỗi: ' + err);
            });
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 class="neon-title" style="margin:0;">KEY MANAGEMENT SYSTEM</h2>
            <div class="nav-links">
                Tài khoản: <b class="neon-pink">{{ session['admin'] }}</b>
                <a href="/change-password">[Đổi Mật Khẩu]</a>
                <a href="/logout" style="color:#ff1744;">[Thoát]</a>
            </div>
        </div>

        {% if msg %}<div class="alert alert-success">{{ msg }}</div>{% endif %}
        {% if err %}<div class="alert alert-danger">{{ err }}</div>{% endif %}

        <!-- Form Tạo Key -->
        <div class="card">
            <h3 class="neon-pink">TẠO KEY MỚI</h3>
            <form action="/create-key" method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <label>Tên Key Custom (Bỏ trống để tự sinh):</label>
                        <input type="text" name="custom_key" placeholder="Ví dụ: VIP-KEY-2026">
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
                        <button type="submit" class="btn btn-glow-green" style="width:100%;">TẠO KEY</button>
                    </div>
                </div>
            </form>
        </div>

        <!-- Danh sách Key -->
        <div class="card">
            <h3 class="neon-title">DANH SÁCH KEY</h3>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Mã Key</th>
                            <th>Người Tạo</th>
                            <th>Thiết bị (Dùng/Tối đa)</th>
                            <th>Trạng thái</th>
                            <th>IP Đã Dùng</th>
                            <th>Hết Hạn Lúc (Giờ VN)</th>
                            <th>Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for k in keys %}
                        <tr>
                            <td>{{ k['id'] }}</td>
                            <td>
                                <b class="neon-title">{{ k['key_code'] }}</b>
                                <button class="btn-copy" onclick="copyToClipboard('{{ k['key_code'] }}')">Copy</button>
                            </td>
                            <td><b style="color:#ff007f;">{{ k['created_by'] or 'Hệ thống' }}</b></td>
                            <td>{{ k['used_devices'] }} / {{ k['max_devices'] }}</td>
                            <td>
                                {% if k['status'] == 'active' %}
                                    <span style="color:#00e676; font-weight:bold;">HOẠT ĐỘNG</span>
                                {% else %}
                                    <span style="color:#ff1744; font-weight:bold;">VÔ HIỆU</span>
                                {% endif %}
                            </td>
                            <td><small style="color:#aaa;">{{ k['ip_logs'] or 'Chưa có' }}</small></td>
                            <td>{{ k['expires_at'] }}</td>
                            <td>
                                <a href="/delete-key/{{ k['id'] }}" onclick="return confirm('Bạn có chắc muốn xóa key này?')">
                                    <button class="btn btn-danger">XÓA</button>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Quản lý Admin (Super Admin) -->
        {% if is_super_admin %}
        <div class="card">
            <h3 class="neon-purple">QUẢN LÝ ADMIN & TRẠNG THÁI</h3>
            <form action="/create-admin" method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <input type="text" name="username" placeholder="Tên đăng nhập Admin mới" required>
                    </div>
                    <div class="form-group">
                        <input type="password" name="password" placeholder="Mật khẩu" required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn btn-glow-pink" style="width:100%;">TẠO ADMIN</button>
                    </div>
                </div>
            </form>

            <h4 style="margin-top:25px; color:#00f3ff;">DANH SÁCH ADMIN HỆ THỐNG</h4>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Tên Admin</th>
                            <th>Mật Khẩu</th>
                            <th>Cấp độ</th>
                            <th>Trạng Thái</th>
                            <th>Lần Cuối Hoạt Động (Giờ VN)</th>
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
                                    <button class="btn-copy" onclick="copyToClipboard('{{ a['username'] }}')">Copy</button>
                                {% endif %}
                            </td>
                            <td>
                                {% if a['is_super'] == 0 %}
                                    <span>{{ a['plain_password'] or '******' }}</span>
                                    <button class="btn-copy" onclick="copyToClipboard('{{ a['plain_password'] }}')">Copy</button>
                                {% else %}
                                    <i>Bảo mật Gốc</i>
                                {% endif %}
                            </td>
                            <td>{% if a['is_super'] == 1 %}<b style="color:#00e676">SUPER ADMIN</b>{% else %}Admin Chi Nhánh{% endif %}</td>
                            <td>
                                {% if a['is_online'] %}
                                    <span class="badge badge-online">● ONLINE</span>
                                {% else %}
                                    <span class="badge badge-offline">○ OFFLINE</span>
                                {% endif %}
                            </td>
                            <td><small style="color:#aaa;">{{ a['last_active'] or 'Chưa ghi nhận' }}</small></td>
                            <td>
                                {% if a['is_super'] == 0 %}
                                    <a href="/delete-admin/{{ a['id'] }}" onclick="return confirm('Xóa Admin này?')">
                                        <button class="btn btn-danger">XÓA</button>
                                    </a>
                                {% else %}
                                    <i style="color:#555;">Mặc định</i>
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

# ==================== ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember')
        
        conn = get_db()
        user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['admin'] = user['username']
            session['is_super'] = user['is_super']
            
            if remember == 'yes':
                session.permanent = True
            else:
                session.permanent = False
                
            now_str = get_vn_now_str()
            conn.execute("UPDATE admin_users SET last_login = ?, last_active = ? WHERE id = ?", (now_str, now_str, user['id']))
            conn.commit()
            conn.close()
            
            return redirect(url_for('dashboard'))
        else:
            conn.close()
            error = "Tài khoản hoặc mật khẩu không đúng!"
            
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
    raw_admins = conn.execute("SELECT * FROM admin_users ORDER BY id ASC").fetchall()
    
    admins = []
    now = get_vn_now().replace(tzinfo=None)
    for a in raw_admins:
        admin_dict = dict(a)
        is_online = False
        if admin_dict.get('last_active'):
            try:
                last_act = datetime.datetime.strptime(admin_dict['last_active'], '%Y-%m-%d %H:%M:%S')
                if (now - last_act).total_seconds() < 300: # Trong vòng 5 phút
                    is_online = True
            except ValueError:
                pass
        admin_dict['is_online'] = is_online
        admins.append(admin_dict)
        
    conn.close()
    return render_template_string(HTML_DASHBOARD, keys=keys, admins=admins, is_super_admin=(session.get('is_super') == 1), msg=msg, err=err)

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'GET':
        return render_template_string(HTML_CHANGE_PASSWORD)
        
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    current_username = session['admin']

    conn = get_db()
    user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (current_username,)).fetchone()

    if not user or not check_password_hash(user['password'], old_password):
        conn.close()
        return render_template_string(HTML_CHANGE_PASSWORD, err="Mật khẩu hiện tại không chính xác!")

    new_hashed_pw = generate_password_hash(new_password)
    conn.execute("UPDATE admin_users SET password = ?, plain_password = ? WHERE username = ?", 
                 (new_hashed_pw, new_password, current_username))
    conn.commit()
    conn.close()

    return render_template_string(HTML_CHANGE_PASSWORD, msg="Đã cập nhật mật khẩu mới thành công!")

@app.route('/create-key', methods=['POST'])
@login_required
def create_key():
    custom_key = request.form.get('custom_key', '').strip()
    hours = int(request.form.get('hours', 24))
    max_devices = int(request.form.get('max_devices', 1))
    created_by = session.get('admin', 'Unknown')
    
    if custom_key:
        key_code = custom_key
    else:
        key_code = "KEY-" + str(uuid.uuid4()).upper()[:12]
        
    expires_at = get_vn_now() + datetime.timedelta(hours=hours)
    created_at = get_vn_now()
    
    conn = get_db()
    try:
        conn.execute("INSERT INTO keys (key_code, max_devices, created_by, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
                     (key_code, max_devices, created_by, 
                      expires_at.strftime('%Y-%m-%d %H:%M:%S'), 
                      created_at.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return redirect(url_for('dashboard', err="Mã Key này đã tồn tại trên hệ thống!"))
    conn.close()
    return redirect(url_for('dashboard', msg=f"Đã tạo key thành công bởi {created_by}!"))

@app.route('/delete-key/<int:key_id>')
@login_required
def delete_key(key_id):
    conn = get_db()
    conn.execute("DELETE FROM keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard', msg="Đã xóa key!"))

@app.route('/create-admin', methods=['POST'])
@login_required
def create_admin():
    if session.get('is_super') != 1:
        return redirect(url_for('dashboard', err="Bạn không có quyền thực hiện!"))
        
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    
    if not username or not password:
        return redirect(url_for('dashboard', err="Vui lòng điền đầy đủ thông tin!"))

    conn = get_db()
    try:
        hashed_pw = generate_password_hash(password)
        conn.execute("INSERT INTO admin_users (username, password, plain_password, is_super) VALUES (?, ?, ?, 0)", 
                     (username, hashed_pw, password))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', msg=f"Tạo tài khoản Admin {username} thành công!"))
    except sqlite3.IntegrityError:
        conn.close()
        return redirect(url_for('dashboard', err="Tên tài khoản này đã tồn tại!"))

@app.route('/delete-admin/<int:admin_id>')
@login_required
def delete_admin(admin_id):
    if session.get('is_super') == 1:
        conn = get_db()
        conn.execute("DELETE FROM admin_users WHERE id = ? AND is_super = 0", (admin_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', msg="Đã xóa tài khoản Admin thành công!"))
    return redirect(url_for('dashboard', err="Bạn không có quyền thực hiện!"))

# ==================== API FOR CLIENT TOOL ====================

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
    now_vn = get_vn_now().replace(tzinfo=None)
    
    if now_vn > expires_at:
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
