from app import app
from extensions import db
from models import User, Category, Post, Reply

def init_db():
    with app.app_context():
        db.create_all()
        if not Category.query.first():
            category = Category(name='默认分类', description='这是一个默认分类')
            category2=Category(name='game',description='idk')
            db.session.add(category)
            db.session.add(category2)
            db.session.commit()
            print("默认分类已创建。")
        print("数据库初始化完成！")

if __name__ == '__main__':
    init_db()