from datetime import datetime
from hashlib import md5

from flask import url_for

from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    avatar_path = db.Column(db.String(200), default='default_avatar.png')  # 新增头像路径字段

    # def get_avatar(self):
    #     # 优先使用自定义头像，否则使用Gravatar
    #     if self.avatar_path and self.avatar_path != 'default_avatar.png':
    #         return url_for('static', filename=f'uploads/avatars/{self.avatar_path}')
    #     else:
    #         return self.avatar()  # 保留原Gravatar方法
    def avatar(self, size=80):
        # 使用 Gravatar 生成头像（基于邮箱哈希）
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def get_avatar(self):
        # 优先返回自定义头像路径
        if self.avatar_path and self.avatar_path != 'default_avatar.png':
            return url_for('static', filename=f'uploads/avatars/{self.avatar_path}')
        # 回退到Gravatar
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'))

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    reply = db.relationship('Reply', backref=db.backref('notification', uselist=False))
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('posts', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 确保这一行存在
    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    attachments = db.Column(db.String(500))

from extensions import db
class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    code = db.Column(db.String(6))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    # 帖子关联
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    post = db.relationship('Post', backref=db.backref('replies', lazy=True))
    # 用户关联
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('replies', lazy=True))
    # 嵌套回复支持
    parent_reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'))  # 新增字段
    parent_reply = db.relationship('Reply', remote_side=[id], backref='child_replies')  # 自关联