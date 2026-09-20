"""
Instalador de Mods do Minecraft
--------------------------------
Interface minimalista: fundo preto e um unico botao de vidro fosco "Mover mods".
Ao passar o mouse, surge um brilho suave em volta do botao e ele aumenta um
pouco (animacao). Ao clicar, move todos os .jar das pastas comuns (Downloads,
Documentos, Area de Trabalho) para a pasta de mods do Minecraft:

    C:\\Users\\<USUARIO>\\AppData\\Roaming\\.minecraft\\mods

Compativel com compilacao em .exe (PyInstaller). Veja o README.md.
"""

import os
import shutil
import threading
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter, ImageTk


# ===========================================================================
# LOGICA: procurar e mover os .jar
# ===========================================================================

def get_search_folders():
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Downloads"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Documentos"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Area de Trabalho"),
        os.path.join(home, "OneDrive", "Downloads"),
        os.path.join(home, "OneDrive", "Documents"),
        os.path.join(home, "OneDrive", "Documentos"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive", "Area de Trabalho"),
    ]
    seen, folders = set(), []
    for path in candidates:
        real = os.path.normpath(path)
        if os.path.isdir(real) and real.lower() not in seen:
            seen.add(real.lower())
            folders.append(real)
    return folders


def get_mods_folder():
    appdata = os.environ.get("APPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming"
    )
    return os.path.join(appdata, ".minecraft", "mods")


def find_jar_files(folders):
    jars = []
    for folder in folders:
        for root, _dirs, files in os.walk(folder):
            if os.path.normpath(root).lower().endswith(os.path.join(".minecraft", "mods")):
                continue
            for name in files:
                if name.lower().endswith(".jar"):
                    jars.append(os.path.join(root, name))
    return jars


def unique_destination(dest_folder, filename):
    dest = os.path.join(dest_folder, filename)
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(filename)
    counter = 1
    while True:
        dest = os.path.join(dest_folder, f"{base}({counter}){ext}")
        if not os.path.exists(dest):
            return dest
        counter += 1


def move_all_jars():
    """Executa todo o processo. Retorna (movidos, erros)."""
    mods_folder = get_mods_folder()
    os.makedirs(mods_folder, exist_ok=True)
    jars = find_jar_files(get_search_folders())
    moved = errors = 0
    for src in jars:
        try:
            if os.path.normpath(os.path.dirname(src)).lower() == os.path.normpath(mods_folder).lower():
                continue
            dest = unique_destination(mods_folder, os.path.basename(src))
            shutil.move(src, dest)
            moved += 1
        except Exception:
            errors += 1
    return moved, errors


# ===========================================================================
# RENDER: botao de vidro fosco + brilho (Pillow)
# ===========================================================================

def load_font(size):
    for path in [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_glass_button(text, w, h, s=3):
    """Botao de vidro fosco (pill). Retorna imagem RGBA (w x h)."""
    W, H = w * s, h * s
    r = H // 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Mascara do formato pill
    pill = Image.new("L", (W, H), 0)
    ImageDraw.Draw(pill).rounded_rectangle([0, 0, W - 1, H - 1], radius=r, fill=255)

    # Corpo com gradiente vertical suave (vidro)
    grad = Image.new("L", (1, H), 0)
    top_a, bot_a = 70, 22
    for y in range(H):
        grad.putpixel((0, y), int(top_a + (bot_a - top_a) * y / H))
    grad = grad.resize((W, H))
    body = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    body.putalpha(ImageChops.multiply(grad, pill))
    img = Image.alpha_composite(img, body)

    # Brilho superior (highlight de vidro)
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    inset = r * 0.35
    ImageDraw.Draw(hl).rounded_rectangle(
        [inset, inset * 0.5, W - 1 - inset, int(H * 0.48)],
        radius=int(r * 0.7), fill=(255, 255, 255, 70),
    )
    hl = hl.filter(ImageFilter.GaussianBlur(radius=7 * s))
    hl.putalpha(ImageChops.multiply(hl.split()[3], pill))
    img = Image.alpha_composite(img, hl)

    # Borda clara
    border = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        [s, s, W - 1 - s, H - 1 - s], radius=r,
        outline=(255, 255, 255, 135), width=max(2, int(1.6 * s)),
    )
    img = Image.alpha_composite(img, border)

    # Texto
    draw = ImageDraw.Draw(img)
    font = load_font(int(H * 0.34))
    draw.text((W / 2, H / 2), text, font=font, fill=(238, 244, 255, 240), anchor="mm")

    return img.resize((w, h), Image.LANCZOS)


def render_glow(w, h, blur, color=(150, 205, 255), alpha=150):
    """Brilho suave (pill borrado) maior que o botao. Retorna RGBA."""
    pad = int(blur * 2.2)
    GW, GH = w + pad * 2, h + pad * 2
    g = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle(
        [pad, pad, pad + w, pad + h], radius=h // 2, fill=color + (alpha,)
    )
    return g.filter(ImageFilter.GaussianBlur(blur)), pad


def set_opacity(img, factor):
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * factor))
    return Image.merge("RGBA", (r, g, b, a))


# ===========================================================================
# INTERFACE (Tkinter + Canvas)
# ===========================================================================

WIN_W, WIN_H = 560, 380
BTN_W, BTN_H = 300, 88
GLOW_BLUR = 26
HOVER_SCALE = 1.06
FRAMES = 11  # numero de quadros da animacao (0..1)


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False

        root.title("Mover Mods")
        root.configure(bg="#000000")
        root.resizable(False, False)
        self._center_window()

        self.canvas = tk.Canvas(
            root, width=WIN_W, height=WIN_H, bg="#000000",
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        cx, cy = WIN_W // 2, WIN_H // 2

        # Pre-renderiza os quadros (botao em varias escalas + brilho em varias opacidades)
        base_glow, self.glow_pad = render_glow(BTN_W, BTN_H, GLOW_BLUR)
        self.btn_frames, self.glow_frames = [], []
        for i in range(FRAMES):
            t = i / (FRAMES - 1)
            scale = 1 + (HOVER_SCALE - 1) * t
            bw, bh = int(BTN_W * scale), int(BTN_H * scale)
            self.btn_frames.append(ImageTk.PhotoImage(render_glass_button("Mover mods", bw, bh)))
            self.glow_frames.append(ImageTk.PhotoImage(set_opacity(base_glow, t)))

        # Itens no canvas (glow atras, botao na frente), centralizados
        self.glow_item = self.canvas.create_image(cx, cy, image=self.glow_frames[0])
        self.btn_item = self.canvas.create_image(cx, cy, image=self.btn_frames[0])

        # Eventos de hover / clique
        for item in (self.btn_item, self.glow_item):
            self.canvas.tag_bind(item, "<Enter>", self.on_enter)
            self.canvas.tag_bind(item, "<Leave>", self.on_leave)
            self.canvas.tag_bind(item, "<Button-1>", self.on_click)

        self.index = 0
        self.target = 0
        self._animating = False

    def _center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - WIN_W) // 2
        y = (self.root.winfo_screenheight() - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

    # -- Animacao de hover ----------------------------------------------
    def on_enter(self, _e):
        self.canvas.config(cursor="hand2")
        self.target = FRAMES - 1
        self._start_anim()

    def on_leave(self, _e):
        self.canvas.config(cursor="")
        self.target = 0
        self._start_anim()

    def _start_anim(self):
        if not self._animating:
            self._animating = True
            self._step()

    def _step(self):
        if self.index == self.target:
            self._animating = False
            return
        self.index += 1 if self.target > self.index else -1
        self.canvas.itemconfig(self.btn_item, image=self.btn_frames[self.index])
        self.canvas.itemconfig(self.glow_item, image=self.glow_frames[self.index])
        self.root.after(12, self._step)

    # -- Clique ----------------------------------------------------------
    def on_click(self, _e):
        if self.busy:
            return
        self.busy = True
        self.canvas.config(cursor="watch")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            moved, errors = move_all_jars()
            self.root.after(0, lambda: self._done(moved, errors))
        except Exception as exc:
            self.root.after(0, lambda: self._error(str(exc)))

    def _done(self, moved, errors):
        self.busy = False
        self.canvas.config(cursor="hand2")
        if moved > 0:
            msg = f"{moved} mod(s) movido(s) para a pasta de mods!"
            if errors:
                msg += f"\n{errors} arquivo(s) nao puderam ser movidos."
            messagebox.showinfo("Concluido", msg)
        else:
            messagebox.showinfo(
                "Nada encontrado",
                "Nenhum arquivo .jar foi encontrado nas pastas comuns.",
            )

    def _error(self, message):
        self.busy = False
        self.canvas.config(cursor="hand2")
        messagebox.showerror("Erro", f"Ocorreu um erro:\n{message}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
