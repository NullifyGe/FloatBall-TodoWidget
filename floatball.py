import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import json
import os
from datetime import datetime, timedelta
import winreg
import sys
from PIL import Image, ImageTk, ImageDraw

# ===================== 配置项 =====================
CONFIG_PATH = "floatball_config.json"
TASK_PATH = "floatball_tasks.json"
SIZE = 64
WINDOW_PADDING = 10
DEFAULT_CONFIG = {
    "ball_color": "#4285F4",
    "image": None,
    "auto_start": False
}
TRANS_KEY = "#000001"

class FloatBall:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", TRANS_KEY)
        self.root.geometry(f"{SIZE}x{SIZE}")
        self.root.resizable(False, False)

        self.dragging = False
        self.off_x = 0
        self.off_y = 0

        self.config = self.load_config()
        self.task_list_data = self.load_tasks()

        self.canvas = tk.Canvas(root, width=SIZE, height=SIZE, bg=TRANS_KEY, highlightthickness=0)
        self.canvas.pack()

        self.ball_color = self.config.get("ball_color", "#4285F4")
        self.ball_img = None
        self.red_dot = None
        self.panel_win = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.render_ball()
        self.check_overdue_remind()
        self.low_power_loop()

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False)
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_CONFIG.copy()

    def save_config(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False)

    def load_tasks(self):
        if not os.path.exists(TASK_PATH):
            with open(TASK_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
            return []
        try:
            with open(TASK_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def save_tasks(self):
        with open(TASK_PATH, "w", encoding="utf-8") as f:
            json.dump(self.task_list_data, f, ensure_ascii=False)

    def render_ball(self):
        self.canvas.delete("all")
        self.ball_img = None

        img_path = self.config.get("image")
        if img_path and os.path.isfile(img_path):
            try:
                img = Image.open(img_path).convert("RGBA")
                w, h = img.size
                crop_side = min(w, h)
                left = (w - crop_side) // 2
                top = (h - crop_side) // 2
                img = img.crop((left, top, left + crop_side, top + crop_side))
                img = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)

                mask = Image.new("L", (SIZE, SIZE), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, SIZE, SIZE), fill=255)
                img.putalpha(mask)

                self.ball_img = ImageTk.PhotoImage(img)
                self.canvas.create_image(SIZE//2, SIZE//2, image=self.ball_img)
                return
            except:
                pass

        self.canvas.create_oval(0, 0, SIZE, SIZE, fill=self.ball_color, outline="")

    def check_overdue_remind(self):
        has_expire = False
        now = datetime.now()
        for item in self.task_list_data:
            try:
                dl = datetime.strptime(item["deadline"], "%Y-%m-%d %H:%M")
                if dl - now < timedelta(hours=24):
                    has_expire = True
                    break
            except:
                continue
        if has_expire:
            self.red_dot = self.canvas.create_oval(SIZE-18, 4, SIZE-2, 16, fill="#ff3333", outline="")
        else:
            if self.red_dot:
                self.canvas.delete(self.red_dot)
                self.red_dot = None

    def low_power_loop(self):
        self.check_overdue_remind()
        self.root.after(180000, self.low_power_loop)

    def on_press(self, e):
        self.dragging = False
        self.off_x = e.x
        self.off_y = e.y

    def on_move(self, e):
        # 标记正在拖动
        self.dragging = True
        
        # 拖动时自动关闭窗口
        if self.panel_win:
            self.close_panel()
            
        # 执行拖动移动
        x = self.root.winfo_x() + (e.x - self.off_x)
        y = self.root.winfo_y() + (e.y - self.off_y)
        self.root.geometry(f"+{x}+{y}")

    def on_release(self, e):
        # 拖动结束 → 不打开窗口
        if self.dragging:
            self.dragging = False
            return
        
        # 只有没拖动，才是点击 → 打开/关闭窗口
        self.toggle_panel()

    def toggle_panel(self):
        if self.panel_win:
            self.close_panel()
        else:
            self.show_panel()

    def show_panel(self):
        px = self.root.winfo_x()
        py = self.root.winfo_y()
        panel_w, panel_h = 320, 440
        panel_y = py + SIZE + WINDOW_PADDING

        self.panel_win = tk.Toplevel(self.root)
        self.panel_win.overrideredirect(True)
        self.panel_win.wm_attributes("-topmost", True)
        self.panel_win.geometry(f"{panel_w}x{panel_h}+{px}+{panel_y}")
        self.panel_win.configure(bg="#f0f0f0")

        head = tk.Frame(self.panel_win, bg="#4285F4", height=28)
        head.pack(fill="x")
        tk.Label(head, text="功能面板", fg="white", bg="#4285F4", font=("微软雅黑",10)).pack(side="left", padx=8)
        tk.Button(head, text="×", fg="white", bg="#4285F4", bd=0, command=self.close_panel).pack(side="right", padx=6)

        tab = ttk.Notebook(self.panel_win)
        tab_todo = tk.Frame(tab, bg="white")
        tab_set = tk.Frame(tab, bg="white")
        tab.add(tab_todo, text="待办")
        tab.add(tab_set, text="设置")
        tab.pack(fill="both", expand=True)

        self.task_box = tk.Listbox(tab_todo, font=("微软雅黑",10))
        self.task_box.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_task_box()

        btn_bar = tk.Frame(tab_todo, bg="white")
        btn_bar.pack(fill="x")
        tk.Button(btn_bar, text="新增任务", command=self.add_task).pack(side="left", padx=4)
        tk.Button(btn_bar, text="标记完成", command=self.done_task).pack(side="left")

        tk.Button(tab_set, text="更换圆形图片", command=self.select_img).pack(pady=4)
        tk.Button(tab_set, text="恢复默认球形", command=self.reset_ball).pack(pady=4)
        tk.Button(tab_set, text="更换颜色", command=self.select_color).pack(pady=4)

        self.autostart_var = tk.BooleanVar(value=self.config.get("auto_start", False))
        tk.Checkbutton(tab_set, text="开机自启", variable=self.autostart_var, command=self.save_autostart).pack(pady=2)
        tk.Button(tab_set, text="退出程序", command=self.root.quit, fg="red").pack(pady=8)

    def close_panel(self):
        if self.panel_win:
            self.panel_win.destroy()
            self.panel_win = None

    def refresh_task_box(self):
        self.task_box.delete(0, tk.END)
        sort_list = []
        for item in self.task_list_data:
            try:
                t = datetime.strptime(item["deadline"], "%Y-%m-%d %H:%M")
                sort_list.append((t, item))
            except:
                continue
        sort_list.sort(key=lambda x:x[0])
        for _, item in sort_list:
            self.task_box.insert(tk.END, f"{item['title']} | {item['deadline']}")

    def add_task(self):
        win = tk.Toplevel()
        win.title("新增任务")
        tk.Label(win, text="内容：").grid(row=0,column=0,padx=5,pady=5)
        e_title = tk.Entry(win, width=25)
        e_title.grid(row=0,column=1)
        tk.Label(win, text="截止：").grid(row=1,column=0,padx=5,pady=5)
        e_time = tk.Entry(win, width=25)
        e_time.grid(row=1,column=1)
        e_time.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))

        def confirm():
            t = e_title.get().strip()
            d = e_time.get().strip()
            if t and d:
                self.task_list_data.append({"title":t, "deadline":d})
                self.save_tasks()
                self.refresh_task_box()
                self.check_overdue_remind()
            win.destroy()
        tk.Button(win, text="确定", command=confirm).grid(row=2,column=0,columnspan=2,pady=6)

    def done_task(self):
        idx = self.task_box.curselection()
        if not idx:
            return
        if messagebox.askyesno("提示", "确定标记完成并删除？"):
            self.task_list_data.pop(idx[0])
            self.save_tasks()
            self.refresh_task_box()
            self.check_overdue_remind()

    def select_img(self):
        p = filedialog.askopenfilename(filetypes=[("图片","*.png;*.jpg;*.jpeg")])
        if p:
            self.config["image"] = p
            self.save_config()
            self.render_ball()

    def reset_ball(self):
        self.config["image"] = None
        self.save_config()
        self.render_ball()
        messagebox.showinfo("提示", "已恢复默认球形")

    def select_color(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.ball_color = c
            self.config["ball_color"] = c
            self.save_config()
            self.render_ball()

    def save_autostart(self):
        val = self.autostart_var.get()
        self.config["auto_start"] = val
        self.save_config()
        app_path = os.path.abspath(sys.argv[0])
        run_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_WRITE)
        try:
            if val:
                winreg.SetValueEx(run_key, "FloatBallWidget", 0, winreg.REG_SZ, app_path)
            else:
                winreg.DeleteValue(run_key, "FloatBallWidget")
        except:
            pass
        winreg.CloseKey(run_key)

if __name__ == "__main__":
    root = tk.Tk()
    app = FloatBall(root)
    root.mainloop()