import time
from collections import deque
import psutil
import asciichartpy as acp
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
import threading
import platform
import os

def make_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="upper"),
        Layout(name="lower")
    )
    layout["lower"].split_row(
        Layout(name="middle_left"),
        Layout(name="middle_right")
    )
    layout["middle_right"].split_column(
        Layout(name="top_inner"),
        Layout(name="bottom_inner")
    )
    layout["upper"].size = 5
    layout["upper"].split_row(
        Layout(name="upper_left"),
        Layout(name="upper_right")
    )
    layout["bottom_inner"].split_row(
        Layout(name="bottom_inner_left"),
        Layout(name="bottom_inner_right")
    )
    layout["upper_left"].ratio = 3
    layout["upper_right"].ratio = 1
    layout["bottom_inner_left"].ratio = 1
    layout["bottom_inner_right"].ratio = 1
    layout["upper_left"].update(Panel("", style="white"))
    layout["upper_right"].update(Panel("", style="white"))
    layout["middle_left"].update(Panel("", style="white"))
    layout["top_inner"].update(Panel("", style="white"))
    layout["bottom_inner_left"].update(Panel("", style="white"))
    layout["bottom_inner_right"].update(Panel("", style="white"))
    return layout

def cpu_usage(layout, bytes_sent_data, bytes_recv_data, transfer_rate):
    with Live(layout, refresh_per_second=10) as live:
        while True:
            cpu_usage_value = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count(logical=True)
            cpu_cores = psutil.cpu_count(logical=False) 
            cpu_freq = psutil.cpu_freq().current
            cpu_time = psutil.cpu_times().user
            
            cpu_info = (
                f"CPU Count: {cpu_count} | Frequency: {cpu_freq / 1000:.2f} GHz\n"
                "------------------------------------\n"
                f"CPU Cores: {cpu_cores} | Uptime: {round(cpu_time / 3600, 3)} hrs"
            )           

            graph = create_cpu_graph(90, cpu_usage_value)
            full_display = f"\n[cyan]{graph}[/cyan]  CPU Usage: {cpu_usage_value}%"
            layout["upper_left"].update(Panel(full_display, title="CPU Usage", style="white"))
            layout["upper_right"].update(Panel(cpu_info, title="CPU Info", style="white"))

            disk_space(layout)
            update_network_speed(bytes_sent_data, bytes_recv_data, layout, transfer_rate)
            system_specs(layout)
            other_specs(layout)

            live.update(layout)
            time.sleep(0.1)

def disk_space(layout):
    partition = 'C:\\'
    usage = psutil.disk_usage(partition)

    graph1 = create_ds_graph(75, usage.used, usage.total)
    graph2 = create_ds_graph(75, usage.free, usage.total)

    total_usage = f"-- Used: {usage.used / (1024**3):.2f} / {usage.total / (1024**3):.2f} GB {'-' * 48} \n\n[magenta]{graph1}[/magenta]\n\n" \
                  f"-- Free: {usage.free / (1024**3):.2f} / {usage.total / (1024**3):.2f} GB {'-' * 49} \n\n[magenta]{graph2}[/magenta]\n" 

    layout["top_inner"].update(Panel(total_usage, title='Disk Space', style='white'))

def create_ds_graph(max_width, used, total):
    percent_used = (used / total) * 100
    filled_length = int(max_width * percent_used // 100) 
    bar = '█' * filled_length + '-' * (max_width - filled_length) 
    return f"|{bar}|"

def create_cpu_graph(max_width, value):
    filled_length = int(max_width * value // 100)
    bar = '| ' + '█' * filled_length + '-' * (max_width - filled_length) + ' |'
    return bar

def plot_network_speed(data_sent, data_recv):
    plot_sent = acp.plot(data_sent, {'height': 4})
    plot_recv = acp.plot(data_recv, {'height': 4})
    combined_plot = f"[green]Upload (kB/s):[/green]\n{plot_sent}\n\n[blue]Download (kB/s):[/blue]\n{plot_recv}"
    return combined_plot

def calc_ul_dl(rate, dt=10, interface="WiFi"):
    t0 = time.time()
    counter = psutil.net_io_counters(pernic=True)[interface]
    tot = (counter.bytes_sent, counter.bytes_recv)

    while True:
        last_tot = tot
        time.sleep(dt)
        counter = psutil.net_io_counters(pernic=True)[interface]
        t1 = time.time()
        tot = (counter.bytes_sent, counter.bytes_recv)
        ul, dl = [
            (now - last) / (t1 - t0) / 1000.0
            for now, last in zip(tot, last_tot)
        ]
        rate.append((ul, dl))
        t0 = time.time()

def update_network_speed(bytes_sent_data, bytes_recv_data, layout, transfer_rate):
    try:
        ul, dl = transfer_rate[-1]
    except IndexError:
        ul, dl = 0, 0

    bytes_sent_data.append(ul)
    bytes_recv_data.append(dl)

    if len(bytes_sent_data) > 50:
        bytes_sent_data.popleft()
    if len(bytes_recv_data) > 50:
        bytes_recv_data.popleft()

    combined_plot = plot_network_speed(bytes_sent_data, bytes_recv_data)
    layout["middle_left"].update(Panel(combined_plot, title="Network Speed", style="white"))

def system_specs(layout):
    system_info = {
        'OS': platform.system(),
        'Node': platform.node(),
        'Version': platform.version(),
        'Architecture': platform.architecture()[0],
        'Machine': platform.machine(),
        'Python Version': platform.python_version(),
    }
    
    specs = "\n".join(
        f"{key:<20}: {value}" for key, value in system_info.items()
    )

    layout["bottom_inner_left"].update(Panel(specs, title="System Specifications", style="white"))

def other_specs(layout):
    battery = psutil.sensors_battery()
    status = "Charging" if battery.power_plugged else "Not Charging"

    boot_time = psutil.boot_time()  
    boot_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time))

    load1, load5, load15 = psutil.getloadavg()
    memory = psutil.virtual_memory()

    max_label_width = 20

    other_specs = (
        f"{'Battery':<{max_label_width-2}}: {battery.percent}% ({status})\n"
        f"{'Last Boot Time':<{max_label_width-2}}: {boot_time_str}\n"
        f"{'Memory Usage':<{max_label_width-2}}: {memory.percent}%\n"
        f"{'Load Average(1m)':<{max_label_width-2}}: {load1:.2f}\n"
        f"{'Load Average(5m)':<{max_label_width-2}}: {load5:.2f}\n"
        f"{'Load Average(15m)':<{max_label_width-2}}: {load15:.2f}"
    )

    layout["bottom_inner_right"].update(Panel(other_specs, title="Other Specifications", style="white"))

layout = make_layout()
bytes_sent_data = deque(maxlen=50)  
bytes_recv_data = deque(maxlen=50)  
transfer_rate = deque(maxlen=1)

t = threading.Thread(target=calc_ul_dl, args=(transfer_rate,))
t.daemon = True
t.start()

cpu_usage(layout, bytes_sent_data, bytes_recv_data, transfer_rate)



