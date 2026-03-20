# 自动联网
import requests
import random
import time
from dotenv import load_dotenv
import os
from playwright.sync_api import sync_playwright
import logging
import ast
from pathlib import Path
import sys

# 日志基础配置
logging.basicConfig(
    level=logging.INFO,  # 级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),  # 写入文件
        logging.StreamHandler()  # 输出到控制台
    ]
)

class Link:
    def __init__(self):
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(__file__).resolve().parent

        load_dotenv(base_dir / "settings.env")

        def parse_literal(value: str | None, default):
            if value is None:
                return default
            s = value.strip()
            if not s:
                return default
            try:
                return ast.literal_eval(s)
            except Exception:
                return default

        default_urls = [
            "https://www.baidu.com",
            "https://www.taobao.com",
            "https://www.jd.com",
            "https://www.1688.com",
            "https://www.58.com",
        ]

        self.urls = parse_literal(os.getenv("URLS"), default_urls)
        self.login_url = os.getenv("LOGIN_URL")
        self.number = os.getenv("NUMBER")
        self.password = os.getenv("PASSWORD")
        self.time_quantums = parse_literal(
            os.getenv("TIME_QUANTUMS"),
            [{"start": "00:00", "end": "23:59", "allow": 1}],
        )
        self.login_success_url = os.getenv("LOGIN_SUCCESS_URL")

        freq_raw = os.getenv("FREQUENCY")
        try:
            self.frequency = int(str(freq_raw).strip()) * 60
        except Exception:
            self.frequency = 10 * 60

        self.login_message = parse_literal(os.getenv("LOGIN_MESSAGE"), {})
        self.browser_path = os.getenv("BROWER_PATH") or "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

    def ping_url(self):
        """
        测试网络连通性
        :return: 是否连通
        """
        # 随机选择一个URL进行测试
        link_url = random.choice(self.urls)
        try:
            response = requests.get(link_url, timeout=10)
            logging.info(f"测试连通性{link_url} 状态码: {response.status_code}")
            return response.status_code == 200
        except requests.RequestException:
            logging.error(f"测试连通性{link_url} 时发生异常")
            return False

    def if_time(self):
        """
        时间段检测
        :return: 是否在时间段内
        """
        # 返回值
        if_time = True
        # 获取当前时间
        current_time = time.strftime("%H:%M", time.localtime())
        for time_quantum in self.time_quantums:
            start_time = time_quantum["start"]
            end_time = time_quantum["end"]
            allow = time_quantum["allow"]
            # 检查当前时间是否在允许的时间段内
            if start_time <= current_time <= end_time and allow == 1:
                break
            # 检查当前时间是否在不允许的时间段内
            if start_time <= current_time <= end_time and allow == 0:
                if_time = False
                return if_time
        return if_time

    def login(self):
        """
        登录
        :return: 是否登录成功
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True,
                                            executable_path=self.browser_path,
                                            slow_mo=500,  # 新增：操作延迟
                                            args=["--disable-blink-features=AutomationControlled"]  # 新增：禁用自动化检测
                                            )
                page = browser.new_page()
                page.goto(self.login_url)
                page.wait_for_load_state("networkidle")
                # 账号输入框
                num_input = page.locator(self.login_message["number_input"])
                num_input.fill(self.number)
                time.sleep(1)
                # 密码输入框
                pswd_input = page.locator(self.login_message["password_input"])
                pswd_input.fill(self.password)
                time.sleep(1)
                # 登录按钮
                login_btn = page.locator(self.login_message["login_button"])
                login_btn.click(timeout=15000,force=True)
                # 查看是否登录成功
                try:
                    page.wait_for_url(self.login_success_url,timeout=15000)
                    logging.info("成功跳转")
                    # 检测连通性
                    if self.ping_url():
                        return True
                    else:
                        return False
                except Exception as e:
                    logging.error(f"登录失败: {e}")
                    return False
                finally:
                    # 关闭浏览器
                    browser.close()
        except Exception as e:
            logging.error(f"登录失败: {e}")
            return False

    def run(self):
        """
        执行函数
        """
        # 循环执行
        while True:
            # 是否在时间段内
            if self.if_time():
                # 网络联通检测
                if self.ping_url():
                    logging.info("网络已连通")
                    # 时间暂停
                    time.sleep(self.frequency)
                else:
                    logging.info("网络未连通，尝试登录")
                    login_if = self.login()
                    if login_if:
                        logging.info("登录成功")
                    else:
                        logging.error("登录失败")
            else:
                logging.info("当前时间不在时间段内，等待下一个时间段")
                # 休眠处理
                time.sleep(int(self.frequency / 2))


if __name__ == "__main__":
    link = Link()
    link.run()
