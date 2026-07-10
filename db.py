# 导入 Python 自带的 SQLite 数据库模块
# 用来保存图片路径、图片哈希等信息
import sqlite3


# 定义数据库文件名字
# 程序运行后会自动生成 images.db 文件
DB_NAME = "images.db"


# 初始化数据库函数
# 程序第一次启动时调用，用来创建数据表
def init_db():

    # 连接 SQLite 数据库
    # 如果 images.db 不存在，SQLite 会自动创建
    conn = sqlite3.connect(DB_NAME)


    # 创建数据库操作游标
    # 后续所有 SQL 命令都通过 cursor 执行
    cursor = conn.cursor()


    # 执行创建图片数据表的 SQL
    # IF NOT EXISTS 表示如果已经存在，就不要重复创建
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (

        -- 图片编号，自动增加
        id INTEGER PRIMARY KEY AUTOINCREMENT,


        -- 图片完整路径
        -- 例如：D:/photo/test.jpg
        path TEXT UNIQUE,


        -- 图片哈希值
        -- 用来判断两张图片是否相似
        hash TEXT

    )
    """)


    # 保存数据库修改
    conn.commit()


    # 关闭数据库连接
    # 防止文件被占用
    conn.close()



# 保存一张图片的信息
# path 是图片路径
# hash_value 是图片计算出来的哈希
def save_image(path, hash_value):


    # 打开数据库
    conn = sqlite3.connect(DB_NAME)


    # 创建游标
    cursor = conn.cursor()


    # 插入图片数据
    # 如果路径已经存在，就替换旧数据
    cursor.execute("""
    INSERT OR REPLACE INTO images
    (
        path,
        hash
    )
    VALUES
    (
        ?,
        ?
    )
    """,
    (
        path,
        hash_value
    ))


    # 保存修改
    conn.commit()


    # 关闭数据库
    conn.close()



# 获取全部图片数据
# 返回所有图片路径和哈希
def get_images():


    # 打开数据库
    conn = sqlite3.connect(DB_NAME)


    # 创建游标
    cursor = conn.cursor()


    # 查询全部图片
    cursor.execute("""
    SELECT
        path,
        hash
    FROM images
    """)


    # 获取查询结果
    data = cursor.fetchall()


    # 关闭数据库
    conn.close()


    # 返回图片列表
    return data



# 删除数据库里的所有图片记录
# 用于重新扫描
def clear_images():


    # 打开数据库
    conn = sqlite3.connect(DB_NAME)


    # 创建游标
    cursor = conn.cursor()


    # 删除全部记录
    cursor.execute("""
    DELETE FROM images
    """)


    # 保存修改
    conn.commit()


    # 关闭数据库
    conn.close()
