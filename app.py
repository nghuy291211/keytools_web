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
    return datetime.datetime.now(VN_TZ)

def get_vn_now_str():
    return get_vn_now().strftime('%Y-%m-%d %H:%M:%S')

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr.strip() if request.remote_addr else "127.0.0.1"

# ==================== KẾT NỐI DATABASE ====================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            plain_password TEXT DEFAULT '',
            is_super INTEGER DEFAULT 0,
            last_login DATETIME,
            last_active DATETIME,
            last_ip TEXT DEFAULT ''
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT UNIQUE NOT NULL,
            max_devices INTEGER DEFAULT 1,
            used_devices INTEGER DEFAULT 0,
            usage_limit INTEGER DEFAULT 1,
            current_usage INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            ip_logs TEXT DEFAULT '',
            created_by TEXT DEFAULT 'Hệ thống',
            created_at DATETIME
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE keys ADD COLUMN usage_limit INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE keys ADD COLUMN current_usage INTEGER DEFAULT 0")
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
    try:
        cursor.execute("ALTER TABLE admin_users ADD COLUMN last_ip TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    conn.commit()

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
        conn.execute("UPDATE admin_users SET last_active = ?, last_ip = ? WHERE username = ?", 
                     (get_vn_now_str(), get_client_ip(), session['admin']))
        conn.commit()
        conn.close()

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('login'))
        conn = get_db()
        user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (session['admin'],)).fetchone()
        conn.close()
        if not user:
            session.clear()
            return redirect(url_for('login', error="account_removed"))
        update_last_active()
        return f(*args, **kwargs)
    return decorated_function

# ==================== COMMON CSS + I18N SCRIPT ====================
COMMON_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&display=swap');
    * { box-sizing: border-box; transition: all 0.25s ease-in-out; }
    body { font-family: 'Rajdhani', -apple-system, sans-serif; background: linear-gradient(135deg, #0a0a16 0%, #1a0933 50%, #0d1b2a 100%); background-attachment: fixed; color: #e0e6ed; margin: 0; padding: 15px; min-height: 100vh; }
    h1, h2, h3, h4 { font-family: 'Orbitron', sans-serif; letter-spacing: 1px; }
    .neon-title { color: #00f3ff; text-shadow: 0 0 10px rgba(0,243,255,0.7), 0 0 20px rgba(0,243,255,0.4); }
    .neon-pink { color: #ff007f; text-shadow: 0 0 10px rgba(255,0,127,0.7); }
    .neon-purple { color: #b500ff; text-shadow: 0 0 10px rgba(181,0,255,0.7); }
    .card { background: rgba(20, 24, 45, 0.75); backdrop-filter: blur(12px); padding: 22px; margin-bottom: 20px; border-radius: 16px; border: 1px solid rgba(0, 243, 255, 0.2); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5), inset 0 0 15px rgba(0, 243, 255, 0.05); }
    .card:hover { border-color: rgba(255, 0, 127, 0.4); box-shadow: 0 8px 32px 0 rgba(255, 0, 127, 0.2); }
    .form-group { margin-bottom: 12px; }
    .form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: #00f3ff; font-weight: 600; }
    input[type="text"], input[type="password"], input[type="number"] { width: 100%; padding: 12px 14px; border-radius: 8px; border: 1px solid #2a3b5c; background: rgba(10, 14, 30, 0.8); color: #fff; font-size: 15px; outline: none; }
    input:focus { border-color: #ff007f; box-shadow: 0 0 12px rgba(255,0,127,0.5); }
    .btn { padding: 10px 18px; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; font-size: 14px; font-family: 'Orbitron', sans-serif; display: inline-block; text-align: center; text-decoration: none; text-transform: uppercase; }
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
    .header { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; border-bottom: 2px solid rgba(0,243,255,0.3); padding-bottom: 15px; position: relative; }
    .nav-links a { color: #00f3ff; text-decoration: none; font-weight: bold; margin-left: 12px; font-size: 14px; }
    .nav-links a:hover { color: #ff007f; text-shadow: 0 0 8px #ff007f; }
    .alert { padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; border: 1px solid; }
    .alert-success { background: rgba(0, 230, 118, 0.15); border-color: #00e676; color: #69f0ae; }
    .alert-danger { background: rgba(255, 23, 68, 0.15); border-color: #ff1744; color: #ff8a80; }
    .checkbox-container { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #bbb; cursor: pointer; margin: 10px 0; }
    .checkbox-container input { width: 16px; height: 16px; accent-color: #ff007f; cursor: pointer; }

    /* Language Toggle */
    .lang-toggle {
        position: absolute;
        top: 0;
        right: 0;
        background: rgba(10, 14, 30, 0.8);
        border: 1px solid rgba(0, 243, 255, 0.4);
        color: #8a8a93;
        padding: 7px 14px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 700;
        font-family: 'Orbitron', sans-serif;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        letter-spacing: 0.5px;
    }
    .lang-toggle:hover {
        border-color: #ff007f;
        color: #fff;
        box-shadow: 0 0 15px rgba(255, 0, 127, 0.5);
        background: rgba(255, 0, 127, 0.1);
    }
    .lang-toggle .active-lang {
        color: #00f3ff;
        text-shadow: 0 0 8px rgba(0, 243, 255, 0.8);
    }
    .lang-toggle .divider { color: #444; font-weight: normal; }

    /* Login page specific */
    .login-wrap { display: flex; justify-content: center; align-items: center; min-height: 90vh; }
    .login-card { width: 100%; max-width: 380px; border: 1px solid rgba(255,0,127,0.4); box-shadow: 0 0 25px rgba(255,0,127,0.2); position: relative; }

    @media (min-width: 600px) {
        .header { flex-direction: row; justify-content: space-between; align-items: center; padding-right: 110px; }
        .form-row { display: flex; gap: 12px; align-items: flex-end; }
        .form-row .form-group { flex: 1; margin-bottom: 0; }
    }
</style>
"""

I18N_SCRIPT = """
<script>
    const I18N = {
        vi: {
            /* Login */
            loginTitle: "ĐĂNG NHẬP HỆ THỐNG",
            lblUsername: "TÊN ĐĂNG NHẬP",
            lblPassword: "MẬT KHẨU",
            phUsername: "Nhập username...",
            phPassword: "Nhập password...",
            rememberMe: "Ghi nhớ đăng nhập (30 ngày)",
            btnLogin: "ĐĂNG NHẬP",

            /* Header */
            accountLabel: "Tài khoản:",
            linkChangeAccount: "[Đổi Tên / Mật Khẩu]",
            linkLogout: "[Thoát]",

            /* Create Key */
            createKeyTitle: "TẠO KEY MỚI",
            lblCustomKey: "Tên Key Custom (Bỏ trống để tự sinh):",
            phCustomKey: "Ví dụ: VIP-KEY-2026",
            lblUsageLimit: "Giới hạn lượt dùng:",
            lblMaxDevices: "Số thiết bị (IP tối đa):",
            btnCreateKey: "TẠO KEY",

            /* Key List */
            keyListTitle: "DANH SÁCH KEY",
            thID: "ID",
            thKeyCode: "Mã Key",
            thCreatedBy: "Người Tạo",
            thDevices: "Thiết bị",
            thUsage: "Lượt Dùng",
            thStatus: "Trạng thái",
            thIPs: "IP Đã Dùng",
            thCreatedAt: "Ngày Tạo",
            thAction: "Hành Động",
            statusActive: "HOẠT ĐỘNG",
            statusDisabled: "VÔ HIỆU",
            noIPs: "Chưa có",
            btnDelete: "XÓA",
            btnCopy: "Copy",

            /* Admin Management */
            adminMgmtTitle: "QUẢN LÝ ADMIN & TRẠNG THÁI",
            phNewAdminUser: "Tên đăng nhập Admin mới",
            phPassword: "Mật khẩu",
            btnCreateAdmin: "TẠO ADMIN",
            adminListTitle: "DANH SÁCH ADMIN HỆ THỐNG",
            thAdminName: "Tên Admin",
            thLevel: "Cấp độ",
            thLoginIP: "IP Đăng Nhập",
            thLastActive: "Lần Cuối Hoạt Động",
            levelSuper: "SUPER ADMIN",
            levelBranch: "Admin Chi Nhánh",
            securedRoot: "Bảo mật Gốc",
            notRecorded: "Chưa ghi nhận",
            defaultLabel: "Mặc định",
            badgeOnline: "● ONLINE",
            badgeOffline: "○ OFFLINE",

            /* Change Password Page */
            accSettingsTitle: "CÀI ĐẶT TÀI KHOẢN",
            lblNewUsername: "Tên đăng nhập mới:",
            phNewUsername: "Nhập tên đăng nhập mới",
            lblOldPasswordConfirm: "Mật khẩu hiện tại (Xác nhận):",
            phOldPassword: "Nhập mật khẩu hiện tại",
            lblNewPassword: "Mật khẩu mới (Để trống nếu giữ nguyên):",
            phNewPassword: "Nhập mật khẩu mới",
            btnBack: "QUAY LẠI",
            btnUpdate: "CẬP NHẬT",

            /* Confirm dialogs */
            confirmDeleteKey: "Bạn có chắc muốn xóa key này?",
            confirmDeleteAdmin: "Xóa Admin này?",

            /* Server messages */
            account_removed: "Tài khoản của bạn đã bị xoá khỏi hệ thống!",
            login_failed: "Tài khoản hoặc mật khẩu không đúng!",
            wrong_password: "Mật khẩu hiện tại không chính xác!",
            username_exists: "Tên đăng nhập mới đã tồn tại trên hệ thống!",
            password_updated: "Đã cập nhật thông tin tài khoản thành công!",
            key_exists: "Mã Key này đã tồn tại trên hệ thống!",
            create_key_success: "Đã tạo key thành công!",
            delete_key_success: "Đã xóa key!",
            no_permission: "Bạn không có quyền thực hiện!",
            fill_all_fields: "Vui lòng điền đầy đủ thông tin!",
            admin_exists: "Tên tài khoản này đã tồn tại!",
            create_admin_success: "Tạo tài khoản Admin thành công!",
            delete_admin_success: "Đã xóa tài khoản Admin thành công!",

            /* Copy alert */
            copyNoContent: "Không có nội dung để sao chép!",
            copySuccess: "Đã sao chép: "
        },
        en: {
            /* Login */
            loginTitle: "SYSTEM LOGIN",
            lblUsername: "USERNAME",
            lblPassword: "PASSWORD",
            phUsername: "Enter username...",
            phPassword: "Enter password...",
            rememberMe: "Remember me (30 days)",
            btnLogin: "LOGIN",

            /* Header */
            accountLabel: "Account:",
            linkChangeAccount: "[Change Name / Password]",
            linkLogout: "[Logout]",

            /* Create Key */
            createKeyTitle: "CREATE NEW KEY",
            lblCustomKey: "Custom Key Name (Leave blank to auto-generate):",
            phCustomKey: "Example: VIP-KEY-2026",
            lblUsageLimit: "Usage limit:",
            lblMaxDevices: "Max devices (IPs):",
            btnCreateKey: "CREATE KEY",

            /* Key List */
            keyListTitle: "KEY LIST",
            thID: "ID",
            thKeyCode: "Key Code",
            thCreatedBy: "Created By",
            thDevices: "Devices",
            thUsage: "Usage",
            thStatus: "Status",
            thIPs: "IPs Used",
            thCreatedAt: "Created At",
            thAction: "Action",
            statusActive: "ACTIVE",
            statusDisabled: "DISABLED",
            noIPs: "None",
            btnDelete: "DELETE",
            btnCopy: "Copy",

            /* Admin Management */
            adminMgmtTitle: "ADMIN MANAGEMENT & STATUS",
            phNewAdminUser: "New Admin Username",
            phPassword: "Password",
            btnCreateAdmin: "CREATE ADMIN",
            adminListTitle: "SYSTEM ADMIN LIST",
            thAdminName: "Admin Name",
            thLevel: "Level",
            thLoginIP: "Login IP",
            thLastActive: "Last Active",
            levelSuper: "SUPER ADMIN",
            levelBranch: "Branch Admin",
            securedRoot: "Secured",
            notRecorded: "Not recorded",
            defaultLabel: "Default",
            badgeOnline: "● ONLINE",
            badgeOffline: "○ OFFLINE",

            /* Change Password Page */
            accSettingsTitle: "ACCOUNT SETTINGS",
            lblNewUsername: "New username:",
            phNewUsername: "Enter new username",
            lblOldPasswordConfirm: "Current password (Confirm):",
            phOldPassword: "Enter current password",
            lblNewPassword: "New password (Leave blank to keep current):",
            phNewPassword: "Enter new password",
            btnBack: "BACK",
            btnUpdate: "UPDATE",

            /* Confirm dialogs */
            confirmDeleteKey: "Are you sure you want to delete this key?",
            confirmDeleteAdmin: "Delete this Admin?",

            /* Server messages */
            account_removed: "Your account has been removed from the system!",
            login_failed: "Incorrect username or password!",
            wrong_password: "Current password is incorrect!",
            username_exists: "New username already exists!",
            password_updated: "Account updated successfully!",
            key_exists: "This key already exists!",
            create_key_success: "Key created successfully!",
            delete_key_success: "Key deleted!",
            no_permission: "You don't have permission!",
            fill_all_fields: "Please fill in all fields!",
            admin_exists: "This username already exists!",
            create_admin_success: "Admin account created successfully!",
            delete_admin_success: "Admin account deleted successfully!",

            /* Copy alert */
            copyNoContent: "Nothing to copy!",
            copySuccess: "Copied: "
        }
    };

    let currentLang = localStorage.getItem('keytools_lang') || 'vi';

    function t(key) {
        return (I18N[currentLang] && I18N[currentLang][key]) || key;
    }

    function applyTranslations() {
        // data-i18n text
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (I18N[currentLang][key] !== undefined) el.textContent = t(key);
        });
        // data-i18n-ph (placeholders)
        document.querySelectorAll('[data-i18n-ph]').forEach(el => {
            const key = el.getAttribute('data-i18n-ph');
            if (I18N[currentLang][key] !== undefined) el.placeholder = t(key);
        });
        // data-i18n-title
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            if (I18N[currentLang][key] !== undefined) el.title = t(key);
        });

        // Server messages (alerts)
        document.querySelectorAll('.alert[data-msg-key]').forEach(el => {
            const key = el.getAttribute('data-msg-key');
            if (I18N[currentLang][key] !== undefined) el.textContent = t(key);
        });

        // Lang toggle active class
        const viEl = document.getElementById('langVI');
        const enEl = document.getElementById('langEN');
        const flagEl = document.getElementById('flagIcon');
        if (viEl && enEl && flagEl) {
            viEl.classList.toggle('active-lang', currentLang === 'vi');
            enEl.classList.toggle('active-lang', currentLang === 'en');
            flagEl.textContent = currentLang === 'vi' ? '🇻🇳' : '🇬🇧';
        }

        // Update page title if has data
        document.documentElement.lang = currentLang;
    }

    function toggleLanguage() {
        currentLang = currentLang === 'vi' ? 'en' : 'vi';
        localStorage.setItem('keytools_lang', currentLang);
        applyTranslations();
    }

    function copyToClipboard(text) {
        if (!text) return alert(t('copyNoContent'));
        navigator.clipboard.writeText(text).then(function() {
            alert(t('copySuccess') + text);
        }, function(err) {
            alert('Error: ' + err);
        });
    }

    // Auto-apply on DOM ready
    document.addEventListener('DOMContentLoaded', () => {
        applyTranslations();

        // Confirm delete links
        document.querySelectorAll('.delete-link').forEach(link => {
            link.addEventListener('click', function(e) {
                const key = this.getAttribute('data-confirm-key');
                if (!confirm(t(key))) e.preventDefault();
            });
        });
    });

    // Apply as soon as possible too (in case DOMContentLoaded already fired)
    if (document.readyState !== 'loading') applyTranslations();
</script>
"""

# ==================== TEMPLATES ====================

HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """ + COMMON_CSS + """
</head>
<body>
    <div class="login-wrap">
        <div class="card login-card">
            <button class="lang-toggle" onclick="toggleLanguage()">
                <span id="flagIcon">🇻🇳</span>
                <span id="langVI" class="active-lang">VI</span>
                <span class="divider">|</span>
                <span id="langEN">EN</span>
            </button>

            <h2 class="neon-title" style="text-align: center; margin-top:0;" data-i18n="loginTitle">SYSTEM LOGIN</h2>
            {% if error %}<div class="alert alert-danger" data-msg-key="{{ error }}"></div>{% endif %}
            <form method="POST">
                <div class="form-group">
                    <label data-i18n="lblUsername">TÊN ĐĂNG NHẬP</label>
                    <input type="text" name="username" data-i18n-ph="phUsername" placeholder="Nhập username..." required>
                </div>
                <div class="form-group">
                    <label data-i18n="lblPassword">MẬT KHẨU</label>
                    <input type="password" name="password" data-i18n-ph="phPassword" placeholder="Nhập password..." required>
                </div>
                <label class="checkbox-container">
                    <input type="checkbox" name="remember" value="yes">
                    <span data-i18n="rememberMe">Ghi nhớ đăng nhập (30 ngày)</span>
                </label>
                <button type="submit" class="btn btn-glow-pink" style="width:100%; margin-top:15px;" data-i18n="btnLogin">ĐĂNG NHẬP</button>
            </form>
        </div>
    </div>
    """ + I18N_SCRIPT + """
</body>
</html>
"""

HTML_CHANGE_PASSWORD = """
<!DOCTYPE html>
<html>
<head>
    <title>Account Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """ + COMMON_CSS + """
</head>
<body>
    <div class="container" style="max-width: 500px; margin-top: 50px;">
        <div class="card" style="position:relative;">
            <button class="lang-toggle" onclick="toggleLanguage()">
                <span id="flagIcon">🇻🇳</span>
                <span id="langVI" class="active-lang">VI</span>
                <span class="divider">|</span>
                <span id="langEN">EN</span>
            </button>

            <h2 class="neon-pink" style="margin-top:0; text-align:center; padding-right: 90px;" data-i18n="accSettingsTitle">CÀI ĐẶT TÀI KHOẢN</h2>

            {% if msg %}<div class="alert alert-success" data-msg-key="{{ msg }}"></div>{% endif %}
            {% if err %}<div class="alert alert-danger" data-msg-key="{{ err }}"></div>{% endif %}

            <form action="/change-password" method="POST">
                <div class="form-group">
                    <label data-i18n="lblNewUsername">Tên đăng nhập mới:</label>
                    <input type="text" name="new_username" value="{{ current_username }}" required data-i18n-ph="phNewUsername" placeholder="Nhập tên đăng nhập mới">
                </div>
                <div class="form-group">
                    <label data-i18n="lblOldPasswordConfirm">Mật khẩu hiện tại (Xác nhận):</label>
                    <input type="password" name="old_password" required data-i18n-ph="phOldPassword" placeholder="Nhập mật khẩu hiện tại">
                </div>
                <div class="form-group">
                    <label data-i18n="lblNewPassword">Mật khẩu mới (Để trống nếu giữ nguyên):</label>
                    <input type="password" name="new_password" data-i18n-ph="phNewPassword" placeholder="Nhập mật khẩu mới">
                </div>
                <div style="display:flex; gap:10px; margin-top: 20px;">
                    <a href="/" class="btn" style="background:#333; color:#fff; flex:1;" data-i18n="btnBack">QUAY LẠI</a>
                    <button type="submit" class="btn btn-glow-pink" style="flex:1;" data-i18n="btnUpdate">CẬP NHẬT</button>
                </div>
            </form>
        </div>
    </div>
    """ + I18N_SCRIPT + """
</body>
</html>
"""

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Key Management System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """ + COMMON_CSS + """
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 class="neon-title" style="margin:0;">KEY MANAGEMENT SYSTEM</h2>
            <div class="nav-links">
                <span data-i18n="accountLabel">Tài khoản:</span> <b class="neon-pink">{{ session['admin'] }}</b>
                <a href="/change-password" data-i18n="linkChangeAccount">[Đổi Tên / Mật Khẩu]</a>
                <a href="/logout" style="color:#ff1744;" data-i18n="linkLogout">[Thoát]</a>
            </div>
            <button class="lang-toggle" onclick="toggleLanguage()" style="top: auto; bottom: 15px; right: 0;">
                <span id="flagIcon">🇻🇳</span>
                <span id="langVI" class="active-lang">VI</span>
                <span class="divider">|</span>
                <span id="langEN">EN</span>
            </button>
        </div>

        {% if msg %}<div class="alert alert-success" data-msg-key="{{ msg }}"></div>{% endif %}
        {% if err %}<div class="alert alert-danger" data-msg-key="{{ err }}"></div>{% endif %}

        <!-- Create Key -->
        <div class="card">
            <h3 class="neon-pink" data-i18n="createKeyTitle">TẠO KEY MỚI</h3>
            <form action="/create-key" method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <label data-i18n="lblCustomKey">Tên Key Custom (Bỏ trống để tự sinh):</label>
                        <input type="text" name="custom_key" data-i18n-ph="phCustomKey" placeholder="Ví dụ: VIP-KEY-2026">
                    </div>
                    <div class="form-group">
                        <label data-i18n="lblUsageLimit">Giới hạn lượt dùng:</label>
                        <input type="number" name="usage_limit" value="10" required min="1">
                    </div>
                    <div class="form-group">
                        <label data-i18n="lblMaxDevices">Số thiết bị (IP tối đa):</label>
                        <input type="number" name="max_devices" value="1" required min="1">
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn btn-glow-green" style="width:100%;" data-i18n="btnCreateKey">TẠO KEY</button>
                    </div>
                </div>
            </form>
        </div>

        <!-- Key List -->
        <div class="card">
            <h3 class="neon-title" data-i18n="keyListTitle">DANH SÁCH KEY</h3>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th data-i18n="thID">ID</th>
                            <th data-i18n="thKeyCode">Mã Key</th>
                            <th data-i18n="thCreatedBy">Người Tạo</th>
                            <th data-i18n="thDevices">Thiết bị</th>
                            <th data-i18n="thUsage">Lượt Dùng</th>
                            <th data-i18n="thStatus">Trạng thái</th>
                            <th data-i18n="thIPs">IP Đã Dùng</th>
                            <th data-i18n="thCreatedAt">Ngày Tạo</th>
                            <th data-i18n="thAction">Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for k in keys %}
                        <tr>
                            <td>{{ k['id'] }}</td>
                            <td>
                                <b class="neon-title">{{ k['key_code'] }}</b>
                                <button class="btn-copy" onclick="copyToClipboard('{{ k['key_code'] }}')" data-i18n="btnCopy">Copy</button>
                            </td>
                            <td><b style="color:#ff007f;">{{ k['created_by'] or 'Hệ thống' }}</b></td>
                            <td>{{ k['used_devices'] }} / {{ k['max_devices'] }}</td>
                            <td><b class="neon-title">{{ k['current_usage'] }} / {{ k['usage_limit'] }}</b></td>
                            <td>
                                {% if k['status'] == 'active' %}
                                    <span style="color:#00e676; font-weight:bold;" data-i18n="statusActive">HOẠT ĐỘNG</span>
                                {% else %}
                                    <span style="color:#ff1744; font-weight:bold;" data-i18n="statusDisabled">VÔ HIỆU</span>
                                {% endif %}
                            </td>
                            <td><small style="color:#aaa;">{{ k['ip_logs'] or 'Chưa có' }}</small></td>
                            <td><small>{{ k['created_at'] }}</small></td>
                            <td>
                                <a href="/delete-key/{{ k['id'] }}" class="delete-link" data-confirm-key="confirmDeleteKey">
                                    <button class="btn btn-danger" data-i18n="btnDelete">XÓA</button>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Admin Management -->
        {% if is_super_admin %}
        <div class="card">
            <h3 class="neon-purple" data-i18n="adminMgmtTitle">QUẢN LÝ ADMIN & TRẠNG THÁI</h3>
            <form action="/create-admin" method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <input type="text" name="username" data-i18n-ph="phNewAdminUser" placeholder="Tên đăng nhập Admin mới" required>
                    </div>
                    <div class="form-group">
                        <input type="password" name="password" data-i18n-ph="phPassword" placeholder="Mật khẩu" required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn btn-glow-pink" style="width:100%;" data-i18n="btnCreateAdmin">TẠO ADMIN</button>
                    </div>
                </div>
            </form>

            <h4 style="margin-top:25px; color:#00f3ff;" data-i18n="adminListTitle">DANH SÁCH ADMIN HỆ THỐNG</h4>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th data-i18n="thID">ID</th>
                            <th data-i18n="thAdminName">Tên Admin</th>
                            <th data-i18n="lblPassword">Mật Khẩu</th>
                            <th data-i18n="thLevel">Cấp độ</th>
                            <th data-i18n="thLoginIP">IP Đăng Nhập</th>
                            <th data-i18n="thStatus">Trạng Thái</th>
                            <th data-i18n="thLastActive">Lần Cuối Hoạt Động</th>
                            <th data-i18n="thAction">Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for a in admins %}
                        <tr>
                            <td>{{ a['id'] }}</td>
                            <td>
                                <b>{{ a['username'] }}</b>
                                {% if a['is_super'] == 0 %}<button class="btn-copy" onclick="copyToClipboard('{{ a['username'] }}')" data-i18n="btnCopy">Copy</button>{% endif %}
                            </td>
                            <td>
                                {% if a['is_super'] == 0 %}
                                    <span>{{ a['plain_password'] or '******' }}</span>
                                    <button class="btn-copy" onclick="copyToClipboard('{{ a['plain_password'] }}')" data-i18n="btnCopy">Copy</button>
                                {% else %}
                                    <i data-i18n="securedRoot">Bảo mật Gốc</i>
                                {% endif %}
                            </td>
                            <td>
                                {% if a['is_super'] == 1 %}
                                    <b style="color:#00e676" data-i18n="levelSuper">SUPER ADMIN</b>
                                {% else %}
                                    <span data-i18n="levelBranch">Admin Chi Nhánh</span>
                                {% endif %}
                            </td>
                            <td><small style="color:#00f3ff; font-weight:bold;">{{ a['last_ip'] or 'Chưa ghi nhận' }}</small></td>
                            <td>
                                {% if a['is_online'] %}
                                    <span class="badge badge-online" data-i18n="badgeOnline">● ONLINE</span>
                                {% else %}
                                    <span class="badge badge-offline" data-i18n="badgeOffline">○ OFFLINE</span>
                                {% endif %}
                            </td>
                            <td><small style="color:#aaa;">{{ a['last_active'] or 'Chưa ghi nhận' }}</small></td>
                            <td>
                                {% if a['is_super'] == 0 %}
                                    <a href="/delete-admin/{{ a['id'] }}" class="delete-link" data-confirm-key="confirmDeleteAdmin">
                                        <button class="btn btn-danger" data-i18n="btnDelete">XÓA</button>
                                    </a>
                                {% else %}
                                    <i style="color:#555;" data-i18n="defaultLabel">Mặc định</i>
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
    """ + I18N_SCRIPT + """
</body>
</html>
"""

# ==================== ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = request.args.get('error')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember')
        client_ip = get_client_ip()
        conn = get_db()
        user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['admin'] = user['username']
            session['is_super'] = user['is_super']
            session.permanent = (remember == 'yes')
            now_str = get_vn_now_str()
            conn.execute("UPDATE admin_users SET last_login = ?, last_active = ?, last_ip = ? WHERE id = ?", 
                         (now_str, now_str, client_ip, user['id']))
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            conn.close()
            error = "login_failed"
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
                if (now - last_act).total_seconds() < 300:
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
    current_username = session['admin']
    if request.method == 'GET':
        return render_template_string(HTML_CHANGE_PASSWORD, current_username=current_username)
    new_username = request.form.get('new_username', '').strip()
    old_password = request.form['old_password']
    new_password = request.form.get('new_password', '').strip()
    conn = get_db()
    user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (current_username,)).fetchone()
    if not user or not check_password_hash(user['password'], old_password):
        conn.close()
        return render_template_string(HTML_CHANGE_PASSWORD, current_username=current_username, err="wrong_password")
    if new_username and new_username != current_username:
        exist_user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (new_username,)).fetchone()
        if exist_user:
            conn.close()
            return render_template_string(HTML_CHANGE_PASSWORD, current_username=current_username, err="username_exists")
    final_password = new_password if new_password else old_password
    new_hashed_pw = generate_password_hash(final_password)
    conn.execute("UPDATE admin_users SET username = ?, password = ?, plain_password = ? WHERE username = ?",
                 (new_username, new_hashed_pw, final_password, current_username))
    conn.commit()
    conn.close()
    session['admin'] = new_username
    return render_template_string(HTML_CHANGE_PASSWORD, current_username=new_username, msg="password_updated")

@app.route('/create-key', methods=['POST'])
@login_required
def create_key():
    custom_key = request.form.get('custom_key', '').strip()
    max_devices = int(request.form.get('max_devices', 1))
    usage_limit = int(request.form.get('usage_limit', 10))
    created_by = session.get('admin', 'Unknown')
    key_code = custom_key if custom_key else "KEY-" + str(uuid.uuid4()).upper()[:12]
    created_at = get_vn_now()
    conn = get_db()
    try:
        conn.execute("INSERT INTO keys (key_code, max_devices, usage_limit, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                     (key_code, max_devices, usage_limit, created_by, created_at.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return redirect(url_for('dashboard', err="key_exists"))
    conn.close()
    return redirect(url_for('dashboard', msg="create_key_success"))

@app.route('/delete-key/<int:key_id>')
@login_required
def delete_key(key_id):
    conn = get_db()
    conn.execute("DELETE FROM keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard', msg="delete_key_success"))

@app.route('/create-admin', methods=['POST'])
@login_required
def create_admin():
    if session.get('is_super') != 1:
        return redirect(url_for('dashboard', err="no_permission"))
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    if not username or not password:
        return redirect(url_for('dashboard', err="fill_all_fields"))
    conn = get_db()
    try:
        hashed_pw = generate_password_hash(password)
        conn.execute("INSERT INTO admin_users (username, password, plain_password, is_super) VALUES (?, ?, ?, 0)",
                     (username, hashed_pw, password))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', msg="create_admin_success"))
    except sqlite3.IntegrityError:
        conn.close()
        return redirect(url_for('dashboard', err="admin_exists"))

@app.route('/delete-admin/<int:admin_id>')
@login_required
def delete_admin(admin_id):
    if session.get('is_super') == 1:
        conn = get_db()
        conn.execute("DELETE FROM admin_users WHERE id = ? AND is_super = 0", (admin_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard', msg="delete_admin_success"))
    return redirect(url_for('dashboard', err="no_permission"))

# ==================== API FOR CLIENT TOOL ====================
@app.route('/api/verify-key', methods=['POST'])
def api_verify_key():
    data = request.get_json() or {}
    key_code = data.get('key', '').strip()
    client_ip = get_client_ip()

    if not key_code:
        return jsonify({"valid": False, "message": "Key không được để trống!"}), 400

    conn = get_db()
    key_data = conn.execute("SELECT * FROM keys WHERE key_code = ?", (key_code,)).fetchone()

    if not key_data:
        conn.close()
        return jsonify({"valid": False, "message": "Key không tồn tại trên hệ thống!"})

    if key_data['current_usage'] >= key_data['usage_limit']:
        conn.close()
        return jsonify({"valid": False, "message": "Key này đã đạt giới hạn số lần sử dụng!"})

    raw_ip_logs = key_data['ip_logs'] or ''
    ip_list = [ip.strip() for ip in raw_ip_logs.split(',') if ip.strip()]

    if client_ip not in ip_list:
        if len(ip_list) >= key_data['max_devices']:
            conn.close()
            return jsonify({"valid": False, "message": f"Key đã đạt giới hạn tối đa ({key_data['max_devices']}) thiết bị!"})
        ip_list.append(client_ip)
        new_ip_logs = ",".join(ip_list)
        new_used_devices = len(ip_list)
    else:
        new_ip_logs = raw_ip_logs
        new_used_devices = key_data['used_devices']

    new_current_usage = key_data['current_usage'] + 1

    conn.execute("UPDATE keys SET ip_logs = ?, used_devices = ?, current_usage = ? WHERE id = ?",
                 (new_ip_logs, new_used_devices, new_current_usage, key_data['id']))
    conn.commit()
    conn.close()

    return jsonify({"valid": True, "message": "Xác thực thành công!", "client_ip": client_ip})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
