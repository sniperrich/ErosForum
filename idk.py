import os

from dotenv import load_dotenv
load_dotenv('smtp.env')  # 加载 .env 文件

print(os.getenv('MAIL_SERVER'))
