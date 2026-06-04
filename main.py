"""
洛克王国远行商人商品定时邮件推送

每天4个时段自动获取商品数据并通过邮件通知：
  上午场 08:00 - 12:00
  下午场 12:00 - 16:00
  傍晚场 16:00 - 20:00
  夜间场 20:00 - 24:00

用法:
  1. 复制 config.example.ini 为 config.ini，填写配置
  2. pip install requests schedule
  3. python main.py
"""

import configparser
import datetime
import json
import os
import smtplib
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
import schedule

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

CONFIG_FILE = "config.ini"

if not os.path.exists(CONFIG_FILE):
    print(f"[ERROR] 配置文件 {CONFIG_FILE} 不存在")
    print(f"[HINT]  请复制 config.example.ini 为 {CONFIG_FILE} 并填写配置")
    sys.exit(1)

config = configparser.ConfigParser()
config.read(CONFIG_FILE, encoding="utf-8")

REQUIRED_KEYS = {
    "smtp": ["host", "port", "use_ssl", "sender", "password", "recipients"],
    "api": ["url", "key"],
}

missing = []
for section, keys in REQUIRED_KEYS.items():
    if not config.has_section(section):
        missing.append(f"[{section}] 整个配置节缺失")
    else:
        for key in keys:
            if not config.has_option(section, key):
                missing.append(f"[{section}] {key}")

if missing:
    print("[ERROR] 配置文件缺少以下必要配置项:")
    for m in missing:
        print(f"  - {m}")
    print(f"[HINT]  请检查 {CONFIG_FILE} 并补充缺失的配置")
    sys.exit(1)

SMTP_HOST = config.get("smtp", "host")
SMTP_PORT = config.getint("smtp", "port")
SMTP_SSL = config.getboolean("smtp", "use_ssl")
SMTP_SENDER = config.get("smtp", "sender")
SMTP_PASSWORD = config.get("smtp", "password")
SMTP_RECIPIENTS = [r.strip() for r in config.get("smtp", "recipients").split(",")]

API_URL = config.get("api", "url")
API_KEY = config.get("api", "key")

# ---------------------------------------------------------------------------
# 时段定义
# ---------------------------------------------------------------------------

PERIODS = [
    {"name": "上午场", "start": "08:00"},
    {"name": "下午场", "start": "12:00"},
    {"name": "傍晚场", "start": "16:00"},
    {"name": "夜间场", "start": "20:00"},
]

# ---------------------------------------------------------------------------
# API 请求
# ---------------------------------------------------------------------------


MAX_RETRIES = 30  # 最大重试次数（每次间隔1分钟，最多重试30次即30分钟）


def fetch_shop_data():
    """获取当前时段商品数据"""
    headers = {"X-API-Key": API_KEY}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_URL, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[ERROR] 第 {attempt} 次请求失败: {e}")
        else:
            status = data.get("status", "unknown")
            items = data.get("data", [])
            if status == "success" and items:
                return data
            print(f"[INFO] 第 {attempt} 次尝试: status={status}, 商品数={len(items)}，1分钟后重试...")

        if attempt < MAX_RETRIES:
            time.sleep(60)

    print("[ERROR] 达到最大重试次数，放弃本次推送")
    return None


# ---------------------------------------------------------------------------
# 邮件构建与发送
# ---------------------------------------------------------------------------


def build_html(data):
    """根据 API 返回数据构建邮件 HTML（仅在有商品数据时调用）"""
    period = data.get("period", "未知")
    timestamp = data.get("timestamp", "")
    items = data.get("data", [])

    rows = ""
    for item in items:
        name = item.get("name", "未知")
        price = item.get("price", "0")
        limit = item.get("limit", "不限购")
        end_time = item.get("end_time", "")
        img = item.get("image_url", "")
        img_tag = f'<img src="{img}" alt="{name}" width="48" height="48" style="vertical-align:middle;margin-right:8px;">' if img else ""
        rows += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{img_tag}{name}</td>
            <td style="padding:8px;border:1px solid #ddd;text-align:right;">{price} 洛克贝</td>
            <td style="padding:8px;border:1px solid #ddd;text-align:center;">{limit}</td>
            <td style="padding:8px;border:1px solid #ddd;text-align:center;">{end_time}</td>
        </tr>
        """

    return f"""
    <h2>📦 远行商人 - {period}</h2>
    <p style="color:#666;">数据时间: {timestamp} · 共 {len(items)} 件商品</p>
    <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;">
        <thead>
            <tr style="background:#4a90d9;color:#fff;">
                <th style="padding:10px;border:1px solid #ddd;text-align:left;">商品</th>
                <th style="padding:10px;border:1px solid #ddd;text-align:right;">价格</th>
                <th style="padding:10px;border:1px solid #ddd;">限购</th>
                <th style="padding:10px;border:1px solid #ddd;">下架时间</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <p style="color:#999;font-size:12px;margin-top:16px;">洛克王国远行商人商品推送</p>
    """


def send_email(html_content, period_name):
    """发送邮件"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"洛克王国远行商人 - {period_name} 商品提醒"
    msg["From"] = SMTP_SENDER
    msg["To"] = ", ".join(SMTP_RECIPIENTS)

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        if SMTP_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()

        server.login(SMTP_SENDER, SMTP_PASSWORD)
        server.sendmail(SMTP_SENDER, SMTP_RECIPIENTS, msg.as_string())
        server.quit()
        print(f"[OK] 邮件已发送 -> {', '.join(SMTP_RECIPIENTS)}")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败: {e}")


# ---------------------------------------------------------------------------
# 定时任务
# ---------------------------------------------------------------------------


def job(period_name):
    """获取数据并发送邮件"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now}] 执行任务: {period_name}")

    data = fetch_shop_data()
    if data is None:
        print(f"[SKIP] {period_name} 未获取到商品数据，跳过发送")
        return

    print(f"[INFO] API 状态: {data.get('status')} · 商品数: {data.get('count', 0)}")

    html = build_html(data)
    send_email(html, period_name)


def main():
    print("=" * 50)
    print("洛克王国远行商人商品定时邮件推送")
    print("=" * 50)
    print(f"SMTP 服务器 : {SMTP_HOST}:{SMTP_PORT}")
    print(f"发件人      : {SMTP_SENDER}")
    print(f"收件人      : {', '.join(SMTP_RECIPIENTS)}")
    print(f"API 地址    : {API_URL}")
    print("-" * 50)

    # 为每个时段创建定时任务（延迟2分钟，等待API数据更新）
    for p in PERIODS:
        h, m = map(int, p["start"].split(":"))
        m += 2
        if m >= 60:
            h += 1
            m -= 60
        schedule_time = f"{h:02d}:{m:02d}"
        schedule_name = p["name"]
        schedule.every().day.at(schedule_time).do(job, period_name=schedule_name)
        print(f"已注册定时任务: {schedule_name} @ 每天 {schedule_time}（延迟2分钟）")

    # 启动时如果处于营业时段且已过2分钟缓冲，立即执行一次
    now = datetime.datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    if 8 <= current_hour < 24:
        for p in PERIODS:
            start_h, start_m = map(int, p["start"].split(":"))
            next_start = start_h + 4
            # 判断是否在该时段内，且已过2分钟缓冲期
            if start_h <= current_hour < next_start:
                if current_hour > start_h or current_minute >= 2:
                    print(f"\n当前处于 {p['name']}，立即执行一次推送...")
                    job(p["name"])
                else:
                    print(f"\n当前处于 {p['name']} 前2分钟缓冲期，跳过本次等待定时任务触发")
                break
    else:
        print("\n当前为未营业时段（00:00-08:00），等待 08:02 开始推送")

    print("\n[RUNNING] 定时任务运行中，按 Ctrl+C 退出...\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
