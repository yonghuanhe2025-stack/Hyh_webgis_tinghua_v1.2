# -*- coding: utf-8 -*-
import paho.mqtt.client as mqtt
import os
import signal
import sys
import atexit
from datetime import datetime
from time import sleep

# ========== MQTT 服务器信息 ==========
MQTT_BROKER = "47.101.130.178"
MQTT_PORT = 9003
MQTT_USER = "tsari"
MQTT_PASS = "tsari123"
MQTT_TOPIC = "/dtu_serial_rx"

# ========== 路径与文件 ==========
BASE_DIR = os.path.dirname(__file__)
LOG_FILE = os.path.join(BASE_DIR, "mqtt_log_running.txt")  # 运行中日志（退出时重命名）
TEST_DATA_DIR = os.path.join(BASE_DIR, "test_data")        # 单条消息输出目录
os.makedirs(TEST_DATA_DIR, exist_ok=True)

# ========== 退出时执行：重命名日志 ==========
def finalize_log():
    """程序结束时将运行中的日志重命名为带时间戳的日志。"""
    if os.path.exists(LOG_FILE):
        end_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(BASE_DIR, f"mqtt_log_{end_time}.txt")
        try:
            os.replace(LOG_FILE, target)
            print(f"\n📝 日志已保存为: {target}")
        except Exception as e:
            print(f"\n⚠️ 重命名日志失败: {e}")

# 退出信号
atexit.register(finalize_log)
signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

# ========== MQTT 回调 ==========
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ 已连接到 MQTT 服务器")
        client.subscribe(MQTT_TOPIC)
        print(f"📡 已订阅主题: {MQTT_TOPIC}")
        print(f"📝 日志文件(运行中): {LOG_FILE}")
        print(f"📂 单条消息输出目录: {TEST_DATA_DIR}")
    else:
        print(f"❌ 连接失败，错误码: {rc}")

def _fmt_sec_filename(dt: datetime) -> str:
    """返回秒级文件名：YYYY_MM_DD_HH_MM_SS.txt"""
    return f"{dt.strftime('%Y_%m_%d_%H_%M_%S')}.txt"

def on_message(client, userdata, msg):
    message = msg.payload.decode("utf-8", errors="ignore")
    now = datetime.now()

    # 终端打印（到毫秒）
    ts_print = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_entry = f"[{ts_print}] {msg.topic} -> {message}\n"
    print(f"📩 {log_entry.strip()}")

    # 1) 追加写“运行中日志”
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"⚠️ 写运行日志失败: {e}")

    # 2) 单条消息另存为文件（严格秒级命名；若同秒存在则等待下一秒）
    while True:
        dt = datetime.now()
        path = os.path.join(TEST_DATA_DIR, _fmt_sec_filename(dt))
        try:
            # 独占创建；存在则抛 FileExistsError
            with open(path, "x", encoding="utf-8") as f:
                f.write(message)
            print(f"💾 已保存消息: {path}")
            break
        except FileExistsError:
            # 同一秒已有文件：等待到下一秒（保持无后缀、无毫秒）
            remaining = max(0.0, 1.0 - dt.microsecond / 1_000_000.0) + 0.001
            sleep(remaining)
        except Exception as e:
            print(f"⚠️ 保存单条消息失败: {e}")
            break

# ========== 主程序 ==========
def main():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
