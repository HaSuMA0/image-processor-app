import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from tkinter import ttk
from PIL import Image
from collections import Counter
import requests
import os
import sys


class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.source_files = []
        self.output_path_var = tk.StringVar()
        self.thread = None
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.pause_event.set()  # 初始为非暂停状态

        self.setup_ui()  # 初始化界面

    def setup_ui(self):
        """设置主界面"""
        self.root.title("图片背景去除工具")
        self.root.geometry("600x600")

        # 拖拽区域
        frame_drag = ttk.LabelFrame(self.root, text="拖拽区域", padding=(10, 10))
        frame_drag.pack(fill="both", expand=True, padx=10, pady=10)

        self.drag_label = tk.Label(
            frame_drag,
            text="将图片或文件夹拖拽到这里",
            bg="lightgray",
            width=60,
            height=10,
            relief="groove",
        )
        self.drag_label.pack(fill="both", expand=True, padx=10, pady=10)
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.handle_drop)

        # 输出设置
        frame_output = ttk.LabelFrame(self.root, text="输出设置", padding=(10, 10))
        frame_output.pack(fill="x", padx=10, pady=10)

        tk.Label(frame_output, text="选择输出文件夹:").pack(anchor="w")
        tk.Entry(frame_output, textvariable=self.output_path_var, width=50).pack(fill="x", padx=5, pady=5)
        ttk.Button(frame_output, text="选择文件夹", command=self.select_output_folder).pack(pady=5)

        # 状态和进度条
        self.status_label = tk.Label(self.root, text="等待处理...", relief="sunken", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=10)

        self.progress_bar = ttk.Progressbar(self.root, length=400, mode="determinate")
        self.progress_bar.pack(fill="x", padx=10, pady=10)

        # 控制按钮
        frame_controls = ttk.LabelFrame(self.root, text="操作", padding=(10, 10))
        frame_controls.pack(fill="x", padx=10, pady=10)

        ttk.Button(frame_controls, text="开始处理", command=self.start_processing).pack(side="left", padx=5)
        self.pause_button = ttk.Button(frame_controls, text="暂停", command=self.pause_processing, state="disabled")
        self.pause_button.pack(side="left", padx=5)
        self.resume_button = ttk.Button(frame_controls, text="继续", command=self.resume_processing, state="disabled")
        self.resume_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(frame_controls, text="停止", command=self.stop_processing, state="disabled")
        self.stop_button.pack(side="left", padx=5)

    def handle_drop(self, event):
        """处理拖拽文件"""
        dropped_files = self.root.tk.splitlist(event.data)
        self.source_files = []
        for item in dropped_files:
            if os.path.isdir(item):
                for root_dir, _, files in os.walk(item):
                    for file in files:
                        if file.lower().endswith((".png", ".jpg", ".jpeg")):
                            self.source_files.append(os.path.join(root_dir, file))
            elif os.path.isfile(item):
                if item.lower().endswith((".png", ".jpg", ".jpeg")):
                    self.source_files.append(item)

        # 更新拖拽区域的文本显示
        if self.source_files:
            self.drag_label.config(
                text=f"已加载 {len(self.source_files)} 个图片文件"
            )
        else:
            self.drag_label.config(
                text="没有找到有效的图片文件，请拖入有效文件！"
            )

    def select_output_folder(self):
        """选择输出文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.output_path_var.set(folder)

    def start_processing(self):
        """启动处理"""
        if not self.source_files:
            self.drag_label.config(text="请先拖拽文件到此处！")
            return

        output_folder = self.output_path_var.get()
        if not output_folder:
            messagebox.showerror("错误", "请先选择输出文件夹！")
            return

        self.stop_event.clear()
        self.pause_event.set()

        self.progress_bar["value"] = 0
        self.status_label.config(text="正在处理中，请稍候...")

        self.pause_button.config(state="normal")
        self.resume_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self.thread = threading.Thread(target=self.process_images, args=(self.source_files, output_folder))
        self.thread.daemon = True
        self.thread.start()

    def process_images(self, file_paths, output_folder):
        """处理图片"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        total_files = len(file_paths)
        for index, file_path in enumerate(file_paths, start=1):
            if self.stop_event.is_set():
                break

            self.pause_event.wait()

            if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                file_name = os.path.basename(file_path)
                output_path = os.path.join(output_folder, file_name)

                image = Image.open(file_path)
                bg_color = self.detect_background_color(image)
                bg_color_ranges = self.create_color_range(bg_color, tolerance=30)
                self.remove_background(file_path, output_path, bg_color_ranges)

            # 更新进度
            self.progress_bar["value"] = (index / total_files) * 100
            self.progress_bar.update_idletasks()
            self.status_label.config(text=f"已处理 {index}/{total_files} 张图片")

        self.status_label.config(text="处理完成！")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
        self.stop_button.config(state="disabled")

    def pause_processing(self):
        """暂停处理"""
        self.pause_event.clear()
        self.status_label.config(text="处理已暂停")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="normal")

    def resume_processing(self):
        """继续处理"""
        self.pause_event.set()
        self.status_label.config(text="正在处理中，请稍候...")
        self.pause_button.config(state="normal")
        self.resume_button.config(state="disabled")

    def stop_processing(self):
        """停止处理"""
        self.stop_event.set()
        self.pause_event.set()
        self.status_label.config(text="处理已停止")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
        self.stop_button.config(state="disabled")

    @staticmethod
    def detect_background_color(image):
        """检测图片背景色"""
        image = image.convert("RGB")
        colors = image.getcolors(image.size[0] * image.size[1])
        if colors:
            most_common_color = Counter(dict(colors)).most_common(1)[0][0]
            return most_common_color
        else:
            return (255, 255, 255)

    @staticmethod
    def create_color_range(bg_color, tolerance=30):
        """创建背景色容差范围"""
        if isinstance(bg_color, tuple) and len(bg_color) == 3:
            return [(max(0, c - tolerance), min(255, c + tolerance)) for c in bg_color]
        else:
            return [(200, 255), (200, 255), (200, 255)]

    @staticmethod
    def remove_background(image_path, output_path, bg_color_ranges):
        """移除图片背景"""
        image = Image.open(image_path).convert("RGBA")
        datas = image.getdata()
        new_data = []

        for item in datas:
            is_bg = all(bg_range[0] <= channel <= bg_range[1] for channel, bg_range in zip(item[:3], bg_color_ranges))
            if is_bg:
                new_data.append((255, 255, 255, 0))  # 设置为透明
            else:
                new_data.append(item)

        image.putdata(new_data)
        image.save(output_path, "PNG")


def check_for_updates(current_version="1.0"):
    """检查版本更新"""
    try:
        url = "https://your-github-pages-url/version.json"  # 替换为你的 version.json 地址
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        latest_version = data["version"]
        download_url = data["url"]

        if latest_version > current_version:
            if messagebox.askyesno("更新提示", f"发现新版本 {latest_version}，是否立即下载更新？"):
                download_and_replace(download_url)
    except Exception as e:
        messagebox.showerror("更新检查失败", f"无法检查更新：{e}")


def download_and_replace(url):
    """下载并替换当前版本"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        new_file = "app-new.exe"
        with open(new_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        current_file = sys.argv[0]
        os.rename(current_file, current_file + ".bak")
        os.rename(new_file, current_file)
        messagebox.showinfo("更新成功", "新版本已安装，请重新启动应用。")
        sys.exit()
    except Exception as e:
        messagebox.showerror("更新失败", f"下载更新失败：{e}")


if __name__ == "__main__":
    # 检查更新
    check_for_updates(current_version="1.0")

    root = TkinterDnD.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
