import os
import ast
import re
import sys
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ModuleNotFoundError as e:
    raise SystemExit("缺少依赖 PySide6，请先执行：pip install -r requirements.txt") from e


ENV_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


@dataclass
class EnvLine:
    raw: str
    key: str | None = None
    value: str | None = None


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def read_env_file(path: Path) -> list[EnvLine]:
    if not path.exists():
        return []

    lines: list[EnvLine] = []
    for raw in path.read_text(encoding="utf-8").splitlines(keepends=True):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            lines.append(EnvLine(raw=raw))
            continue
        m = ENV_KEY_RE.match(raw)
        if not m:
            lines.append(EnvLine(raw=raw))
            continue
        key, value = m.group(1), m.group(2)
        lines.append(EnvLine(raw=raw, key=key, value=value))
    return lines


def write_env_file(path: Path, lines: list[EnvLine], updates: dict[str, str]) -> None:
    seen: set[str] = set()
    out: list[str] = []

    def normalize_value(s: str) -> str:
        s = s.strip()
        s = " ".join(s.splitlines())
        return s

    for line in lines:
        if line.key is None:
            out.append(line.raw)
            continue
        key = line.key
        if key in updates:
            value = normalize_value(updates[key])
            out.append(f"{key} = {value}\n")
            seen.add(key)
        else:
            out.append(line.raw if line.raw.endswith("\n") else (line.raw + "\n"))
            seen.add(key)

    for key, value in updates.items():
        if key in seen:
            continue
        out.append(f"{key} = {normalize_value(value)}\n")

    path.write_text("".join(out), encoding="utf-8")


def _unquote_if_quoted(value: str) -> str:
    s = value.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        try:
            v = ast.literal_eval(s)
        except Exception:
            return s
        return v if isinstance(v, str) else s
    return s


def _parse_literal(value: str) -> object | None:
    s = value.strip()
    if not s:
        return None
    try:
        return ast.literal_eval(s)
    except Exception:
        return None


def _to_py_list_str(items: list[str]) -> str:
    return "[" + ", ".join(repr(x) for x in items) + "]"


def _to_py_dict_str(d: dict[str, str]) -> str:
    return repr(d)


def _set_windows_app_id(app_id: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes  # noqa: PLC0415

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        return



class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("自动联网")
        self.resize(920, 680)

        self._base_dir = _app_base_dir()
        icon_path = self._base_dir / "linkURL.ico"
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        self._process: QtCore.QProcess | None = None
        self._log_timer = QtCore.QTimer(self)
        self._log_timer.setInterval(500)
        self._log_timer.timeout.connect(self._poll_log)
        self._log_path: Path | None = None
        self._log_pos = 0
        self._env_lines: list[EnvLine] = []

        self.env_path_edit = QtWidgets.QLineEdit()
        self.env_path_edit.setReadOnly(True)
        self.env_browse_btn = QtWidgets.QPushButton("选择...")
        self.env_reload_btn = QtWidgets.QPushButton("重新加载")
        self.env_save_btn = QtWidgets.QPushButton("保存配置")

        self.start_btn = QtWidgets.QPushButton("启动")
        self.stop_btn = QtWidgets.QPushButton("结束")
        self.stop_btn.setEnabled(False)

        self.status_label = QtWidgets.QLabel("未运行")
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.field_urls = QtWidgets.QPlainTextEdit()
        self.field_login_url = QtWidgets.QLineEdit()
        self.field_login_success_url = QtWidgets.QLineEdit()
        self.field_number = QtWidgets.QLineEdit()
        self.field_password = QtWidgets.QLineEdit()
        self.field_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.field_time_quantums = QtWidgets.QPlainTextEdit()
        self.field_frequency = QtWidgets.QLineEdit()
        self.field_selectors = QtWidgets.QPlainTextEdit()
        self.field_browser_path = QtWidgets.QLineEdit()

        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(2000)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.field_urls.setFont(font)
        self.field_time_quantums.setFont(font)
        self.field_selectors.setFont(font)
        self.output.setFont(font)

        self.field_urls.setPlaceholderText("每行一个网址，例如：\nhttps://www.baidu.com\nhttps://www.jd.com")
        self.field_time_quantums.setPlaceholderText('每行一个字典，例如：\n{"start":"00:00","end":"23:59","allow":1}')
        self.field_selectors.setPlaceholderText("共三行：\n第1行：账号输入框选择器\n第2行：密码输入框选择器\n第3行：登录按钮选择器")

        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addWidget(QtWidgets.QLabel("配置文件："))
        top_bar.addWidget(self.env_path_edit, 1)
        top_bar.addWidget(self.env_browse_btn)
        top_bar.addWidget(self.env_reload_btn)
        top_bar.addWidget(self.env_save_btn)

        run_bar = QtWidgets.QHBoxLayout()
        run_bar.addWidget(self.start_btn)
        run_bar.addWidget(self.stop_btn)
        run_bar.addSpacing(16)
        run_bar.addWidget(QtWidgets.QLabel("状态："))
        run_bar.addWidget(self.status_label, 1)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.addRow("测试网址列表：", self.field_urls)
        form.addRow("登录页地址：", self.field_login_url)
        form.addRow("登录成功地址：", self.field_login_success_url)
        form.addRow("账号：", self.field_number)
        form.addRow("密码：", self.field_password)
        form.addRow("运行时间段：", self.field_time_quantums)
        form.addRow("检测间隔（分钟）：", self.field_frequency)
        form.addRow("页面选择器：", self.field_selectors)
        form.addRow("浏览器路径：", self.field_browser_path)

        left = QtWidgets.QWidget()
        left.setLayout(form)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.output)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addLayout(top_bar)
        layout.addLayout(run_bar)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self.setStatusBar(QtWidgets.QStatusBar(self))

        self.env_browse_btn.clicked.connect(self._choose_env_file)
        self.env_reload_btn.clicked.connect(self.load_env)
        self.env_save_btn.clicked.connect(self.save_env)
        self.start_btn.clicked.connect(self.start_program)
        self.stop_btn.clicked.connect(self.stop_program)

        self._set_default_env_path()
        self.load_env()

    def _append_output(self, text: str) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        if not text.endswith("\n"):
            cursor.insertText("\n")
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _set_default_env_path(self) -> None:
        self.env_path_edit.setText(str(self._base_dir / "settings.env"))

    def _selected_run_target(self) -> tuple[str, list[str], str]:
        env_path = self._env_path()
        exe_path = env_path.parent / "auto_link.exe"
        if exe_path.exists() and exe_path.suffix.lower() == ".exe":
            return str(exe_path), [], str(exe_path.parent)
        return sys.executable, [str(self._base_dir / "link.py")], str(self._base_dir)

    def _env_path(self) -> Path:
        return Path(self.env_path_edit.text()).resolve()

    def _choose_env_file(self) -> None:
        start_dir = str(self._env_path().parent)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择配置文件", start_dir, "ENV (*.env);;All (*.*)")
        if not path:
            return
        self.env_path_edit.setText(path)
        self.load_env()

    def load_env(self) -> None:
        path = self._env_path()
        self._env_lines = read_env_file(path)
        values: dict[str, str] = {}
        for line in self._env_lines:
            if line.key:
                values[line.key] = line.value or ""

        urls_raw = values.get("URLS", "")
        urls_val = _parse_literal(urls_raw)
        if isinstance(urls_val, list) and all(isinstance(x, str) for x in urls_val):
            self.field_urls.setPlainText("\n".join(urls_val))
        else:
            self.field_urls.setPlainText(_unquote_if_quoted(urls_raw))

        self.field_login_url.setText(_unquote_if_quoted(values.get("LOGIN_URL", "")))
        self.field_login_success_url.setText(_unquote_if_quoted(values.get("LOGIN_SUCCESS_URL", "")))
        self.field_number.setText(_unquote_if_quoted(values.get("NUMBER", "")))
        self.field_password.setText(_unquote_if_quoted(values.get("PASSWORD", "")))

        tq_raw = values.get("TIME_QUANTUMS", "")
        tq_val = _parse_literal(tq_raw)
        if isinstance(tq_val, list) and all(isinstance(x, dict) for x in tq_val):
            self.field_time_quantums.setPlainText("\n".join(repr(x) for x in tq_val))
        else:
            self.field_time_quantums.setPlainText(_unquote_if_quoted(tq_raw))

        self.field_frequency.setText(_unquote_if_quoted(values.get("FREQUENCY", "")))

        lm_raw = values.get("LOGIN_MESSAGE", "")
        lm_val = _parse_literal(lm_raw)
        if isinstance(lm_val, dict):
            a = str(lm_val.get("number_input", "") or "")
            b = str(lm_val.get("password_input", "") or "")
            c = str(lm_val.get("login_button", "") or "")
            self.field_selectors.setPlainText("\n".join([a, b, c]).rstrip("\n"))
        else:
            self.field_selectors.setPlainText(_unquote_if_quoted(lm_raw))

        self.field_browser_path.setText(_unquote_if_quoted(values.get("BROWER_PATH", "")))

        self.statusBar().showMessage(f"已加载：{path}", 3000)

    def save_env(self) -> None:
        path = self._env_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = self._env_lines
        if not lines and path.exists():
            lines = read_env_file(path)

        urls = [x.strip() for x in self.field_urls.toPlainText().splitlines() if x.strip()]

        tq_lines = [x.strip() for x in self.field_time_quantums.toPlainText().splitlines() if x.strip()]
        tq_items: list[dict] = []
        for one in tq_lines:
            v = _parse_literal(one)
            if not isinstance(v, dict):
                QtWidgets.QMessageBox.warning(self, "配置错误", f"运行时间段格式不正确：\n{one}")
                return
            tq_items.append(v)

        selectors = [x.strip() for x in self.field_selectors.toPlainText().splitlines()]
        while len(selectors) < 3:
            selectors.append("")
        selectors = selectors[:3]
        login_message = {
            "number_input": selectors[0],
            "password_input": selectors[1],
            "login_button": selectors[2],
        }

        freq = self.field_frequency.text().strip()
        if freq and not freq.isdigit():
            QtWidgets.QMessageBox.warning(self, "配置错误", "检测间隔必须是整数（分钟）")
            return

        updates = {
            "URLS": _to_py_list_str(urls),
            "LOGIN_URL": repr(self.field_login_url.text().strip()),
            "LOGIN_SUCCESS_URL": repr(self.field_login_success_url.text().strip()),
            "NUMBER": repr(self.field_number.text().strip()),
            "PASSWORD": repr(self.field_password.text()),
            "TIME_QUANTUMS": "[" + ", ".join(repr(x) for x in tq_items) + "]",
            "FREQUENCY": freq or "10",
            "LOGIN_MESSAGE": _to_py_dict_str(login_message),
            "BROWER_PATH": repr(self.field_browser_path.text().strip()),
        }
        write_env_file(path, lines, updates)
        self._env_lines = read_env_file(path)
        self.statusBar().showMessage(f"已保存：{path}", 3000)
        self._write_gui_log(f"已保存配置：{path}")

    def start_program(self) -> None:
        if self._process is not None:
            return

        self.save_env()
        if self._process is not None:
            return

        program, args, workdir = self._selected_run_target()
        self._prepare_log_follow(Path(workdir) / "app.log", clear=True)

        proc = QtCore.QProcess(self)
        proc.setProgram(program)
        proc.setArguments(args)
        proc.setWorkingDirectory(workdir)
        proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        proc.finished.connect(self._on_process_finished)

        self._process = proc
        proc.start()
        if not proc.waitForStarted(3000):
            self.statusBar().showMessage("启动失败：进程未能启动", 5000)
            self._stop_log_follow()
            self._process = None
            return

        self.status_label.setText("运行中")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("已启动", 3000)
        self._write_gui_log(f"已启动：{program} {' '.join(args)}")

    def stop_program(self) -> None:
        proc = self._process
        if proc is None:
            return

        self._write_gui_log("请求结束")
        proc.terminate()
        if not proc.waitForFinished(3000):
            proc.kill()
            proc.waitForFinished(3000)

    def _on_process_finished(self) -> None:
        self._poll_log()
        self._stop_log_follow()
        self._process = None
        self.status_label.setText("未运行")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("进程已退出", 3000)
        self._write_gui_log("已关闭")

    def _prepare_log_follow(self, log_path: Path, clear: bool = True) -> None:
        if clear:
            self.output.clear()
        self._log_path = log_path
        try:
            self._log_pos = log_path.stat().st_size
        except Exception:
            self._log_pos = 0
        self._log_timer.start()

    def _stop_log_follow(self) -> None:
        self._log_timer.stop()
        self._log_path = None
        self._log_pos = 0

    def _current_log_path(self) -> Path:
        if self._log_path is not None:
            return self._log_path
        try:
            return self._env_path().parent / "app.log"
        except Exception:
            return self._base_dir / "app.log"

    def _write_gui_log(self, message: str, level: str = "INFO") -> None:
        log_path = self._current_log_path()
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            line = f"{ts} - {level} - {message}\n"
            log_path.open("a", encoding="utf-8").write(line)
        except Exception:
            return

    def _poll_log(self) -> None:
        log_path = self._log_path
        if log_path is None:
            return
        try:
            if not log_path.exists():
                return
            size = log_path.stat().st_size
            if size < self._log_pos:
                self._log_pos = 0
            with log_path.open("rb") as f:
                f.seek(self._log_pos)
                chunk = f.read()
                self._log_pos = f.tell()
            if not chunk:
                return
            text = chunk.decode("utf-8", errors="ignore")
            if text:
                self._append_output(text.rstrip("\n"))
        except Exception:
            return


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    _set_windows_app_id("auto_link.自动联网")
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("自动联网")
    app.setApplicationDisplayName("自动联网")
    icon_path = _app_base_dir() / "linkURL.ico"
    if icon_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
