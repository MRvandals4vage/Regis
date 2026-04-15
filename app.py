# app.py — PyQt6 GUI bridging Menu Bar capabilities with a Floating Chat Window

import sys
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QSystemTrayIcon, QMenu
)
from PyQt6.QtGui import QIcon, QFont, QAction, QColor, QPalette
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from planner import plan
from executor import execute
from memory import Memory
from vision import Vision

class WorkerSignals(QObject):
    finished = pyqtSignal(str)   # Returns a log message or status
    log_msg  = pyqtSignal(str)

class AIWorker(threading.Thread):
    def __init__(self, command, memory, vision, signals):
        super().__init__()
        self.command = command
        self.memory = memory
        self.vision = vision
        self.signals = signals

    def run(self):
        self.memory.save_command(self.command)
        self.signals.log_msg.emit(f"🟢 User: {self.command}\n[Thinking...]")

        action_plan = plan(self.command, screen_context="")
        steps = action_plan.get("steps", [])

        if not steps:
            self.signals.finished.emit("❌ Planner returned no steps.\n")
            return

        plan_str = "📋 Plan:\n"
        for i, s in enumerate(steps, 1):
            plan_str += f"  {i}. {s['action']} → {s.get('params', {})}\n"
        self.signals.log_msg.emit(plan_str)

        self.signals.log_msg.emit("[Executing...]")
        results = execute(steps)
        self.memory.save_steps(steps)

        ok = sum(1 for r in results if r["status"] == "ok")
        self.signals.finished.emit(f"✅ Executed {ok}/{len(steps)} steps.\n")

class FloatingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.memory = Memory()
        self.vision = Vision()
        
        # Window settings
        self.setWindowTitle("AI Assistant")
        self.setFixedSize(400, 500)
        
        # Make the window float above others
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)

        # Style sheet (Dark mode minimal look)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QTextEdit { 
                background-color: #252526; color: #cccccc; 
                border: 1px solid #333333; border-radius: 5px; 
                padding: 5px; font-family: 'Menlo'; font-size: 13px;
            }
            QLineEdit { 
                background-color: #3c3c3c; color: #ffffff; 
                border: 1px solid #555555; border-radius: 5px; 
                padding: 8px; font-size: 14px;
            }
            QPushButton { 
                background-color: #0e639c; color: white; 
                border: none; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1177bb; }
        """)

        # Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        vbox = QVBoxLayout(central_widget)
        vbox.setContentsMargins(15, 15, 15, 15)
        vbox.setSpacing(10)

        # Chat log display
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        vbox.addWidget(self.log_area)

        # Input row
        hbox = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a command...")
        self.input_field.returnPressed.connect(self.handle_command)
        
        self.run_btn = QPushButton("Run")
        self.run_btn.setFixedSize(60, 34)
        self.run_btn.clicked.connect(self.handle_command)

        hbox.addWidget(self.input_field)
        hbox.addWidget(self.run_btn)
        vbox.addLayout(hbox)

        # Setup signals
        self.signals = WorkerSignals()
        self.signals.log_msg.connect(self.append_log)
        self.signals.finished.connect(self.worker_finished)

    def handle_command(self):
        text = self.input_field.text().strip()
        if not text:
            return
        
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.run_btn.setEnabled(False)

        # Run LLM + Exec in background thread
        worker = AIWorker(text, self.memory, self.vision, self.signals)
        worker.start()

    def append_log(self, text):
        self.log_area.append(text)
        # Scroll to bottom
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def worker_finished(self, final_text):
        self.append_log(final_text)
        self.input_field.setEnabled(True)
        self.run_btn.setEnabled(True)
        self.input_field.setFocus()

class AITrayApp:
    def __init__(self):
        self.app = QApplication(sys.sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.window = FloatingWindow()

        # System Tray
        self.tray = QSystemTrayIcon()
        
        # NOTE: Using a generic transparent/1px icon so it doesn't crash if an icon file is missing.
        # Natively you'd pass a real 'icon.png' path here
        icon = QIcon() 
        self.tray.setIcon(icon) 
        self.tray.setVisible(True)
        
        # Menu
        self.menu = QMenu()
        
        toggle_action = QAction("Toggle Chat Window", self.menu)
        toggle_action.triggered.connect(self.toggle_window)
        self.menu.addAction(toggle_action)

        quit_action = QAction("Quit Assistant", self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)
        
        self.tray.setContextMenu(self.menu)

        # You can click the tray icon to trigger actions too (not supported perfectly on all macOS versions)
        # self.tray.activated.connect(self.tray_icon_clicked)

        self.window.show()

    def toggle_window(self):
        if self.window.isVisible():
            self.window.hide()
        else:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    tray_app = AITrayApp()
    tray_app.run()
