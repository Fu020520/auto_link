# 自动断网重连（OpenClaw 龙虾机器人/校园网重新认证）

OpenClaw 龙虾机器人部署在实验室、机房、校园网等环境时，常见问题是网络会被周期性断开或需要重新认证登录。本项目通过“定时检测 + 断网自动打开认证页并登录”的方式，让设备在断网后能自动恢复联网，减少人工干预。

推荐入口：`main.py`

## 功能概览

- 随机选择一个测试网址进行连通性检测（HTTP 200 视为正常）
- 按时间段策略决定是否执行（可设置禁止运行的区间）
- 断网时自动打开认证/登录页，自动填写账号密码并点击登录
- 日志同时输出到控制台并写入 `app.log`

## 工作流程

1. 读取同级目录的 `settings.env` 配置。
2. 在允许的时间段内循环执行：
   - 从 `URLS` 中随机取一个地址，使用 HTTP GET 测试连通性。
   - 若状态码为 200：认为网络已连通。
   - 否则：打开 `LOGIN_URL`，按 `LOGIN_MESSAGE` 中配置的选择器填写账号/密码并点击登录按钮（用于重新认证）。
3. 每次循环结束后休眠 `FREQUENCY` 分钟（代码中会自动换算成秒）。

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 安装 Playwright 浏览器运行时（二选一）

- 使用 Playwright 自带 Chromium（推荐，最省事）：

```bash
python -m playwright install chromium
```

- 使用本机 Chrome/Chromium：在 `settings.env` 配置 `BROWER_PATH` 指向浏览器可执行文件路径

3. 配置 `settings.env`

从 `settings.env.example` 复制一份为 `settings.env`，再按你的网络认证页面情况修改（账号密码建议放在本地，不要提交到公开仓库）。

```bash
copy settings.env.example settings.env
```

4. 运行（推荐）

```bash
python main.py
```

如需不启动 GUI，直接运行循环脚本：

```bash
python main.py --cli
```

也可以分别运行：

```bash
python gui.py
python link.py
```

## GUI 说明

- GUI 页面输入时不需要双引号，保存时会自动写入 `settings.env` 所需的格式。
- 右侧输出会跟随本次运行写入到 `app.log` 的新增内容。

## 使用打包版（Windows 可执行程序）

如果你已自行打包生成可执行文件（例如 `dist/auto_link.exe`），可按下面方式使用：

1. 准备配置文件

把 `settings.env.example` 复制到 `dist` 目录并重命名为 `settings.env`，再按你的认证页修改账号、密码、选择器等：

```bash
copy settings.env.example dist\settings.env
```

2. 配置浏览器路径（建议必须设置）

打包版默认不会自带 Playwright 的 Chromium 运行时，因此建议在 `dist/settings.env` 里设置 `BROWER_PATH` 指向本机 Chrome/Chromium 的可执行文件路径。

3. 运行

```bash
dist\auto_link.exe
```

日志会输出到控制台并写入 `dist\app.log`（与可执行文件同目录）。

## 自己打包（PyInstaller）

建议使用 `main.py` 作为统一入口进行打包：

```bash
pyinstaller -F -w -i linkURL.ico --name 自动联网 main.py
```

打包后把 `settings.env.example` 复制到 exe 同目录并改名为 `settings.env` 再运行。

## 配置说明（settings.env）

配置文件位于项目根目录：`settings.env`。脚本通过 `python-dotenv` 加载后再解析。

- `URLS`
  - 用途：用于连通性测试的 URL 列表（脚本会随机挑一个）。
  - 示例：`["https://www.baidu.com", "https://www.jd.com"]`
- `LOGIN_URL`
  - 用途：登录页地址（Playwright 会 `goto` 这个地址）。
  - 建议：写完整协议，例如 `http://192.168.254.25/` 或 `https://...`，仅写 IP 可能无法正常打开。
- `LOGIN_SUCCESS_URL`
  - 用途：用于判断是否登录成功的目标地址（`wait_for_url`）。
- `NUMBER`
  - 用途：账号/工号/手机号等“用户名”字段的值。
- `PASSWORD`
  - 用途：密码字段的值。
- `TIME_QUANTUMS`
  - 用途：允许/禁止运行的时间段列表。
  - 格式：`[{"start":"HH:MM","end":"HH:MM","allow":1或0}, ...]`
  - 规则：当当前时间落在某段 `allow:0` 的区间内时，脚本会跳过登录/检测并持续等待。
  - 示例：`[{"start":"08:30","end":"18:30","allow":1},{"start":"18:31","end":"23:59","allow":0}]`
- `FREQUENCY`
  - 用途：循环间隔，单位为“分钟”。
  - 示例：`10` 表示每 10 分钟检测一次。
- `LOGIN_MESSAGE`
  - 用途：登录页元素的选择器配置，用于定位账号输入框、密码输入框、登录按钮。
  - 格式：`{"number_input":"...","password_input":"...","login_button":"..."}`
  - 说明：Playwright 支持 CSS 选择器等写法；如果使用 XPath，可按 Playwright 语法写为 `xpath=...`。
- `BROWER_PATH`
  - 用途：浏览器可执行文件路径（可选）。
  - 说明：该键名与代码保持一致（注意是 `BROWER_PATH`，不是 `BROWSER_PATH`）。
  - Windows 路径建议使用双反斜杠或正斜杠，例如：
    - `C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe`
    - `C:/Program Files/Google/Chrome/Application/chrome.exe`

## 输出与排错

- 日志文件：`app.log`
- 常见问题排查：
  - 连通性检测失败：确认 `URLS` 可访问、代理/防火墙策略正确。
  - 登录页无法打开：确认 `LOGIN_URL` 包含正确协议与路径。
  - 元素找不到：检查 `LOGIN_MESSAGE` 中的选择器是否匹配登录页实际元素。
  - 登录后仍判定断网：更换 `URLS` 为你所在网络环境下稳定可访问的网站，或增加多个候选地址。
