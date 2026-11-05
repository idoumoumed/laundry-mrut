from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import sqlite3
import datetime
import os
import hashlib

app = Flask(__name__)
app.secret_key = 'el_mehjoub_laundry_super_secret_cyber_security_key_2026'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

USERNAME = "idoumou el mehjoub"
PASSWORD_HASH = hashlib.sha256("Aa33273969".encode()).hexdigest()

MAURITANIA_STATES = [
    "نواكشوط الغربية", "نواكشوط الشمالية", "نواكشوط الجنوبية",
    "داخلت نواذيبو", "ترارزة (روصو)", "لبراكنة (ألاك)",
    "كوركول (كيهيدي)", "كيديماغا (سيلبابي)", "لعصابة (كيفة)",
    "الحوض الغربي (عيون العتروس)", "الحوض الشرقي (النعمة)",
    "تكانت (تجكجة)", "آدرار (أطار)", "إنشيري (أكجوجت)", "تيرس زمور (زويرات)"
]

def init_db():
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT, item_type TEXT, quantity INTEGER, 
            price_per_item REAL, status TEXT, date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, phone TEXT, birth_date TEXT, birthplace TEXT,
            salary REAL, attendance TEXT, photo TEXT, service_experience TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fleet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT, driver_name TEXT, destination_state TEXT, load_details TEXT, status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, amount REAL, description TEXT, date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مغسلة خالك - تسجيل الدخول الآمن</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #1a1a1a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; font-family: 'Segoe UI', Tahoma, sans-serif; }
        .login-card { background: #2b2b2b; border: 2px solid #ffc107; border-radius: 15px; padding: 40px; width: 100%; max-width: 420px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .btn-warning { background-color: #ffc107; font-weight: bold; }
    </style>
</head>
<body>
    <div class="login-card text-center">
        <h3 class="text-warning mb-4"><i class="fa-solid fa-shield-halved me-2"></i> بوابة نظام مؤسسة خالك</h3>
        <p class="text-muted mb-4 small">نظام إدارة مغسلة خالك الحصري والمحمي</p>
        {% if error %}
            <div class="alert alert-danger py-2 mb-3">{{ error }}</div>
        {% endif %}
        <form action="/login" method="POST">
            <div class="mb-3 text-start">
                <label class="form-label text-warning small">اسم المستخدم المؤسسي:</label>
                <input type="text" name="username" class="form-control bg-dark text-white border-secondary" placeholder="ادخل اسم المستخدم" required>
            </div>
            <div class="mb-4 text-start">
                <label class="form-label text-warning small">كلمة المرور المشفرة:</label>
                <input type="password" name="password" class="form-control bg-dark text-white border-secondary" placeholder="ادخل كلمة المرور" required>
            </div>
            <button type="submit" class="btn btn-warning w-100 py-2 fs-5">دخول للنظام 🔒</button>
        </form>
    </div>
</body>
</html>
'''

BASE_HTML = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مغسلة خالك - النظام الذكي (موريتانيا)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root { --main-yellow: #ffc107; --dark-bg: #212529; }
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, sans-serif; min-height: 100vh; display: flex; flex-direction: column; }
        .wrapper { display: flex; width: 100%; min-height: 100vh; }
        .sidebar { background: var(--dark-bg); width: 260px; color: white; border-left: 5px solid var(--main-yellow); flex-shrink: 0; }
        .sidebar .nav-link { color: #adb5bd; padding: 12px 15px; font-weight: 600; border-radius: 6px; margin-bottom: 6px; }
        .sidebar .nav-link:hover, .sidebar .nav-link.active { background: var(--main-yellow); color: #000; }
        .main-content { flex-grow: 1; padding: 30px; background-color: #f4f6f9; }
        .btn-warning { background-color: var(--main-yellow); border-color: var(--main-yellow); font-weight: bold; color: #000; }
        .card-custom { border-radius: 12px; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.05); background: white; margin-bottom: 20px; }
        #map { height: 500px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; }
        .worker-img { width: 85px; height: 85px; object-fit: cover; border-radius: 50%; border: 3px solid var(--main-yellow); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="sidebar p-3 d-flex flex-column">
            <h4 class="text-warning text-center mb-1"><i class="fa-solid fa-soap"></i> مغسلة خالك</h4>
            <div class="text-center text-muted small mb-4">مؤسسة idoumou el mehjoub</div>
            <nav class="nav nav-pills flex-column mb-auto">
                <a href="/" class="nav-link {% if page == 'dashboard' %}active{% endif %}">
                    <i class="fa-solid fa-chart-pie me-2"></i> لوحة التحكم والتحليل
                </a>
                <a href="/orders_page" class="nav-link {% if page == 'orders' %}active{% endif %}">
                    <i class="fa-solid fa-list-check me-2"></i> إدارة الطلبات
                </a>
                <a href="/workers_page" class="nav-link {% if page == 'workers' %}active{% endif %}">
                    <i class="fa-solid fa-users-gear me-2"></i> شؤون العمال والصور
                </a>
                <a href="/fleet_page" class="nav-link {% if page == 'fleet' %}active{% endif %}">
                    <i class="fa-solid fa-truck-fast me-2"></i> الأسطول والولايات (GPS)
                </a>
                <a href="/finance_page" class="nav-link {% if page == 'finance' %}active{% endif %}">
                    <i class="fa-solid fa-wallet me-2"></i> الميزانية والبنزين والرواتب
                </a>
            </nav>
            <div class="mt-auto">
                <div class="text-muted small text-center mb-2">العملة: أوقية موريتانية (MRU)</div>
                <a href="/logout" class="btn btn-outline-danger w-100 btn-sm"><i class="fa-solid fa-right-from-bracket me-1"></i> خروج آمن</a>
            </div>
        </div>
        <div class="main-content">
            {% block content %}{% endblock %}
        </div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
'''

DASHBOARD_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <h3 class="mb-4 fw-bold"><i class="fa-solid fa-chart-line text-warning me-2"></i> لوحة التحكم والتحليل التشغيلي (موريتانيا)</h3>
    <div class="alert alert-dark bg-dark text-white p-4 mb-4 rounded-3 shadow">
        <h4 class="text-warning"><i class="fa-solid fa-brain me-2"></i> التحليل المالي الذكي (AI Financial Engine)</h4>
        <p class="mb-0 fs-5">{{ ai_financial_advice }}</p>
    </div>
    <div class="row g-3 mb-4">
        <div class="col-md-3">
            <div class="card card-custom p-3 border-start border-warning border-4">
                <div class="text-muted">إجمالي الإيرادات</div>
                <div class="fs-3 fw-bold text-dark">{{ "%.2f"|format(total_revenue) }} أوقية <small class="text-muted fs-6">(MRU)</small></div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card card-custom p-3 border-start border-danger border-4">
                <div class="text-muted">إجمالي المصاريف والبنزين</div>
                <div class="fs-3 fw-bold text-danger">{{ "%.2f"|format(total_expenses) }} أوقية <small class="text-muted fs-6">(MRU)</small></div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card card-custom p-3 border-start border-success border-4">
                <div class="text-muted">صافي الأرباح الحقيقية</div>
                <div class="fs-3 fw-bold text-success">{{ "%.2f"|format(net_profit) }} أوقية <small class="text-muted fs-6">(MRU)</small></div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card card-custom p-3 border-start border-info border-4">
                <div class="text-muted">العمال والأسطول</div>
                <div class="fs-3 fw-bold text-info">{{ total_workers }} عمال / {{ total_buses }} باصات</div>
            </div>
        </div>
    </div>
''')

ORDERS_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <h3 class="mb-4 fw-bold"><i class="fa-solid fa-boxes-stacked text-warning me-2"></i> إدارة طلبات المغسلة (بالأوقية الموريتانية)</h3>
    <div class="card card-custom p-4 mb-4">
        <h5 class="mb-3">إضافة طلب جديد</h5>
        <form action="/add_order" method="POST" class="row g-3">
            <div class="col-md-3"><input type="text" name="customer_name" class="form-control" placeholder="اسم العميل" required></div>
            <div class="col-md-2">
                <select name="item_type" class="form-select">
                    <option value="سجاد كبير">سجاد كبير</option>
                    <option value="سجاد متوسط">سجاد متوسط</option>
                    <option value="بطانية">بطانية</option>
                </select>
            </div>
            <div class="col-md-2"><input type="number" name="quantity" class="form-control" value="1" min="1" required></div>
            <div class="col-md-2"><input type="number" step="100" name="price_per_item" class="form-control" placeholder="السعر بالأوقية" required></div>
            <div class="col-md-2">
                <select name="status" class="form-select">
                    <option value="قيد التنفيذ">قيد التنفيذ</option>
                    <option value="جاهز">جاهز</option>
                </select>
            </div>
            <div class="col-md-1"><button type="submit" class="btn btn-warning w-100">حفظ</button></div>
        </form>
    </div>
    <div class="table-responsive bg-white p-3 card-custom">
        <table class="table table-hover align-middle">
            <thead class="table-dark">
                <tr><th>ID</th><th>العميل</th><th>القطعة</th><th>العدد</th><th>المبلغ (أوقية موريتانية)</th><th>الحالة</th><th>التاريخ</th><th>إجراء</th></tr>
            </thead>
            <tbody>
                {% for o in orders %}
                <tr>
                    <td class="fw-bold text-warning">#{{ o[0] }}</td>
                    <td>{{ o[1] }}</td><td>{{ o[2] }}</td><td>{{ o[3] }}</td>
                    <td class="fw-bold text-success">{{ o[3] * o[4] }} أوقية (MRU)</td>
                    <td><span class="badge bg-warning text-dark">{{ o[5] }}</span></td>
                    <td class="text-muted small">{{ o[6] }}</td>
                    <td><a href="/delete_order/{{ o[0] }}" class="btn btn-sm btn-outline-danger"><i class="fa-solid fa-trash"></i></a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
''')

WORKERS_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <h3 class="mb-4 fw-bold"><i class="fa-solid fa-users text-warning me-2"></i> سجل العمال (الصور الحقيقية وولايات الميلاد)</h3>
    <div class="card card-custom p-4 mb-4">
        <h5 class="mb-3 text-warning"><i class="fa-solid fa-user-plus me-2"></i> إضافة عامل جديد (مع رفع صورته الحقيقية وتجربة الخدمة)</h5>
        <form action="/add_worker" method="POST" enctype="multipart/form-data" class="row g-3">
            <div class="col-md-3"><input type="text" name="name" class="form-control" placeholder="اسم العامل الثلاثي" required></div>
            <div class="col-md-2"><input type="text" name="phone" class="form-control" placeholder="رقم الهاتف" required></div>
            <div class="col-md-2"><input type="date" name="birth_date" class="form-control" required></div>
            <div class="col-md-3">
                <select name="birthplace" class="form-select" required>
                    <option value="" disabled selected>اختر ولاية الميلاد الموريتانية...</option>
                    {% for state in mauritania_states %}
                    <option value="{{ state }}">{{ state }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-2"><input type="number" step="1000" name="salary" class="form-control" placeholder="الراتب بالأوقية" required></div>
            <div class="col-md-4">
                <label class="form-label small text-muted fw-bold">اختر صورة العامل الحقيقية من جهازك:</label>
                <input type="file" name="photo_file" class="form-control" accept="image/*" required>
            </div>
            <div class="col-md-3">
                <label class="form-label small text-muted fw-bold">تجربة الخدمة / كفاءة الميدان:</label>
                <input type="text" name="service_experience" class="form-control" placeholder="مثال: خبرة 3 سنوات في غسيل السجاد">
            </div>
            <div class="col-md-2">
                <label class="form-label small text-muted fw-bold">حالة الحضور اليوم:</label>
                <select name="attendance" class="form-select">
                    <option value="حاضر">حاضر اليوم</option>
                    <option value="غائب">غائب اليوم</option>
                </select>
            </div>
            <div class="col-md-3 d-flex align-items-end">
                <button type="submit" class="btn btn-warning w-100 fw-bold py-2">حفظ العامل 💾</button>
            </div>
        </form>
    </div>
    <div class="row g-4">
        {% for w in workers %}
        <div class="col-md-4">
            <div class="card card-custom p-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge bg-dark text-warning">ID: #{{ w[0] }}</span>
                </div>
                <div class="d-flex align-items-center mb-3">
                    <img src="{{ url_for('static', filename='uploads/' + w[7]) }}" class="worker-img me-3" onerror="this.src='https://via.placeholder.com/85'">
                    <div>
                        <h5 class="mb-0 fw-bold">{{ w[1] }}</h5>
                        <small class="text-muted">الهاتف: {{ w[2] }}</small>
                    </div>
                </div>
                <p class="mb-1"><strong>مواليد:</strong> {{ w[3] }} | <strong>الولاية:</strong> {{ w[4] }}</p>
                <p class="mb-1"><strong>الراتب:</strong> {{ w[5] }} أوقية (MRU)</p>
                <p class="mb-1"><strong>تجربة الخدمة:</strong> <span class="text-primary fw-bold">{{ w[8] if w[8] else 'خدمة ميدانية قياسية' }}</span></p>
                <p class="mb-2"><strong>الحالة:</strong> <span class="badge {% if w[6]=='حاضر' %}bg-success{% else %}bg-danger{% endif %}">{{ w[6] }}</span></p>
                <a href="/delete_worker/{{ w[0] }}" class="btn btn-sm btn-outline-danger w-100"><i class="fa-solid fa-trash me-1"></i> حذف العامل</a>
            </div>
        </div>
        {% endfor %}
    </div>
''')

FLEET_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <h3 class="mb-4 fw-bold"><i class="fa-solid fa-truck text-warning me-2"></i> أسطول الباصات وحمولاتها ووجهات ولايات موريتانيا</h3>
    <div class="card card-custom p-4 mb-4">
        <h5 class="mb-3 text-warning"><i class="fa-solid fa-plus-circle me-2"></i> إضافة سيارة أو باص جديد (الرقم، السائق، ولاية الوجهة، والحمولة)</h5>
        <form action="/add_bus" method="POST" class="row g-3">
            <div class="col-md-3"><input type="text" name="bus_number" class="form-control" placeholder="رقم الباص / اللوحة" required></div>
            <div class="col-md-3"><input type="text" name="driver_name" class="form-control" placeholder="اسم سائق الباص" required></div>
            <div class="col-md-3">
                <select name="destination_state" class="form-select" required>
                    <option value="" disabled selected>اختر ولاية الوجهة للباص...</option>
                    {% for state in mauritania_states %}
                    <option value="{{ state }}">{{ state }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-3"><input type="text" name="load_details" class="form-control" placeholder="حمولة الباص (مثال: سجاد وبطانيات)" required></div>
            <div class="col-12"><button type="submit" class="btn btn-warning w-100 fw-bold">نشر الباص في الأسطول والخريطة 🚚</button></div>
        </form>
    </div>
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card card-custom p-3 bg-dark text-white">
                <h5 class="text-warning mb-3"><i class="fa-solid fa-list-numeric me-2"></i> قائمة الباصات وجهاتها</h5>
                <div class="list-group mb-3">
                    {% for b in fleet %}
                    <div class="list-group-item bg-secondary text-white border-0 mb-2 rounded">
                        <div class="fw-bold">🚐 باص #{{ b[0] }} - لوحة: {{ b[1] }}</div>
                        <small>السائق: {{ b[2] }} | الوجهة: <strong>{{ b[3] }}</strong></small><br>
                        <small class="text-warning">الحمولة: {{ b[4] }}</small>
                    </div>
                    {% else %}
                    <div class="text-muted small text-center py-2">لا توجد باصات مسجلة بعد.</div>
                    {% endfor %}
                </div>
            </div>
        </div>
        <div class="col-md-8">
            <div id="map"></div>
        </div>
    </div>
''').replace('{% block scripts %}{% endblock %}', '''
    <script>
        var map = L.map('map').setView([18.0735, -15.9582], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var shopMarker = L.marker([18.0735, -15.9582]).addTo(map).bindPopup('مقر مغسلة خالك الرئيسي (نواكشوط)').openPopup();
    </script>
''')

FINANCE_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <h3 class="mb-4 fw-bold"><i class="fa-solid fa-coins text-warning me-2"></i> الميزانية، تكاليف البنزين والرواتب (أوقية موريتانية)</h3>
    <div class="row g-4 mb-4">
        <div class="col-md-6">
            <div class="card card-custom p-4">
                <h5 class="mb-3 text-danger"><i class="fa-solid fa-file-invoice-dollar me-2"></i> تسجيل مصروف أو تكلفة بنزين الباصات</h5>
                <form action="/add_expense" method="POST" class="row g-3">
                    <div class="col-md-6">
                        <select name="category" class="form-select">
                            <option value="بنزين ووقود الباصات">⛽ بنزين ووقود الباصات</option>
                            <option value="كهرباء المغسلة">💡 كهرباء المغسلة</option>
                            <option value="صيانة ماكينات">⚙️ صيانة ماكينات الغسيل</option>
                            <option value="مواد تنظيف">🧼 مساحيق ومواد تنظيف</option>
                            <option value="أخرى">📌 مصاريف أخرى</option>
                        </select>
                    </div>
                    <div class="col-md-6"><input type="number" step="100" name="amount" class="form-control" placeholder="المبلغ بالأوقية (MRU)" required></div>
                    <div class="col-12"><input type="text" name="description" class="form-control" placeholder="تفاصيل التكلفة (مثال: تعبئة بنزين باص رقم 1)"></div>
                    <div class="col-12"><button type="submit" class="btn btn-danger w-100 fw-bold">حفظ المصروف / البنزين</button></div>
                </form>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card card-custom p-4 bg-dark text-white">
                <h5 class="text-warning mb-3"><i class="fa-solid fa-robot me-2"></i> الحساب الآلي لنهاية الشهر</h5>
                <p class="text-muted">خصم رواتب جميع العمال تلقائياً وإضافتها لسجل المصاريف والبنزين بضغطة زر.</p>
                <a href="/process_monthly_salaries" class="btn btn-warning w-100 py-3 fw-bold">
                    <i class="fa-solid fa-calculator me-2"></i> تنفيذ خصم الرواتب الآلي (أوقية) 🤖
                </a>
            </div>
        </div>
    </div>
    <div class="table-responsive bg-white p-3 card-custom">
        <h5 class="mb-3">سجل المصاريف والتكاليف والبنزين</h5>
        <table class="table table-hover align-middle">
            <thead class="table-dark">
                <tr><th>ID</th><th>البند</th><th>المبلغ (أوقية موريتانية)</th><th>التفاصيل</th><th>التاريخ</th><th>إجراء</th></tr>
            </thead>
            <tbody>
                {% for e in expenses %}
                <tr>
                    <td class="fw-bold text-danger">#{{ e[0] }}</td>
                    <td><span class="badge bg-danger">{{ e[1] }}</span></td>
                    <td class="fw-bold text-danger">{{ e[2] }} أوقية (MRU)</td>
                    <td>{{ e[3] }}</td><td class="text-muted small">{{ e[4] }}</td>
                    <td><a href="/delete_expense/{{ e[0] }}" class="btn btn-sm btn-outline-danger"><i class="fa-solid fa-trash"></i></a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        
        if user == USERNAME and pwd_hash == PASSWORD_HASH:
            session['logged_in'] = True
            session['username'] = user
            return redirect(url_for('home'))
        else:
            return render_template_string(LOGIN_HTML, error="اسم المستخدم أو كلمة المرور غير صحيحة!")
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def check_auth():
    return session.get('logged_in', False)

@app.route('/')
def home():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(quantity * price_per_item) FROM orders')
    rev_res = cursor.fetchone()[0]
    total_revenue = rev_res if rev_res else 0.0

    cursor.execute('SELECT SUM(amount) FROM expenses')
    exp_res = cursor.fetchone()[0]
    total_expenses = exp_res if exp_res else 0.0

    cursor.execute('SELECT COUNT(*) FROM workers')
    total_workers = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM fleet')
    total_buses = cursor.fetchone()[0]
    conn.close()

    net_profit = total_revenue - total_expenses
    ai_advice = f"تحليل الذكاء الاصطناعي المالي: إجمالي الإيرادات {total_revenue} أوقية موريتانية (MRU)، المصاريف وبنزين الباصات {total_expenses} أوقية، وصافي الربح {net_profit} أوقية. الأداء التشغيلي محمي ومستقر."

    return render_template_string(DASHBOARD_HTML, page='dashboard', total_revenue=total_revenue, 
                                 total_expenses=total_expenses, net_profit=net_profit, 
                                 total_workers=total_workers, total_buses=total_buses, ai_financial_advice=ai_advice)

@app.route('/orders_page')
def orders_page():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders ORDER BY id DESC')
    orders = cursor.fetchall()
    conn.close()
    return render_template_string(ORDERS_HTML, page='orders', orders=orders)

@app.route('/add_order', methods=['POST'])
def add_order():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (customer_name, item_type, quantity, price_per_item, status, date) VALUES (?, ?, ?, ?, ?, ?)',
                   (request.form['customer_name'], request.form['item_type'], int(request.form['quantity']),
                    float(request.form['price_per_item']), request.form['status'], datetime.datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    return redirect(url_for('orders_page'))

@app.route('/delete_order/<int:id>')
def delete_order(id):
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM orders WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('orders_page'))

@app.route('/workers_page')
def workers_page():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM workers ORDER BY id DESC')
    workers = cursor.fetchall()
    conn.close()
    return render_template_string(WORKERS_HTML, page='workers', workers=workers, mauritania_states=MAURITANIA_STATES)

@app.route('/add_worker', methods=['POST'])
def add_worker():
    if not check_auth(): return redirect(url_for('login'))
    name = request.form['name']
    phone = request.form['phone']
    birth_date = request.form['birth_date']
    birthplace = request.form['birthplace']
    salary = float(request.form['salary'])
    attendance = request.form['attendance']
    service_experience = request.form.get('service_experience', '')
    
    photo_file = request.files.get('photo_file')
    if photo_file and photo_file.filename != '':
        photo_filename = photo_file.filename
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
        photo_file.save(photo_path)
    else:
        photo_filename = "default.png"

    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO workers (name, phone, birth_date, birthplace, salary, attendance, photo, service_experience) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                   (name, phone, birth_date, birthplace, salary, attendance, photo_filename, service_experience))
    conn.commit()
    conn.close()
    return redirect(url_for('workers_page'))

@app.route('/delete_worker/<int:id>')
def delete_worker(id):
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM workers WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('workers_page'))

@app.route('/fleet_page')
def fleet_page():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM fleet ORDER BY id DESC')
    fleet = cursor.fetchall()
    conn.close()
    return render_template_string(FLEET_HTML, page='fleet', fleet=fleet, mauritania_states=MAURITANIA_STATES)

@app.route('/add_bus', methods=['POST'])
def add_bus():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO fleet (bus_number, driver_name, destination_state, load_details, status) VALUES (?, ?, ?, ?, ?)',
                   (request.form['bus_number'], request.form['driver_name'], request.form['destination_state'], 
                    request.form['load_details'], 'متوجه إلى الولاية'))
    conn.commit()
    conn.close()
    return redirect(url_for('fleet_page'))

@app.route('/finance_page')
def finance_page():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM expenses ORDER BY id DESC')
    expenses = cursor.fetchall()
    conn.close()
    return render_template_string(FINANCE_HTML, page='finance', expenses=expenses)

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO expenses (category, amount, description, date) VALUES (?, ?, ?, ?)',
                   (request.form['category'], float(request.form['amount']), 
                    request.form['description'], datetime.datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    return redirect(url_for('finance_page'))

@app.route('/delete_expense/<int:id>')
def delete_expense(id):
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('finance_page'))

@app.route('/process_monthly_salaries')
def process_monthly_salaries():
    if not check_auth(): return redirect(url_for('login'))
    conn = sqlite3.connect('laundry_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(salary) FROM workers')
    res = cursor.fetchone()[0]
    total_salaries = res if res else 0.0
    
    if total_salaries > 0:
        cursor.execute('INSERT INTO expenses (category, amount, description, date) VALUES (?, ?, ?, ?)',
                       ('رواتب العمال', total_salaries, 'خصم رواتب الشهر تلقائياً عبر الذكاء الاصطناعي (أوقية موريتانية)', datetime.datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
    conn.close()
    return redirect(url_for('finance_page'))

if __name__ == '__main__':
    app.run(debug=True)
