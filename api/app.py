import configparser
import psycopg2
from psycopg2 import pool
from flask import Flask, request, jsonify
import requests
from PIL import Image
import io
from colorthief import ColorThief
import imageio
import redis
from gevent import pywsgi

# 读取配置文件
config = configparser.ConfigParser()
config.read('static/config.ini')

# 初始化PostgreSQL数据库连接池
db_pool = None
if config.getboolean('database', 'enabled'):
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1,  # 最小连接数
        20,  # 最大连接数
        dbname=config['database']['dbname'],
        user=config['database']['user'],
        password=config['database']['password'],
        host=config['database']['host'],
        port=config['database']['port']
    )

# 初始化Redis
if config.getboolean('redis', 'enabled'):
    redis_password = config['redis']['password']
    redis_client = redis.Redis(
        host=config['redis']['host'],
        port=config['redis']['port'],
        db=config['redis']['db'],
        password=redis_password if redis_password else None
    )
else:
    redis_client = None

app = Flask(__name__)


# 从连接池中获取连接并执行查询
def query_image(url):
    if db_pool:
        conn = db_pool.getconn()
        try:
            c = conn.cursor()
            c.execute("SELECT img_color FROM images WHERE img_url=%s", (url,))
            result = c.fetchone()
            conn.commit()
            return result
        finally:
            db_pool.putconn(conn)


# 从连接池中获取连接并执行插入
def insert_image(url, color):
    if db_pool:
        conn = db_pool.getconn()
        try:
            c = conn.cursor()
            c.execute("INSERT INTO images (img_url, img_color) VALUES (%s, %s)", (url, color))
            conn.commit()
        finally:
            db_pool.putconn(conn)


@app.route('/api/Imgcolor', methods=['GET'])
def get_dominant_color_api():
    # 获取图片URL
    image_url = request.args.get('img')
    if not image_url:
        return jsonify({"error": "缺少图片URL"}), 400

    # 查询Redis缓存
    if redis_client and redis_client.exists(image_url):
        color = redis_client.get(image_url)
        return jsonify({"RGB": color.decode('utf-8')})

    # 查询数据库
    color = query_image(image_url)
    if color:
        # 将结果插入Redis缓存，并设置过期时间
        if redis_client:
            redis_client.set(image_url, color[0], ex=config.getint('redis', 'expire_time'))
        return jsonify({"RGB": color[0]})

    # 下载图片
    response = requests.get(image_url)
    if response.status_code != 200:
        return jsonify({"error": "无法下载图片"}), 400

    # 将图片数据转换为字节流
    image_bytes = io.BytesIO(response.content)

    # 尝试使用imageio读取图片
    try:
        image = imageio.imread(image_bytes)
        # imageio读取的图片是numpy数组，需要转换为Pillow的Image对象
        image = Image.fromarray(image)
    except:
        # 如果imageio无法读取图片，使用Pillow尝试读取
        image = Image.open(image_bytes)

    # 使用colorthief提取主题色
    color_thief = ColorThief(image_bytes)
    dominant_color = color_thief.get_color(quality=1)  # quality参数可以调整提取质量

    # 将RGB颜色转换为十六进制格式
    hex_color = '#{:02x}{:02x}{:02x}'.format(dominant_color[0], dominant_color[1], dominant_color[2])

    # 将结果插入数据库
    insert_image(image_url, hex_color)

    # 将结果插入Redis缓存，并设置过期时间
    if redis_client:
        redis_client.set(image_url, hex_color, ex=config.getint('redis', 'expire_time'))

    # 返回JSON格式的结果
    return jsonify({"RGB": hex_color})


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('127.0.0.1', 5000), app)
    server.serve_forever()