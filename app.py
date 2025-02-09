from datetime import datetime
import random

from flask_mail import Mail, Message
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy.testing.suite.test_reflection import users
from werkzeug.exceptions import abort
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.fields.simple import HiddenField
from wtforms.validators import DataRequired, Email, EqualTo
from extensions import db

from flask_migrate import Migrate, migrate

from flask_wtf.file import FileField, FileAllowed
import os
from werkzeug.utils import secure_filename
from flask_wtf.file import FileField, MultipleFileField
import os

from dotenv import load_dotenv
app = Flask(__name__)
migrate=Migrate(app,db)
load_dotenv('smtp.env')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AVATAR_UPLOAD'] = os.path.join(UPLOAD_FOLDER, 'avatars')
mail = Mail()
serializer = Serializer(app.config['SECRET_KEY'], salt='email-verify')
if not os.path.exists(app.config['AVATAR_UPLOAD']):
    os.makedirs(app.config['AVATAR_UPLOAD'])
# 初始化 db
db.init_app(app)
mail.init_app(app)

# 初始化 Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'
class ProfileForm(FlaskForm):
    avatar = FileField('上传头像', validators=[
        FileAllowed(['jpg', 'png', 'gif'], '仅支持 JPG/PNG/GIF 格式')
    ])
    submit = SubmitField('更新资料')
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# 导入模型
from models import User, Category, Post, Reply, Notification, VerificationCode


# 表单定义
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('注册')
    verification_code = StringField('验证码', validators=[DataRequired()])
def generate_verification_code(email):
    code = str(random.randint(100000, 999999))
    existing = VerificationCode.query.filter_by(email=email).first()
    if existing:
        existing.code = code
        existing.created_at = datetime.utcnow()
    else:
        db.session.add(VerificationCode(email=email, code=code))
    db.session.commit()
    return code
def send_verification_email(email, code):
    msg = Message('邮箱验证码', sender='3259379048@qq.com', recipients=[email])
    msg.body = f'来自Eros Forum 您的验证码是：{code}，10分钟内有效'
    mail.send(msg)

class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

from wtforms import SelectField

class PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired()])
    content = TextAreaField('内容', validators=[DataRequired()])
    # 新增分类选择字段
    category = SelectField('选择分类', coerce=int, validators=[DataRequired()])
    submit = SubmitField('发布')

    class PostForm(FlaskForm):
        content = TextAreaField('内容', render_kw={
            'rows': 10,
            'placeholder': '使用 Markdown 格式编写...'
        })
    files = MultipleFileField('上传附件', validators=[
        FileAllowed(['jpg', 'png', 'pdf', 'doc', 'docx'], '允许格式：图片/PDF/Word')
    ])
from flask import send_from_directory

@app.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(
        os.path.join(app.config['UPLOAD_FOLDER'], 'post_files'),
        filename,
        as_attachment=True
    )
class ReplyForm(FlaskForm):
    content = TextAreaField('回复内容', validators=[DataRequired()])
    submit = SubmitField('提交')

# 路由
@app.route('/')
def index():
    categories = Category.query.all()
    return render_template('index.html', categories=categories)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()

    if form.validate_on_submit():
        # 处理头像上传
        if form.avatar.data:
            file = form.avatar.data
            filename = f"user_{current_user.id}_{secure_filename(file.filename)}"
            upload_path = os.path.join(
                app.root_path, 'static/uploads/avatars', filename
            )
            file.save(upload_path)
            current_user.avatar_path = filename

        db.session.commit()
        flash('资料已更新', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', form=form)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        code_record = VerificationCode.query.filter_by(
            email=form.email.data,
            code=form.verification_code.data
        ).first()
        if not code_record or (datetime.utcnow() - code_record.created_at).seconds > 600:
            flash('验证码错误或已过期', 'danger')
            return redirect(url_for('register'))
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('注册成功！请登录。', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('邮箱或密码错误！', 'danger')
    return render_template('login.html', form=form)


@app.route('/send_code', methods=['POST'])
def send_code():
    email = request.json.get('email')
    if not email:
        return jsonify({'success': False})

    code = generate_verification_code(email)
    try:
        send_verification_email(email, code)
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录。', 'success')
    return redirect(url_for('index'))

@app.route('/category/<int:category_id>')
def category(category_id):
    category = Category.query.get_or_404(category_id)
    posts = category.posts
    return render_template('category.html', category=category, posts=posts)

# @app.route('/post/<int:post_id>', methods=['GET', 'POST'])
# def post(post_id):
#     post = Post.query.get_or_404(post_id)
#     form = ReplyForm()
#     if form.validate_on_submit():
#         reply = Reply(content=form.content.data, post=post, user=current_user)
#         db.session.add(reply)
#         db.session.commit()
#         flash('回复成功！', 'success')
#         return redirect(url_for('post', post_id=post.id))
#     print(post.user_id)
#     print(User.query.get_or_404(post.user_id).username)
#     return render_template('post.html', post=post, form=form,post_user=User.query.get_or_404(post.user_id).username)


class ReplyForm(FlaskForm):
    content = TextAreaField('回复内容', validators=[DataRequired()])
    # 新增父回复ID字段（用于嵌套回复）
    parent_reply_id = HiddenField('父回复ID')  # 新增
    submit = SubmitField('提交')
# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    file = request.files.get('file')
    if file and allowed_file(file.filename):
        filename = f"post_{current_user.id}_{secure_filename(file.filename)}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'post_images', filename)
        file.save(save_path)
        return jsonify({
            'success': True,
            'file_path': url_for('static', filename=f'uploads/post_images/{filename}')
        })
    return jsonify({'success': False})

# @app.route('/post/<int:post_id>', methods=['GET', 'POST'])
# def post(post_id):
#     post = Post.query.get_or_404(post_id)
#     form = ReplyForm()
#
#     if form.validate_on_submit():
#         reply = Reply(
#             content=form.content.data,
#             post=post,
#             user=current_user,
#             parent_reply_id=form.parent_reply_id.data or None  # 处理父回复
#         )
#         db.session.add(reply)
#         db.session.commit()
#         flash('回复成功！', 'success')
#         return redirect(url_for('post', post_id=post.id))
#
#     # 获取所有顶级回复（没有父回复的回复）
#     top_level_replies = [r for r in post.replies if r.parent_reply_id is None]
#     return render_template('post.html', post=post, form=form, replies=top_level_replies,post_user=User.query.get_or_404(post.user_id).username)
#
@app.route('/notifications')
@login_required
def notifications():
    # 获取所有通知并按时间排序
    notifications = current_user.notifications.order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/mark_as_read/<int:notification_id>')
@login_required
def mark_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user != current_user:
        abort(403)
    notification.is_read = True
    db.session.commit()
    return redirect(url_for('post', post_id=notification.reply.post_id))

@app.context_processor
def inject_unread_count():
    # 全局注入未读消息数量
    if current_user.is_authenticated:
        unread_count = current_user.notifications.filter_by(is_read=False).count()
    else:
        unread_count = 0
    return {'unread_count': unread_count}
@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    form = ReplyForm()

    if form.validate_on_submit():
        reply = Reply(
            content=form.content.data,
            post=post,
            user=current_user,
            parent_reply_id=form.parent_reply_id.data or None
        )
        db.session.add(reply)
        db.session.commit()

        # 发送通知给相关用户
        recipients = set()

        # 通知帖子作者（如果是回复帖子）
        if not reply.parent_reply_id and post.user != current_user:
            recipients.add(post.user)

        # 通知父回复作者（如果是回复某条回复）
        if reply.parent_reply and reply.parent_reply.user != current_user:
            recipients.add(reply.parent_reply.user)

        # 创建通知
        for user in recipients:
            notification = Notification(
                user=user,
                message=f'用户 {current_user.username} 回复了你的内容',
                reply=reply
            )
            db.session.add(notification)

        db.session.commit()

        flash('回复成功！', 'success')
        return redirect(url_for('post', post_id=post.id))
    top_level_replies = [r for r in post.replies if r.parent_reply_id is None]
    return render_template('post.html', post=post, form=form, replies=top_level_replies,
                           post_user=User.query.get_or_404(post.user_id).username)


@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    # 动态加载分类选项
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]  # 新增

    if form.validate_on_submit():
        # 根据选择的分类ID获取分类对象
        category = Category.query.get(form.category.data)  # 修改
        post = Post(
            title=form.title.data,
            content=form.content.data,
            category=category,  # 使用选择的分类
            user=current_user
        )

        if form.files.data:
            filenames = []
            for file in form.files.data:
                if file and allowed_file(file.filename):
                    filename = f"post_{post.id}_{secure_filename(file.filename)}"
                    save_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'post_files')
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir)
                    file.save(os.path.join(save_dir, filename))
                    filenames.append(filename)
            post.attachments = ','.join(filenames)
        db.session.add(post)
        db.session.commit()
        flash('帖子发布成功！', 'success')
        return redirect(url_for('index'))
    return render_template('create_post.html', form=form)

# 初始化数据库
first_request_handled = False

@app.before_request
def create_tables():
    global first_request_handled
    if not first_request_handled:
        db.create_all()
        if not Category.query.first():
            category = Category(name='默认分类', description='这是一个默认分类')
            db.session.add(category)
            db.session.commit()
        first_request_handled = True

if __name__ == '__main__':
    app.run(debug=True, port=5081)