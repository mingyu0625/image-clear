# 导入系统模块
import os
import cv2  # OpenCV，用来读取图片
import hashlib  # 用来计算文件哈希
import sqlite3
from datetime import datetime
from PIL import Image
import imagehash  # 图片感知哈希，用于查重

# 导入数据库模块
import db

# 缩略图缓存目录（中文）
THUMB_DIR = "缩略图缓存"


# 确保缩略图目录存在
def ensure_thumb_dir():
    if not os.path.exists(THUMB_DIR):
        os.makedirs(THUMB_DIR)


# 计算文件的MD5哈希（用于精确去重）
def get_file_hash(file_path):
    """计算文件的MD5值，用于精确判断文件是否相同"""
    try:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


# 计算图片的感知哈希（用于相似图片去重）
def get_image_hash(file_path):
    """计算图片的感知哈希，用于判断图片是否相似（即使尺寸、格式不同）"""
    try:
        img = Image.open(file_path)
        # 转换为灰度图，统一处理
        img = img.convert("L")
        # 缩小到8x8，计算感知哈希
        return str(imagehash.phash(img, hash_size=8))
    except Exception as e:
        return None


# 生成缩略图
def generate_thumbnail(file_path):
    """为图片生成缩略图，用于界面显示"""
    try:
        ensure_thumb_dir()
        # 用文件路径的哈希作为缩略图文件名
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        thumb_path = os.path.join(THUMB_DIR, f"{file_hash}.jpg")

        # 如果缩略图已存在，直接返回路径
        if os.path.exists(thumb_path):
            return thumb_path

        # 生成缩略图
        img = Image.open(file_path)
        img.thumbnail((200, 200))  # 缩放到200x200以内
        img.save(thumb_path, "JPEG", quality=85)
        return thumb_path
    except Exception as e:
        return None


# 扫描文件夹中的所有图片
def scan_folder(folder_path):
    """扫描指定文件夹，提取所有图片信息并存入数据库"""
    print(f"正在扫描: {folder_path}")

    # 支持的图片格式
    extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp")

    # 清空旧数据
    db.clear_images()

    # 遍历文件夹
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # 检查是否是图片
            if not file.lower().endswith(extensions):
                continue

            full_path = os.path.join(root, file)

            try:
                # 获取文件修改日期
                mtime = os.path.getmtime(full_path)
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

                # 计算文件哈希和图片哈希
                file_hash = get_file_hash(full_path)
                img_hash = get_image_hash(full_path)

                # 如果图片无法读取，标记为无效
                if img_hash is None:
                    flags = "无效"
                else:
                    flags = "有效"

                # 生成缩略图
                thumb_path = generate_thumbnail(full_path)

                # 保存到数据库（使用完整的哈希值）
                db.save_image(full_path, file_hash, date_str, flags, thumb_path)

                print(f"  ✓ {file}")

            except Exception as e:
                print(f"  ✗ {file} - 错误: {e}")
                continue

    print("扫描完成!")


# 移动重复或无效的图片
def move_duplicates():
    """找出重复图片和无效图片，移动到子文件夹"""
    # 获取所有有效图片（有哈希值的）
    valid_images = db.get_valid_images()

    # 用字典记录已见过的哈希值
    seen_hashes = {}
    duplicates = []
    invalid_files = []

    # 获取所有图片
    all_images = db.get_images()

    for path, hash_val, date, flags, thumb in all_images:
        # 如果图片无效，加入待移动列表
        if flags == "无效":
            invalid_files.append(path)
            continue

        # 如果哈希值已存在，说明是重复图片
        if hash_val in seen_hashes:
            duplicates.append(path)
        else:
            seen_hashes[hash_val] = path

    # 创建目标文件夹（中文目录名）
    base_dir = os.path.dirname(all_images[0][0]) if all_images else "."

    dup_dir = os.path.join(base_dir, "重复图片")
    invalid_dir = os.path.join(base_dir, "无效图片")

    os.makedirs(dup_dir, exist_ok=True)
    os.makedirs(invalid_dir, exist_ok=True)

    # 移动重复图片
    for file_path in duplicates:
        try:
            file_name = os.path.basename(file_path)
            dest = os.path.join(dup_dir, file_name)

            # 如果目标已存在，加数字后缀
            counter = 1
            while os.path.exists(dest):
                name, ext = os.path.splitext(file_name)
                dest = os.path.join(dup_dir, f"{name}_{counter}{ext}")
                counter += 1

            os.rename(file_path, dest)
            print(f"已移动重复图片: {file_name}")
        except Exception as e:
            print(f"移动失败 {file_path}: {e}")

    # 移动无效图片
    for file_path in invalid_files:
        try:
            file_name = os.path.basename(file_path)
            dest = os.path.join(invalid_dir, file_name)

            counter = 1
            while os.path.exists(dest):
                name, ext = os.path.splitext(file_name)
                dest = os.path.join(invalid_dir, f"{name}_{counter}{ext}")
                counter += 1

            os.rename(file_path, dest)
            print(f"已移动无效图片: {file_name}")
        except Exception as e:
            print(f"移动失败 {file_path}: {e}")

    print(f"移动完成: 重复图片 {len(duplicates)} 张, 无效图片 {len(invalid_files)} 张")
