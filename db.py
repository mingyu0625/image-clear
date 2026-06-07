import sqlite3  # 导入数据库模块，用来存图片信息
import os  # 导入系统模块，用来处理文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images.db")  # 数据库文件路径，自动放在程序同级目录
def init_db():  # 定义初始化数据库的函数
    conn = sqlite3.connect(DB_PATH)  # 连接数据库文件，不存在就自动创建
    c = conn.cursor()  # 创建游标对象，用来执行SQL命令
    c.execute("""  # 开始执行建表语句
        CREATE TABLE IF NOT EXISTS images (  # 如果表不存在就创建，名字叫images
            id INTEGER PRIMARY KEY AUTOINCREMENT,  # 自动编号，每张照片唯一标识
            path TEXT UNIQUE,  # 图片完整路径，不允许重复
            date TEXT,  # 拍摄或创建日期
            hash TEXT,  # 图片指纹值，用来查重
            flags TEXT DEFAULT 'valid',  # 状态标签，默认是有效图片
            thumb_path TEXT,  # 缩略图路径，加速显示
            group_id INTEGER  # 分组编号，用来管理重复图
        )  # 建表语句结束
    """)  # 执行建表命令
    c.execute("CREATE INDEX IF NOT EXISTS idx_date ON images(date)")  # 给日期字段建索引，让按时间排序更快
    c.execute("CREATE INDEX IF NOT EXISTS idx_hash ON images(hash)")  # 给指纹字段建索引，让查重比对更快
    conn.commit()  # 保存刚才的建表操作
    conn.close()  # 关闭数据库连接，释放资源
def get_images():  # 定义获取所有图片信息的函数
    conn = sqlite3.connect(DB_PATH)  # 连接数据库
    c = conn.cursor()  # 创建游标
    c.execute("SELECT path, date, flags, thumb_path FROM images ORDER BY date DESC")  # 按日期倒序查询所有图片信息
    rows = c.fetchall()  # 把查询结果全部取出来
    conn.close()  # 关闭连接
    return rows  # 返回数据给界面用
def update_flags(path, flags):  # 定义更新图片状态的函数
    conn = sqlite3.connect(DB_PATH)  # 连接数据库
    c = conn.cursor()  # 创建游标
    c.execute("UPDATE images SET flags=? WHERE path=?", (flags, path))  # 根据路径更新状态标签
    conn.commit()  # 保存修改
    conn.close()  # 关闭连接
