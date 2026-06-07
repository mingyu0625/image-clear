import os  # 导入系统模块，处理文件路径
import cv2  # 导入OpenCV库，用来分析图片内容
import imagehash  # 导入指纹库，生成图片唯一特征值
from PIL import Image  # 导入Pillow库，处理图片缩放和格式
import math  # 导入数学库，计算图片信息熵
import sqlite3  # 导入数据库模块
from concurrent.futures import ThreadPoolExecutor  # 导入多线程工具，加速扫描
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images.db")  # 数据库路径
THUMB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumbs")  # 缩略图文件夹路径
os.makedirs(THUMB_DIR, exist_ok=True)  # 创建缩略图文件夹，已存在就不报错
def get_date_from_path(path):  # 从文件路径获取创建日期
    try:  # 尝试执行
        stat = os.stat(path)  # 获取文件属性
        return str(stat.st_ctime)[:10]  # 提取创建时间的前10位，格式为YYYY-MM-DD
    except:  # 如果获取失败
        return "1970-01-01"  # 返回默认日期，防止程序崩溃
def compute_hash(path):  # 计算图片指纹值
    try:  # 尝试执行
        img = Image.open(path).convert("L").resize((16, 16))  # 打开图片，转灰度，缩放到16x16像素
        return str(imagehash.dhash(img))  # 生成dHash指纹并转成字符串
    except:  # 如果图片损坏或格式不支持
        return "null"  # 返回空值，标记为无效
def is_invalid(path):  # 判断图片是否无效
    try:  # 尝试分析
        img = cv2.imread(path)  # 用OpenCV读取图片
        if img is None: return "corrupted"  # 读不到就标记为损坏
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # 转成灰度图方便计算
        if cv2.Laplacian(gray, cv2.CV_64F).var() < 80: return "blurry"  # 计算边缘方差，小于80说明太模糊
        h, w = img.shape[:2]  # 获取图片高度和宽度
        aspect = w / h  # 计算宽高比
        if 1.75 < aspect < 1.85 or 0.53 < aspect < 0.57: return "screenshot"  # 符合常见截屏比例就标记为截屏
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])  # 计算灰度直方图
        entropy = -sum((p/255.0)*math.log2(p/255.0) for p in hist if p > 0)  # 计算信息熵，值越低说明内容越单调
        if entropy < 1.5: return "meaningless"  # 信息熵太低说明是纯色或无意义图
    except:  # 分析过程中出错
        return "corrupted"  # 统一标记为损坏
    return "valid"  # 全部检查通过，标记为有效
def generate_thumb(path, thumb_path):  # 生成缩略图函数
    try:  # 尝试生成
        img = Image.open(path).resize((200, 200), Image.LANCZOS)  # 打开原图，高质量缩放到200x200
        img.save(thumb_path, "JPEG", quality=85)  # 保存为JPEG格式，质量85%平衡清晰度和体积
    except:  # 生成失败不报错，跳过
        pass
def scan_folder(folder):  # 扫描文件夹主函数
    conn = sqlite3.connect(DB_PATH)  # 连接数据库
    c = conn.cursor()  # 创建游标
    c.execute("DELETE FROM images")  # 清空旧数据，避免重复扫描累加
    conn.commit()  # 保存清空操作
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]  # 只找常见图片格式
    print(f"Scanning {len(files)} images...")  # 打印扫描数量
    with ThreadPoolExecutor(max_workers=4) as executor:  # 启动4个后台线程加速处理
        for i, path in enumerate(files):  # 遍历每张图片
            date = get_date_from_path(path)  # 获取日期
            h = compute_hash(path)  # 计算指纹
            flags = is_invalid(path)  # 判断是否无效
            thumb_path = os.path.join(THUMB_DIR, f"{os.path.basename(path)}.thumb.jpg")  # 生成缩略图路径
            generate_thumb(path, thumb_path)  # 生成缩略图
            c.execute("INSERT OR IGNORE INTO images (path, date, hash, flags, thumb_path) VALUES (?,?,?,?,?)", (path, date, h, flags, thumb_path))  # 写入数据库，路径重复就跳过
            if (i+1) % 100 == 0:  # 每处理100张
                conn.commit()  # 保存一次进度，防止断电丢数据
                print(f"Processed {i+1}/{len(files)}")  # 打印进度
    conn.commit()  # 最后保存剩余数据
    conn.close()  # 关闭数据库
    print("Scan complete.")  # 打印完成提示
def move_duplicates():  # 移动重复和无效图片函数
    conn = sqlite3.connect(DB_PATH)  # 连接数据库
    c = conn.cursor()  # 创建游标
    c.execute("SELECT path, hash FROM images WHERE flags='valid'")  # 只查有效图片的指纹
    rows = c.fetchall()  # 取出数据
    conn.close()  # 关闭连接
    groups = {}  # 创建字典用来分组
    for path, h in rows:  # 遍历每张有效图
        if h not in groups: groups[h] = []  # 如果指纹没出现过，新建分组
        groups[h].append(path)  # 把路径加到对应指纹分组里
    dup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Duplicates")  # 重复图文件夹路径
    invalid_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Invalid")  # 无效图文件夹路径
    os.makedirs(dup_dir, exist_ok=True)  # 创建重复图文件夹
    os.makedirs(invalid_dir, exist_ok=True)  # 创建无效图文件夹
    moved = 0  # 记录移动数量
    conn = sqlite3.connect(DB_PATH)  # 重新连接数据库
    c = conn.cursor()  # 创建游标
    for h, paths in groups.items():  # 遍历每个指纹分组
        if len(paths) > 1:  # 如果分组里超过1张图
            for p in paths[1:]:  # 从第二张开始算重复
                os.rename(p, os.path.join(dup_dir, os.path.basename(p)))  # 移动到重复文件夹
                c.execute("UPDATE images SET flags='duplicate' WHERE path=?", (p,))  # 更新数据库状态
                moved += 1  # 计数器加1
    c.execute("UPDATE images SET flags='invalid' WHERE flags IN ('blurry','screenshot','meaningless','corrupted')")  # 把所有无效标签统一改为invalid
    for p in c.execute("SELECT path FROM images WHERE flags='invalid'").fetchall():  # 找出所有无效图路径
        os.rename(p[0], os.path.join(invalid_dir, os.path.basename(p[0])))  # 移动到无效文件夹
        moved += 1  # 计数器加1
    conn.commit()  # 保存所有修改
    conn.close()  # 关闭数据库
    print(f"Moved {moved} files.")  # 打印移动总数
