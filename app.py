import os
from functools import wraps

from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

app = Flask(__name__)

# Core configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# MongoDB
MONGO_URI = os.getenv("mongodb+srv://jadhavudaydada827714_db_user:oFGm9OY9Xj2jGleJ@cluster0.lgsejct.mongodb.net/?appName=Cluster0")
mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
mdb = mongo["college"]

# OAuth
oauth = OAuth(app)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

google = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET", "")
apple = None
if APPLE_CLIENT_ID and APPLE_CLIENT_SECRET:
    apple = oauth.register(
        name="apple",
        client_id=APPLE_CLIENT_ID,
        client_secret=APPLE_CLIENT_SECRET,
        access_token_url="https://appleid.apple.com/auth/token",
        authorize_url="https://appleid.apple.com/auth/authorize",
        client_kwargs={"scope": "name email"},
    )

# SQL User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / teacher / cc / hod
    provider = db.Column(db.String(20), default="email")  # email / google / apple

with app.app_context():
    db.create_all()

# ------------------------
# Helpers
# ------------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/")
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                return "Access denied", 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def safe_object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None

def faculty_upsert(name, email, role, provider="email"):
    mdb.faculty.update_one(
        {"email": email},
        {"$set": {"name": name, "email": email, "role": role, "provider": provider}},
        upsert=True,
    )

def get_students():
    students = list(mdb.students.find().sort("roll", 1))
    for s in students:
        s["_id"] = str(s["_id"])
    return students

def layout(title, body):
    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{title}</title>
      <style>
        :root {{
          --bg1: #4facfe;
          --bg2: #00f2fe;
          --card: rgba(255,255,255,.92);
          --text: #0f172a;
          --muted: #64748b;
          --line: #dbe4f0;
          --blue: #2563eb;
          --green: #16a34a;
          --red: #dc2626;
          --dark: #0f172a;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: Arial, Helvetica, sans-serif;
          color: var(--text);
          background: linear-gradient(135deg, var(--bg1), var(--bg2));
          min-height: 100vh;
        }}
        .wrap {{
          min-height: 100vh;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 16px;
        }}
        .card {{
          width: 100%;
          max-width: 980px;
          background: var(--card);
          border-radius: 22px;
          box-shadow: 0 20px 60px rgba(15, 23, 42, .22);
          overflow: hidden;
        }}
        .hero {{
          padding: 28px;
          background: linear-gradient(135deg, #0f172a, #1e3a8a);
          color: white;
        }}
        .hero h1, .hero h2, .hero p {{ margin: 0; }}
        .hero p {{ margin-top: 8px; opacity: .9; line-height: 1.6; }}
        .content {{ padding: 24px; }}
        .grid {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 18px;
        }}
        .panel {{
          background: white;
          border: 1px solid var(--line);
          border-radius: 18px;
          padding: 18px;
        }}
        .row {{ display: grid; gap: 10px; }}
        input, select, button, a.btn {{
          width: 100%;
          padding: 12px 14px;
          border-radius: 12px;
          border: 1px solid var(--line);
          font-size: 15px;
        }}
        input, select {{
          background: #fff;
          outline: none;
        }}
        button, a.btn {{
          cursor: pointer;
          text-decoration: none;
          display: inline-block;
          border: none;
          text-align: center;
          font-weight: 700;
        }}
        .primary {{ background: var(--blue); color: white; }}
        .dark {{ background: var(--dark); color: white; }}
        .green {{ background: var(--green); color: white; }}
        .red {{ background: var(--red); color: white; }}
        .ghost {{ background: white; color: var(--text); border: 1px solid var(--line); }}
        .muted {{ color: var(--muted); }}
        .tabs {{
          display: flex;
          gap: 10px;
          margin-bottom: 14px;
          flex-wrap: wrap;
        }}
        .tabs button {{
          width: auto;
          padding: 10px 16px;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          background: white;
        }}
        th, td {{
          padding: 12px 10px;
          border-bottom: 1px solid #e5eef7;
          text-align: left;
          vertical-align: middle;
        }}
        th {{
          background: #f8fbff;
          font-size: 14px;
        }}
        .actions {{
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }}
        .actions a {{
          width: auto;
          min-width: 92px;
        }}
        .topbar {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          margin-bottom: 18px;
          flex-wrap: wrap;
        }}
        .badge {{
          display: inline-block;
          padding: 7px 12px;
          border-radius: 999px;
          background: #eff6ff;
          color: #1d4ed8;
          font-weight: 700;
          font-size: 13px;
        }}
        .two {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }}
        @media (max-width: 768px) {{
          .grid, .two {{ grid-template-columns: 1fr; }}
          .content {{ padding: 16px; }}
          .hero {{ padding: 20px; }}
          table {{ display: block; overflow-x: auto; white-space: nowrap; }}
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          {body}
        </div>
      </div>
    </body>
    </html>
    """)

# ------------------------
# Login / Signup page
# ------------------------
LOGIN_PAGE = """
<div class="hero">
  <h1>Smart Attendance Login</h1>
  <p>Sign in with email, Google, or Apple. Teachers open attendance only. CC and HOD can add/delete students. Admin has full access.</p>
</div>

<div class="content">
  <div class="tabs">
    <button class="primary" onclick="showTab('login')">Login</button>
    <button class="ghost" onclick="showTab('signup')">Signup</button>
  </div>

  <div class="grid">
    <div class="panel" id="loginTab">
      <h2>Login</h2>
      <p class="muted">Use your college email and password.</p>
      <form class="row" method="post" action="/login">
        <input name="email" type="email" placeholder="Email" required />
        <input name="password" type="password" placeholder="Password" required />
        <button class="primary" type="submit">Login</button>
      </form>

      <div style="height:12px"></div>

      <a class="btn dark" href="/login/google">Continue with Google</a>
      <div style="height:10px"></div>
      <a class="btn ghost" href="/login/apple">Continue with Apple</a>

      <p class="muted" style="margin-top:12px">
        Google and Apple buttons will work only after you add the correct OAuth credentials in environment variables.
      </p>
    </div>

    <div class="panel" id="signupTab" style="display:none;">
      <h2>Signup</h2>
      <p class="muted">Create an account for teachers, CC, HOD, or admin.</p>
      <form class="row" method="post" action="/signup">
        <input name="name" type="text" placeholder="Full Name" required />
        <input name="email" type="email" placeholder="Email" required />
        <input name="password" type="password" placeholder="Password" required />
        <select name="role" required>
          <option value="teacher">Teacher</option>
          <option value="cc">CC</option>
          <option value="hod">HOD</option>
          <option value="admin">Admin</option>
        </select>
        <button class="primary" type="submit">Create Account</button>
      </form>
    </div>
  </div>
</div>

<script>
function showTab(tab) {
  document.getElementById("loginTab").style.display = tab === "login" ? "block" : "none";
  document.getElementById("signupTab").style.display = tab === "signup" ? "block" : "none";
}
</script>
"""

# ------------------------
# Routes
# ------------------------
@app.route("/")
def home():
    return layout("Login", LOGIN_PAGE)

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        session["user"] = user.email
        session["name"] = user.name
        session["role"] = user.role
        return redirect("/dashboard")

    return layout("Login", f"""
    <div class="hero">
      <h1>Smart Attendance Login</h1>
      <p>Invalid email or password.</p>
    </div>
    <div class="content">
      <a class="btn primary" href="/">Go Back</a>
    </div>
    """)

@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "teacher").strip()

    if not name or not email or not password:
        return "Missing data", 400

    if User.query.filter_by(email=email).first():
        return layout("Signup", f"""
        <div class="hero">
          <h1>Smart Attendance Signup</h1>
          <p>This email already exists.</p>
        </div>
        <div class="content">
          <a class="btn primary" href="/">Go Back</a>
        </div>
        """)

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role=role,
        provider="email",
    )
    db.session.add(user)
    db.session.commit()

    faculty_upsert(name, email, role, provider="email")

    session["user"] = user.email
    session["name"] = user.name
    session["role"] = user.role
    return redirect("/dashboard")

@app.route("/login/google")
def google_login():
    if not google:
        return layout("Google Login", """
        <div class="hero">
          <h1>Google Login</h1>
          <p>Google OAuth is not configured yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.</p>
        </div>
        <div class="content">
          <a class="btn primary" href="/">Go Back</a>
        </div>
        """)
    return google.authorize_redirect(url_for("google_callback", _external=True))

@app.route("/auth/google/callback")
def google_callback():
    if not google:
        return redirect("/")

    token = google.authorize_access_token()
    user_info = google.get("userinfo").json()

    email = (user_info.get("email") or "").strip().lower()
    name = (user_info.get("name") or "Google User").strip()

    if not email:
        return "Google login did not return an email.", 400

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, password=generate_password_hash(os.urandom(16).hex()), role="teacher", provider="google")
        db.session.add(user)
        db.session.commit()
        faculty_upsert(name, email, "teacher", provider="google")

    session["user"] = user.email
    session["name"] = user.name
    session["role"] = user.role
    return redirect("/dashboard")

@app.route("/login/apple")
def apple_login():
    if not apple:
        return layout("Apple Login", """
        <div class="hero">
          <h1>Apple Login</h1>
          <p>Apple OAuth is not configured yet. Add APPLE_CLIENT_ID and APPLE_CLIENT_SECRET.</p>
        </div>
        <div class="content">
          <a class="btn primary" href="/">Go Back</a>
        </div>
        """)
    return apple.authorize_redirect(url_for("apple_callback", _external=True))

@app.route("/auth/apple/callback")
def apple_callback():
    if not apple:
        return redirect("/")
    token = apple.authorize_access_token()
    # Apple sign-in requires a full Apple OAuth setup and token decoding.
    # This route is kept safe so it won't crash if credentials are missing.
    return redirect("/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role", "teacher")
    name = session.get("name", "User")
    students = get_students()
    faculty_count = mdb.faculty.count_documents({})

    if role == "teacher":
        body = f"""
        <div class="hero">
          <h1>Teacher Attendance Panel</h1>
          <p>Welcome, {name}. Mark present or absent. Attendance access is available only for teachers.</p>
        </div>
        <div class="content">
          <div class="topbar">
            <div class="badge">Role: Teacher</div>
            <a class="btn dark" href="/logout">Logout</a>
          </div>

          <div class="panel">
            <table>
              <thead>
                <tr>
                  <th>Roll</th>
                  <th>Name</th>
                  <th>Action</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {''.join(f'''
                <tr>
                  <td>{s.get("roll", "")}</td>
                  <td>{s.get("name", "")}</td>
                  <td>
                    <div class="actions">
                      <a class="btn green" href="/present/{s["_id"]}">Present</a>
                      <a class="btn red" href="/absent/{s["_id"]}">Absent</a>
                    </div>
                  </td>
                  <td>{s.get("status", "-")}</td>
                </tr>
                ''' for s in students) if students else '<tr><td colspan="4" class="muted">No students added yet.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
        """
        return layout("Teacher Dashboard", body)

    # Admin / CC / HOD dashboard
    add_form = ""
    if role in ["admin", "cc", "hod"]:
        add_form = """
        <div class="panel">
          <h2>Add Student</h2>
          <form class="row" method="post" action="/add">
            <input name="roll" type="text" placeholder="Roll No" required />
            <input name="name" type="text" placeholder="Student Name" required />
            <button class="primary" type="submit">Add Student</button>
          </form>
        </div>
        """

    delete_col = "<th>Delete</th>" if role in ["admin", "cc", "hod"] else ""

    rows = ""
    for s in students:
        delete_td = ""
        if role in ["admin", "cc", "hod"]:
            delete_td = f'<td><a class="btn red" style="width:auto;min-width:92px;" href="/delete/{s["_id"]}">Delete</a></td>'

        rows += f"""
        <tr>
          <td>{s.get("roll", "")}</td>
          <td>{s.get("name", "")}</td>
          <td>
            <div class="actions">
              <a class="btn green" href="/present/{s["_id"]}">Present</a>
              <a class="btn red" href="/absent/{s["_id"]}">Absent</a>
            </div>
          </td>
          <td>{s.get("status", "-")}</td>
          {delete_td}
        </tr>
        """

    body = f"""
    <div class="hero">
      <h1>{role.upper()} Dashboard</h1>
      <p>Welcome, {name}. Faculty stored in MongoDB: {faculty_count}. Students are managed here with role-based access.</p>
    </div>

    <div class="content">
      <div class="topbar">
        <div class="badge">Role: {role.upper()}</div>
        <a class="btn dark" href="/logout">Logout</a>
      </div>

      <div class="two">
        {add_form}
        <div class="panel">
          <h2>Faculty Records</h2>
          <p class="muted">Faculty members are stored in MongoDB collection <b>faculty</b>.</p>
          <div class="badge">Total Faculty: {faculty_count}</div>
        </div>
      </div>

      <div style="height:16px"></div>

      <div class="panel">
        <h2>Student Attendance</h2>
        <table>
          <thead>
            <tr>
              <th>Roll</th>
              <th>Name</th>
              <th>Action</th>
              <th>Status</th>
              {delete_col}
            </tr>
          </thead>
          <tbody>
            {rows if rows else f'<tr><td colspan="{5 if role in ["admin","cc","hod"] else 4}" class="muted">No students added yet.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
    """
    return layout("Dashboard", body)

@app.route("/add", methods=["POST"])
@role_required("admin", "cc", "hod")
def add():
    roll = request.form.get("roll", "").strip()
    name = request.form.get("name", "").strip()

    if not roll or not name:
        return "Missing student data", 400

    mdb.students.insert_one({
        "roll": roll,
        "name": name,
        "status": "-"
    })
    return redirect("/dashboard")

@app.route("/delete/<student_id>")
@role_required("admin", "cc", "hod")
def delete(student_id):
    oid = safe_object_id(student_id)
    if not oid:
        return "Invalid student id", 400

    mdb.students.delete_one({"_id": oid})
    return redirect("/dashboard")

@app.route("/present/<student_id>")
@login_required
def present(student_id):
    oid = safe_object_id(student_id)
    if not oid:
        return "Invalid student id", 400

    mdb.students.update_one({"_id": oid}, {"$set": {"status": "Present"}})
    return redirect("/dashboard")

@app.route("/absent/<student_id>")
@login_required
def absent(student_id):
    oid = safe_object_id(student_id)
    if not oid:
        return "Invalid student id", 400

    mdb.students.update_one({"_id": oid}, {"$set": {"status": "Absent"}})
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.errorhandler(404)
def page_not_found(_):
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
