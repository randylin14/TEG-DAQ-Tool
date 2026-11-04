import datetime
from collections import deque
import tkinter as tk
from tkinter import messagebox, ttk
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation


# ================= 1. 彈出視窗選擇 COM 埠 =================
# ================= 1. 彈出視窗選擇 COM 埠 =================
def select_com_port() -> str | None:
  selected_port: str | None = None

  root = tk.Tk()
  root.title("TEG 實驗連線設定")
  root.geometry("360x200")
  root.resizable(False, False)

  # 置中視窗
  root.update_idletasks()
  width = root.winfo_width()
  height = root.winfo_height()
  x = (root.winfo_screenwidth() // 2) - (width // 2)
  y = (root.winfo_screenheight() // 2) - (height // 2)
  root.geometry(f"{width}x{height}+{x}+{y}")

  tk.Label(
      root,
      text="請選擇 Arduino 所在的 COM 埠:",
      font=("Arial", 11, "bold"),
  ).pack(pady=15)

  # 自動掃描可用 COM 埠
  ports = [port.device for port in serial.tools.list_ports.comports()]
  default_port = ports[0] if ports else "COM3"

  combo = ttk.Combobox(root, values=ports, font=("Arial", 12), width=18)
  combo.pack(pady=5)
  combo.set(default_port)

  def on_confirm():
    nonlocal selected_port
    port = combo.get().strip()
    if not port:
      messagebox.showerror("錯誤", "請選擇或輸入有效的 COM 埠！")
      return
    selected_port = port
    root.destroy()

  btn = tk.Button(
      root,
      text="確定連線並啟動",
      command=on_confirm,
      bg="#2ecc71",
      fg="white",
      font=("Arial", 11, "bold"),
      width=15,
      height=1,
  )
  btn.pack(pady=15)

  root.mainloop()
  return selected_port
# 執行選擇視窗
SERIAL_PORT = select_com_port()
if not SERIAL_PORT:
  print("❌ 未選擇 COM 埠，程式已取消執行。")
  exit()

BAUD_RATE = 9600
MAX_POINTS = 100  # 圖表顯示最近 100 筆資料 (約 200 秒)

# ================= 2. 初始化 CSV 記錄檔 =================
filename = f"TEG_Power_Log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
csv_file = open(filename, mode="w", encoding="utf-8-sig")
csv_file.write(
    "PC_Time,Arduino_Time(s),T1(C),T2(C),T3(C),T4(C),Delta_T(C),V_Open(V),V_Load(V),Power(mW)\n"
)
csv_file.flush()

# 開啟序列埠
try:
  ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
  print(f"✅ 成功連接 {SERIAL_PORT} (溫度 + 雙電壓 + 功率 DAQ 模式)")
  print(f"📁 完整數據正即時儲存至：{filename}")
  print("📊 關閉圖表視窗即可安全結束記錄。\n")
except Exception as e:
  messagebox.showerror(
      "連線錯誤",
      f"無法開啟 {SERIAL_PORT}。\n請確認連接埠是否正確且未被其他軟體佔用。\n錯誤: {e}",
  )
  csv_file.close()
  exit()

# 儲存繪圖資料的佇列
times = deque(maxlen=MAX_POINTS)
t1_data = deque(maxlen=MAX_POINTS)
t2_data = deque(maxlen=MAX_POINTS)
t3_data = deque(maxlen=MAX_POINTS)
t4_data = deque(maxlen=MAX_POINTS)
v_open_data = deque(maxlen=MAX_POINTS)
v_load_data = deque(maxlen=MAX_POINTS)
power_data = deque(maxlen=MAX_POINTS)

# ================= 3. 設定 Matplotlib 動態圖表 =================
plt.rcParams["axes.unicode_minus"] = False
fig, (ax_temp, ax_volt, ax_power) = plt.subplots(
    3, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 2, 2]}
)

if fig.canvas.manager is not None:
  fig.canvas.manager.set_window_title(
      f"TEG 溫差發電與功率即時量測系統 [{SERIAL_PORT}]"
  )

# --- 上圖：四通道溫度曲線 ---
(line_t1,) = ax_temp.plot(
    [], [], label="T1 (°C)", color="#e74c3c", linewidth=2, marker="o", markersize=3
)
(line_t2,) = ax_temp.plot(
    [], [], label="T2 (°C)", color="#e67e22", linewidth=2, marker="o", markersize=3
)
(line_t3,) = ax_temp.plot(
    [], [], label="T3 (°C)", color="#2ecc71", linewidth=2, marker="o", markersize=3
)
(line_t4,) = ax_temp.plot(
    [], [], label="T4 (°C)", color="#3498db", linewidth=2, marker="o", markersize=3
)
ax_temp.set_ylabel("Temperature (°C)", fontsize=10, fontweight="bold")
ax_temp.legend(loc="upper left", frameon=True, fontsize=8, ncol=4)
ax_temp.grid(True, linestyle="--", alpha=0.6)

# --- 中圖：電壓曲線 (V_Open & V_Load) ---
(line_vopen,) = ax_volt.plot(
    [],
    [],
    label="V_Open (V)",
    color="#9b59b6",
    linewidth=2,
    marker="s",
    markersize=3,
)
(line_vload,) = ax_volt.plot(
    [],
    [],
    label="V_Load (V)",
    color="#8e44ad",
    linewidth=2,
    linestyle="--",
    marker="^",
    markersize=3,
)
ax_volt.set_ylabel("Voltage (V)", fontsize=10, fontweight="bold")
ax_volt.legend(loc="upper left", frameon=True, fontsize=8, ncol=2)
ax_volt.grid(True, linestyle="--", alpha=0.6)

# --- 下圖：發電功率曲線 (mW) ---
(line_power,) = ax_power.plot(
    [],
    [],
    label="Power (mW)",
    color="#e67e22",
    linewidth=2.2,
    marker="d",
    markersize=3,
)
ax_power.set_xlabel("Time (s)", fontsize=10, fontweight="bold")
ax_power.set_ylabel("Power (mW)", fontsize=10, fontweight="bold")
ax_power.legend(loc="upper left", frameon=True, fontsize=8)
ax_power.grid(True, linestyle="--", alpha=0.6)


# 避開檢查誤判的格式化函式
def format_val_2f(val):
  if val == val and val > -100:
    return "%.2f" % val
  return ""


def format_val_4f(val):
  if val == val and val > -100:
    return "%.4f" % val
  return ""


def format_title(val, unit=""):
  if val == val:
    return ("%.1f" % val) + unit
  return "OPEN"


def update_plot(_):
  while ser.in_waiting > 0:
    raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
    if not raw_line or raw_line.startswith("Time"):
      continue

    parts = raw_line.split(",")
    if len(parts) == 8:
      try:
        ard_time = float(parts[0])
        vals = [-999.0 if "NAN" in p.upper() else float(p) for p in parts[1:]]
        t1, t2, t3, t4, v_open, v_load, power = vals

        delta_t = (t1 - t2) if (t1 > -100 and t2 > -100) else -999.0
        now_str = datetime.datetime.now().strftime("%H:%M:%S")

        # 寫入 CSV 檔案
        csv_line = (
            f"{now_str},{ard_time},{format_val_2f(t1)},{format_val_2f(t2)},"
            f"{format_val_2f(t3)},{format_val_2f(t4)},{format_val_2f(delta_t)},"
            f"{format_val_4f(v_open)},{format_val_4f(v_load)},{format_val_2f(power)}"
        )
        print(
            f"[{now_str}] {ard_time:4.0f}s | ΔT:{format_val_2f(delta_t)}°C |"
            f" V_Op:{format_val_4f(v_open)}V | V_Ld:{format_val_4f(v_load)}V |"
            f" P:{format_val_2f(power)}mW"
        )
        csv_file.write(csv_line + "\n")
        csv_file.flush()

        times.append(ard_time)
        t1_data.append(t1 if t1 > -100 else float("nan"))
        t2_data.append(t2 if t2 > -100 else float("nan"))
        t3_data.append(t3 if t3 > -100 else float("nan"))
        t4_data.append(t4 if t4 > -100 else float("nan"))
        v_open_data.append(v_open if v_open > -100 else float("nan"))
        v_load_data.append(v_load if v_load > -100 else float("nan"))
        power_data.append(power if power > -100 else float("nan"))

      except ValueError:
        pass

  if len(times) > 0:
    line_t1.set_data(times, t1_data)
    line_t2.set_data(times, t2_data)
    line_t3.set_data(times, t3_data)
    line_t4.set_data(times, t4_data)
    ax_temp.relim()
    ax_temp.autoscale_view()

    line_vopen.set_data(times, v_open_data)
    line_vload.set_data(times, v_load_data)
    ax_volt.relim()
    ax_volt.autoscale_view()

    line_power.set_data(times, power_data)
    ax_power.relim()
    ax_power.autoscale_view()

    dt_now = (
        (t1_data[-1] - t2_data[-1])
        if (t1_data[-1] == t1_data[-1] and t2_data[-1] == t2_data[-1])
        else float("nan")
    )
    ax_temp.set_title(
        f"Temperature & ΔT | T1:{format_title(t1_data[-1], '°C')}"
        f" T2:{format_title(t2_data[-1], '°C')} (ΔT:{format_title(dt_now, '°C')})",
        fontsize=10,
        fontweight="bold",
    )
    ax_volt.set_title(
        f"Voltage | V_Open: {format_title(v_open_data[-1], 'V')}  V_Load:"
        f" {format_title(v_load_data[-1], 'V')}",
        fontsize=10,
        fontweight="bold",
    )
    ax_power.set_title(
        f"Generation Power | P: {format_title(power_data[-1], ' mW')}",
        fontsize=10,
        fontweight="bold",
        color="#d35400",
    )

  return line_t1, line_t2, line_t3, line_t4, line_vopen, line_vload, line_power


ani = animation.FuncAnimation(
    fig, update_plot, interval=500, cache_frame_data=False
)

try:
  plt.tight_layout()
  plt.show()
finally:
  ser.close()
  csv_file.close()
  print(f"\n✅ 實驗記錄已結束！完整數據已安全儲存至：{filename}")