# 导入 Python 自带的 SQLite 数据库模块
import sqlite3
import os

# 定义数据库文件名字
DB_NAME = "images.db"


# 初始化数据库 - 创建包含所有字段的表
def init_db():
    """程序第一次启动时调用，用来创建数据表"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 创建完整的图片表，包含所有需要的字段
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            hash TEXT,
            date TEXT,
            flags TEXT,
            thumb_path TEXT
        )
    """)

    conn.commit()
    conn.close()


# 保存图片信息（完整版）
def save_image(path, hash_value, date="", flags="", thumb_path=""):
    """保存一张图片的所有信息到数据库"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO images (path, hash, date, flags, thumb_path)
        VALUES (?, ?, ?, ?, ?)
    """, (path, hash_value, date, flags, thumb_path))

    conn.commit()
    conn.close()


# 获取全部图片数据（返回5个字段）
def get_images():
    """获取所有图片的完整数据"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT path, hash, date, flags, thumb_path FROM images")
    data = cursor.fetchall()

    conn.close()
    return data


# 获取所有有效图片（用于查重）
def get_valid_images():
    """只获取标记为'valid'的图片路径和哈希"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT path, hash FROM images WHERE flags='valid'")
    data = cursor.fetchall()

    conn.close()
    return data


# 删除所有图片记录
def clear_images():
    """清空数据库所有记录，用于重新扫描"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM images")
    conn.commit()
    conn.close()
