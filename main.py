import sys  # 导入系统模块，处理命令行参数
import os  # 导入系统模块，处理文件路径
from PySide6.QtWidgets import QApplication, QMainWindow, QListView, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox  # 导入界面组件
from PySide6.QtCore import QAbstractListModel, Qt, QRunnable, QThreadPool, Signal, QObject  # 导入核心功能：数据模型、多线程、信号
from PySide6.QtGui import QPixmap, QStandardItemModel  # 导入图形组件：图片加载
import db  # 导入数据库模块
import worker  # 导入后台处理模块
class ImageModel(QAbstractListModel):  # 定义图片数据模型类
    def __init__(self, data):  # 初始化函数
        super().__init__()  # 调用父类初始化
        self._data = data  # 保存传入的图片数据列表
    def rowCount(self, parent=None):  # 重写行数方法，告诉界面有多少条数据
        return len(self._data)  # 返回数据总长度
    def data(self, index, role=Qt.DisplayRole):  # 重写数据获取方法，界面渲染时调用
        if not index.isValid(): return None  # 索引无效就返回空
        row = index.row()  # 获取当前行号
        path, date, flags, thumb = self._data[row]  # 拆解该行数据
        if role == Qt.DisplayRole: return os.path.basename(path)  # 如果是显示文本角色，返回文件名
        if role == Qt.DecorationRole:  # 如果是图标角色
            if thumb and os.path.exists(thumb):  # 如果缩略图存在
                return QPixmap(thumb)  # 加载并返回图片对象
        if role == Qt.UserRole + 1: return date  # 自定义角色1返回日期，用于时间轴分组
        if role == Qt.UserRole + 2: return flags  # 自定义角色2返回状态标签
        return None  # 其他情况返回空
class WorkerSignals(QObject):  # 定义信号类，用于线程间通信
    finished = Signal()  # 定义完成信号
    progress = Signal(str)  # 定义进度提示信号
class ScanWorker(QRunnable):  # 定义扫描后台任务类
    def __init__(self, folder):  # 初始化函数
        super().__init__()  # 调用父类初始化
        self.folder = folder  # 保存要扫描的文件夹路径
        self.signals = WorkerSignals()  # 创建信号对象
    def run(self):  # 重写运行方法，这里写后台要执行的代码
        self.signals.progress.emit("正在扫描图片...")  # 发送进度提示
        worker.scan_folder(self.folder)  # 调用扫描函数
        self.signals.progress.emit("扫描完成，正在分类...")  # 发送下一步提示
        worker.move_duplicates()  # 调用移动函数
        self.signals.finished.emit()  # 发送完成信号
class MainWindow(QMainWindow):  # 定义主窗口类
    def __init__(self):  # 初始化函数
        super().__init__()  # 调用父类初始化
        self.setWindowTitle("图片清理助手")  # 设置窗口标题
        self.resize(1200, 800)  # 设置窗口大小
        central = QWidget()  # 创建中心容器
        self.setCentralWidget(central)  # 设为窗口主体
        layout = QVBoxLayout(central)  # 创建垂直布局
        self.status = QLabel("就绪")  # 创建状态提示标签
        layout.addWidget(self.status)  # 加入布局
        self.list_view = QListView()  # 创建列表视图组件
        self.list_view.setUniformItemSizes(True)  # 开启统一尺寸优化，提升滚动性能
        self.list_view.setViewMode(QListView.IconMode)  # 设置为图标网格模式，类似相册
        layout.addWidget(self.list_view)  # 加入布局
        btn_layout = QVBoxLayout()  # 创建按钮垂直布局
        self.scan_btn = QPushButton("📁 选择文件夹并扫描")  # 创建扫描按钮
        self.scan_btn.clicked.connect(self.start_scan)  # 点击按钮触发扫描函数
        btn_layout.addWidget(self.scan_btn)  # 加入布局
        self.move_btn = QPushButton("🗑️ 移动重复/无效图片")  # 创建移动按钮
        self.move_btn.clicked.connect(self.start_move)  # 点击按钮触发移动函数
        btn_layout.addWidget(self.move_btn)  # 加入布局
        layout.addLayout(btn_layout)  # 把按钮布局加入主布局
        db.init_db()  # 初始化数据库
        self.load_data()  # 加载数据到界面
    def load_data(self):  # 加载数据函数
        rows = db.get_images()  # 从数据库取数据
        self.model = ImageModel(rows)  # 创建数据模型
        self.list_view.setModel(self.model)  # 绑定到列表视图
    def start_scan(self):  # 开始扫描函数
        from PySide6.QtWidgets import QFileDialog  # 导入文件夹选择框
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")  # 弹出选择框
        if not folder: return  # 没选就退出
        self.status.setText("扫描中...")  # 更新状态提示
        self.worker = ScanWorker(folder)  # 创建后台任务
        self.worker.signals.finished.connect(lambda: self.on_scan_done(folder))  # 绑定完成信号
        self.worker.signals.progress.connect(self.status.setText)  # 绑定进度信号
        QThreadPool.globalInstance().start(self.worker)  # 放入全局线程池运行，不卡界面
    def on_scan_done(self, folder):  # 扫描完成回调
        self.status.setText(f"✅ 扫描完成")  # 更新状态
        self.load_data()  # 刷新界面数据
        QMessageBox.information(self, "完成", f"已扫描 {len(db.get_images())} 张图片")  # 弹出提示框
    def start_move(self):  # 开始移动函数
        if QMessageBox.question(self, "确认", "将重复/无效图片移至子文件夹，是否继续？") == QMessageBox.Yes:  # 弹出确认框
            worker.move_duplicates()  # 执行移动
            self.load_data()  # 刷新界面
            self.status.setText("✅ 移动完成")  # 更新状态
if __name__ == "__main__":  # 判断是否直接运行本文件
    os.environ["QSG_RENDER_LOOP"] = "opengl"  # 强制开启GPU硬件加速，保证滚动不卡
    app = QApplication(sys.argv)  # 创建应用实例
    app.setStyle("Fusion")  # 使用现代融合主题，界面更干净
    win = MainWindow()  # 创建主窗口
    win.show()  # 显示窗口
    sys.exit(app.exec())  # 进入事件循环，程序正常退出
