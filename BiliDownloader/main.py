import tkinter as tk
from tkinter import filedialog
import yt_dlp
import os
import sys
import threading
import re


def get_base_dir():
    """获取程序自身所在目录（源码运行或 exe 打包都有效）"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


class BilibiliDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("B站视频/音频下载工具")
        self.root.geometry("550x400")
        self.root.resizable(False, False)

        # 程序所在目录（打包exe后为_MEIPASS临时目录）
        self.base_dir = get_base_dir()

        # --- 界面布局设置 ---

        # 1. 视频链接输入区
        tk.Label(root, text="视频链接：", font=("微软雅黑", 10)).place(x=20, y=30)
        self.entry_url = tk.Entry(root, width=55)
        self.entry_url.place(x=90, y=30)
        # 设置默认链接
        self.entry_url.insert(0, "https://www.bilibili.com/video/BV1PEdMBBEyA?t=24.0")

        # 2. 下载格式选择
        tk.Label(root, text="下载格式：", font=("微软雅黑", 10)).place(x=20, y=70)
        self.download_type = tk.StringVar(value="video")
        tk.Radiobutton(root, text="视频 (mp4)", variable=self.download_type, value="video", font=("微软雅黑", 9)).place(x=90, y=68)
        tk.Radiobutton(root, text="音频 (m4a)", variable=self.download_type, value="audio", font=("微软雅黑", 9)).place(x=220, y=68)

        # 3. 保存位置选择区
        tk.Label(root, text="保存位置：", font=("微软雅黑", 10)).place(x=20, y=110)
        self.entry_path = tk.Entry(root, width=45)
        self.entry_path.place(x=90, y=110)
        # 默认路径：exe同级目录下的 source 文件夹
        default_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "source")
        self.entry_path.insert(0, default_path)
        btn_select = tk.Button(
            root, text="选择文件夹", command=self.select_folder, font=("微软雅黑", 9)
        )
        btn_select.place(x=460, y=106)

        # 4. 开始下载按钮
        self.btn_download = tk.Button(
            root,
            text="开始下载",
            command=self.start_download,
            bg="#4CAF50",
            fg="white",
            font=("微软雅黑", 11),
            width=15,
        )
        self.btn_download.place(x=200, y=155)

        # 5. 进度条
        self.progress_bar = tk.Canvas(root, width=500, height=22, bg="#e0e0e0", highlightthickness=0)
        self.progress_bar.place(x=25, y=195)
        self.progress_fill = self.progress_bar.create_rectangle(0, 0, 0, 22, fill="#4CAF50", width=0)
        self.progress_label = tk.Label(root, text="", font=("微软雅黑", 8))
        self.progress_label.place(x=25, y=220)

        # 6. 状态提示标签
        self.label_status = tk.Label(
            root, text="", font=("微软雅黑", 9), wraplength=500, justify="left"
        )
        self.label_status.place(x=20, y=250)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, folder_selected)

    def update_progress(self, percent):
        """更新进度条"""
        bar_width = 500
        fill_width = int(bar_width * percent / 100)
        self.progress_bar.coords(self.progress_fill, 0, 0, fill_width, 22)
        self.progress_label.config(text=f"{percent:.1f}%")
        self.root.update_idletasks()

    def sanitize_filename(self, name):
        """清理文件名中的非法字符"""
        return re.sub(r'[\\/:\*\?"<>\|]', '_', name)

    def get_ffmpeg_path(self):
        """获取 ffmpeg.exe 路径（优先级：打包目录 > exe同级目录 > 系统PATH）"""
        # 1. 打包在 exe 内部（_MEIPASS）
        ffmpeg_internal = os.path.join(self.base_dir, "ffmpeg.exe")
        if os.path.exists(ffmpeg_internal):
            return ffmpeg_internal
        # 2. exe 同级目录
        ffmpeg_side = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "ffmpeg.exe")
        if os.path.exists(ffmpeg_side):
            return ffmpeg_side
        # 3. 找不到则让 yt-dlp 自己去 PATH 找
        return None

    def start_download(self):
        url = self.entry_url.get().strip()
        save_path = self.entry_path.get().strip()
        download_type = self.download_type.get()

        if not url or not save_path:
            self.label_status.config(text="⚠️ 提示：请先输入视频链接并选择保存路径！", fg="red")
            return

        # 重置进度条
        self.update_progress(0)

        # 禁用按钮防止重复点击
        self.btn_download.config(state=tk.DISABLED)
        self.label_status.config(text="⏳ 正在获取视频信息...", fg="blue")
        self.root.update_idletasks()

        # 开启子线程
        thread = threading.Thread(target=self.download_task, args=(url, save_path, download_type))
        thread.start()

    def download_task(self, url, save_path, download_type):
        try:
            # 确保目录存在
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # 第一步：提取视频标题，检查本地是否已存在
            self.root.after(0, lambda: self.label_status.config(text="⏳ 正在获取视频信息...", fg="blue"))

            info_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            }

            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'unknown')
                safe_title = self.sanitize_filename(title)

            # 检查文件是否已存在
            ext = "mp4" if download_type == "video" else "m4a"
            expected_file = os.path.join(save_path, f"{safe_title}.{ext}")

            if os.path.exists(expected_file):
                file_type = "视频" if download_type == "video" else "音频"
                self.root.after(0, lambda: self.label_status.config(
                    text=f"✅ 该{file_type}已存在，无需重复下载！\n{expected_file}",
                    fg="green"
                ))
                self.root.after(0, lambda: self.update_progress(100))
                self.root.after(0, lambda: self.btn_download.config(state=tk.NORMAL))
                return

            # 第二步：执行下载
            self.root.after(0, lambda: self.label_status.config(text="⏳ 正在下载...", fg="blue"))
            self.root.after(0, lambda: self.update_progress(0))

            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent_str = d.get('_percent_str', '0%').strip('%')
                    try:
                        percent = float(percent_str)
                        self.root.after(0, lambda p=percent: self.update_progress(p))
                    except ValueError:
                        pass
                elif d['status'] == 'finished':
                    self.root.after(0, lambda: self.label_status.config(text="⏳ 正在合并处理...", fg="blue"))

            # 构建 ydl_opts
            ffmpeg_path = self.get_ffmpeg_path()

            common_opts = {
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'progress_hooks': [progress_hook],
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            }

            if ffmpeg_path:
                common_opts['ffmpeg_location'] = ffmpeg_path

            if download_type == "video":
                ydl_opts = {
                    **common_opts,
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
                    'merge_output_format': 'mp4',
                }
            else:
                ydl_opts = {
                    **common_opts,
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(save_path, '%(title)s.m4a'),
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # 完成
            self.update_progress(100)
            file_type = "视频" if download_type == "video" else "音频"
            self.root.after(0, lambda: self.label_status.config(
                text=f"✅ {file_type}下载成功！\n已保存至：{save_path}",
                fg="green"
            ))

        except Exception as e:
            error_msg = str(e)
            if "Video unavailable" in error_msg:
                msg = "❌ 视频不存在或已被删除。"
            elif "Sign in to confirm your age" in error_msg:
                msg = "❌ 该视频包含成人内容，无法直接下载。"
            else:
                msg = f"❌ 下载失败：{error_msg}"

            self.root.after(0, lambda: self.label_status.config(text=msg, fg="red"))

        finally:
            self.root.after(0, lambda: self.btn_download.config(state=tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()
    app = BilibiliDownloader(root)
    root.mainloop()
