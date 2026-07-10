# 导入系统模块
import sys
import os

# 导入PySide6界面组件
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QListView, QVBoxLayout,
    QWidget, QPushButton, QLabel, QMessageBox, QFileDialog
)
from PySide6.QtCore import (
    QAbstractListModel, Qt, QRunnable, QThreadPool,
    Signal, QObject
)
from PySide6.QtGui import QPixmap

# 导入自定义模块
import db
import worker


# ===== 图片数据模型 =====
class ImageModel(QAbstractListModel):
    """定义图片数据模型，告诉界面如何显示图片列表"""

    def __init__(self, data):
        super().__init__()
        self._data = data  # 保存图片数据列表

    def rowCount(self, parent=None):
        """返回数据总行数"""
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        """界面渲染时调用，返回对应位置的数据"""
        if not index.isValid():
            return None

        row = index.row()
        # 解包5个字段：path, hash, date, flags, thumb_path
        path, hash_val, date, flags, thumb_path = self._data[row]

        if role == Qt.DisplayRole:
            # 显示文件名
            return os.path.basename(path)

        if role == Qt.DecorationRole:
            # 显示缩略图
            if thumb_path and os.path.exists(thumb_path):
                return QPixmap(thumb_path)

        if role == Qt.UserRole + 1:
            # 自定义角色：返回日期
            return date

        if role == Qt.UserRole + 2:
            # 自定义角色：返回状态标签
            return flags

        return None


# ===== 后台线程信号 =====
class WorkerSignals(QObject):
    """定义线程间通信的信号"""
    finished = Signal()  # 完成信号
    progress = Signal(str)  # 进度提示信号


# ===== 扫描后台任务 =====
class ScanWorker(QRunnable):
    """后台扫描任务，不阻塞界面"""

    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self.signals = WorkerSignals()

    def run(self):
        """后台线程执行的代码"""
        self.signals.progress.emit("正在扫描图片...")
        worker.scan_folder(self.folder)

        self.signals.progress.emit("扫描完成，正在分类...")
        worker.move_duplicates()

        self.signals.finished.emit()


# ===== 主窗口 =====
class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        # 窗口设置
        self.setWindowTitle("图片清理助手")
        self.resize(1200, 800)

        # 创建中心容器
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 状态栏
        self.status = QLabel("就绪")
        layout.addWidget(self.status)

        # 图片列表视图（网格模式）
        self.list_view = QListView()
        self.list_view.setUniformItemSizes(True)  # 优化性能
        self.list_view.setViewMode(QListView.IconMode)  # 图标网格模式
        layout.addWidget(self.list_view)

        # 按钮区域
        btn_layout = QVBoxLayout()

        self.scan_btn = QPushButton("📁 选择文件夹并扫描")
        self.scan_btn.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.scan_btn)

        self.move_btn = QPushButton("🗑️ 移动重复/无效图片")
        self.move_btn.clicked.connect(self.start_move)
        btn_layout.addWidget(self.move_btn)

        layout.addLayout(btn_layout)

        # 初始化数据库
        db.init_db()
        self.load_data()

    def load_data(self):
        """从数据库加载数据并刷新界面"""
        rows = db.get_images()
        self.model = ImageModel(rows)
        self.list_view.setModel(self.model)

    def start_scan(self):
        """开始扫描文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if not folder:
            return

        self.status.setText("扫描中...")
        self.scan_btn.setEnabled(False)

        # 创建后台任务
        self.worker = ScanWorker(folder)
        self.worker.signals.finished.connect(lambda: self.on_scan_done(folder))
        self.worker.signals.progress.connect(self.status.setText)

        # 启动线程
        QThreadPool.globalInstance().start(self.worker)

    def on_scan_done(self, folder):
        """扫描完成回调"""
        self.status.setText("✅ 扫描完成")
        self.load_data()
        self.scan_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "完成",
            f"已扫描 {len(db.get_images())} 张图片\n\n"
            "重复图片和无效图片已自动移到子文件夹。"
        )

    def start_move(self):
        """手动执行移动操作"""
        reply = QMessageBox.question(
            self,
            "确认",
            "将重复/无效图片移至子文件夹，是否继续？"
        )

        if reply == QMessageBox.Yes:
            self.status.setText("移动中...")
            worker.move_duplicates()
            self.load_data()
            self.status.setText("✅ 移动完成")


# ===== 程序入口 =====
if __name__ == "__main__":
    # 启用GPU加速
    os.environ["QSG_RENDER_LOOP"] = "opengl"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 现代主题

    win = MainWindow()
    win.show()

    sys.exit(app.exec())
