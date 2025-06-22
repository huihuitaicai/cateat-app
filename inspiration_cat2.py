import sys
import sqlite3
import csv
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QDialog, QTextEdit, QPushButton, QFileDialog, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QKeySequence


DB_FILE = "inspirations.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inspirations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class TextViewerDialog(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("查看内容")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(text)
        layout.addWidget(self.text_edit)
        btn_close = QLabel('<a href="#">关闭</a>')
        btn_close.setTextInteractionFlags(Qt.TextBrowserInteraction)
        btn_close.linkActivated.connect(self.accept)
        layout.addWidget(btn_close)

class InspirationViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("投喂记录查看")
        self.resize(600, 400)
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        layout.addWidget(self.table)

        # 新增导出按钮
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("全部导出")
        self.export_btn.clicked.connect(self.export_all)
        btn_layout.addStretch()
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        self.load_data()

        self.table.cellDoubleClicked.connect(self.show_cell_content)

    def load_data(self):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.execute("SELECT timestamp, content FROM inspirations ORDER BY timestamp DESC")
            rows = cursor.fetchall()

        self.table.setRowCount(len(rows))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["时间", "灵感内容"])

        for row_idx, (timestamp, content) in enumerate(rows):
            self.table.setItem(row_idx, 0, QTableWidgetItem(timestamp))
            self.table.setItem(row_idx, 1, QTableWidgetItem(content))

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

    def show_cell_content(self, row, column):
        item = self.table.item(row, column)
        if item:
            dlg = TextViewerDialog(item.text(), self)
            dlg.exec_()

    def export_all(self):
        # 选择保存路径和文件名
        path, _ = QFileDialog.getSaveFileName(self, "保存文件", "inspirations.txt", "CSV 文件 (*.txt)")
        if not path:
            return

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.execute("SELECT timestamp, content FROM inspirations ORDER BY timestamp DESC")
            rows = cursor.fetchall()

        try:
            with open(path, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for row in rows:
                    writer.writerow([row[0]])  # 时间单独一行
                    writer.writerow([row[1]])  # 内容单独一行
            self.export_btn.setText("导出成功！")
            QTimer.singleShot(2000, lambda: self.export_btn.setText("全部导出"))
        except Exception as e:
            self.export_btn.setText("导出失败！")
            QTimer.singleShot(2000, lambda: self.export_btn.setText("全部导出"))
            print("导出错误:", e)

class InspirationCat(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("灵感猫猫投喂箱")
        self.setFixedSize(200, 200)
        self.setAcceptDrops(True)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.click_count = 0
        self.click_timer = QTimer()
        self.click_timer.setInterval(1000)  # 1秒内连续点击次数有效
        self.click_timer.timeout.connect(self.reset_click_count)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.cat_image = QLabel()
        self.idle_pixmap = QPixmap(resource_path("cat_idle.png")).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.eat_pixmap = QPixmap(resource_path("cat_eat.png")).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cat_image.setPixmap(self.idle_pixmap)
        self.cat_image.setAlignment(Qt.AlignCenter)

        self.label = QLabel("拖文字到我这里～\n或复制后按Ctrl+V投喂")
        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.cat_image)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.old_pos = None  # 用于拖动窗口

    def reset_click_count(self):
        self.click_count = 0
        self.click_timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()
            self.click_count += 1
            if not self.click_timer.isActive():
                self.click_timer.start()
            if self.click_count >= 3:
                self.open_viewer()
                self.reset_click_count()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.cat_image.setPixmap(self.eat_pixmap)  # 拖入时变吃图

    def dragLeaveEvent(self, event):
        self.cat_image.setPixmap(self.idle_pixmap)  # 拖出控件恢复闲置图
    
    def dropEvent(self, event):
        text = event.mimeData().text().strip()
        if text:
            self.feed_inspiration(text)
        self.cat_image.setPixmap(self.idle_pixmap)  # 松手后恢复闲置图

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            if text:
                self.feed_inspiration(text)
        else:
            super().keyPressEvent(event)

    def feed_inspiration(self, text):
        self.label.setText("灵感吃下了！😋")
        self.cat_image.setPixmap(self.eat_pixmap)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO inspirations (content, timestamp) VALUES (?, ?)", (text, now))
            conn.commit()
        QTimer.singleShot(1500, self.reset_cat)

    def reset_cat(self):
        self.cat_image.setPixmap(self.idle_pixmap)
        self.label.setText("拖文字到我嘴里～\n或复制后按Ctrl+V投喂")

    def open_viewer(self):
        self.viewer = InspirationViewer()
        self.viewer.show()

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    win = InspirationCat()
    win.show()
    sys.exit(app.exec_())
