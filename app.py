from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
# from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from sqlalchemy import and_

app = Flask(__name__)

# 这一步可以用不先把数据表建立出来，在终端中创建就可以
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leave.db'
app.config['SECRET_KEY'] = 'fshmzk666'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    permission = db.Column(db.Integer)
    level = db.Column(db.Integer)

class leaves(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    lvdate = db.Column(db.String(20))
    reason = db.Column(db.String(512))
    status = db.Column(db.Integer)
    userlevel = db.Column(db.Integer)
    # __tablename__ = 'leaves'
    # __table_args__ = {'autoload': True, 'autoload_with': db.engine}
    # def __repr__(self):
    #     return '<User %r>' % self.username

# 创建数据库表
# with app.app_context():
#     db.create_all()
# @app.before_request
# def reverse_proxy_fix():
#     if 'X-Script-Name' in request.headers:
#         # Rewrite SCRIPT_NAME and PATH_INFO based on X-Script-Name header
#         script_name = request.headers['X-Script-Name']
#         request.environ['SCRIPT_NAME'] = script_name
#         path_info = request.environ['PATH_INFO']
#         if path_info.startswith(script_name):
#             request.environ['PATH_INFO'] = path_info[len(script_name):]

# app.wsgi_app = ProxyFix(app.wsgi_app)

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# # 注册页面
# @app.route('/registerindex')
# def registerindex():
#     return render_template('register.html')

# 注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.json['username']
        password = request.json['password']
        oclevel = request.json['selectedRole']
        # confirm_password = request.form['confirm_password']
        permission_level = 1

        # # Check if the two passwords match
        # if password != confirm_password:
        #     flash('Passwords do not match. Please try again.')
        #     return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Checking if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({"message": "用户名已经注册过了", "success": False})
        else:
            new_user = User(username=username, password_hash=hashed_password, 
                            permission=permission_level, level=oclevel)
            db.session.add(new_user)
            db.session.commit()
            return jsonify({"message": "注册成功", "success": True})
    else:
        return render_template('register.html')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.json['username']
        password = request.json['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # return redirect(url_for('index'))
            return jsonify({"message": "登录成功", "success": True})
        else:
            flash('Invalid username or password')
            return jsonify({"message": "账号密码错误", "success": False})
    else:
        return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/fetch-data', methods=['POST'])
def fetch_data():
    data = request.json
    # print(data)
    days = data['dates']
    
    # Assume you have a database setup with SQLAlchemy and a model called Event
    # Query database for each date and get relevant data
    lvnames = [[i.name for i in leaves.query.filter_by(lvdate=day).all()] for day in days]
    lvreasons = [[i.reason for i in leaves.query.filter_by(lvdate=day).all()] for day in days]
    lvstatuses = [[i.status for i in leaves.query.filter_by(lvdate=day).all()] for day in days]
    lvlevels = [[i.userlevel for i in leaves.query.filter_by(lvdate=day).all()] for day in days]
    # print(lvnames)
    # Format and send the results back to frontend
    # formatted_results = format_results(lvname)  # You'll need to implement this based on your data
    return jsonify({"names": lvnames, "reasons": lvreasons, "statuses": lvstatuses, "userlevel": lvlevels})

@app.route('/submit-data', methods=['POST'])
def submit_data():
    data = request.json
    date = data['date']
    text = data['text']
    level = data['level']
    if current_user != "admin":
        existing_lv = leaves.query.filter_by(name=current_user.username, lvdate=date).first()
        today = datetime.now().strftime("%Y-%m-%d")
        max_lv = leaves.query.filter(and_(leaves.name==current_user.username, leaves.lvdate > today)).all()
        if existing_lv:
            return jsonify({"message": "已请过假了，不用重复提交", "date": date, "name": current_user.username})
        elif len(max_lv) > 4:
            return jsonify({"message": "请假次数超了", "date": date, "name": current_user.username})
        else:
            new_leave = leaves(name=current_user.username, lvdate=date, reason=text, status=1, userlevel=level)
            db.session.add(new_leave)
            db.session.commit()
    else:
        

    return jsonify({"message": "已提交请假申请", "date": date, "name": current_user.username})

@app.route('/del-data', methods=['POST'])
def del_data():
    data = request.json
    name = data['name']
    date = data['date']
    print(date)
    new_del = leaves.query.filter(and_(leaves.name == name, leaves.lvdate == date)).first()
    if new_del:
        db.session.delete(new_del)
        db.session.commit()
    else:
        print("Item not found")

@app.route('/approve', methods=['POST'])
def approve():
    data = request.json
    name = data['name']
    date = data['date']
    new_status = leaves.query.filter(and_(leaves.name==name, leaves.lvdate==date)).first()
    if new_status:
        new_status.status = 2 # 2代表批准了
        db.session.commit()
    else:
        print("Item not found")

@app.route('/reject', methods=['POST'])
def reject():
    data = request.json
    name = data['name']
    date = data['date']
    new_status = leaves.query.filter(and_(leaves.name==name, leaves.lvdate==date)).first()
    if new_status:
        new_status.status = 3 # 3代表拒绝了
        db.session.commit()
    else:
        print("Item not found")


@app.route('/api/usr_info')
@login_required
def user_info():
    # 返回当前用户的信息
    permission = User.query.filter_by(username=current_user.username).first().permission
    userlevel = User.query.filter_by(username=current_user.username).first().level
    # print(permission)
    return jsonify({"username": current_user.username, 
                    "permission": permission,
                    "userlevel": userlevel})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.jinja_env.variable_start_string = '[['
    app.jinja_env.variable_end_string = ']]'
    app.run(host='0.0.0.0', port=8080, debug=True)
