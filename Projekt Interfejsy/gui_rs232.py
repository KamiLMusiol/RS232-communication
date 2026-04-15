import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import time
import serial.tools.list_ports
import os

BG        = "#0d1117"
PANEL     = "#161b22"
BORDER    = "#30363d"
ACCENT    = "#00e5a0"
ACCENT2   = "#0099ff"
WARNING   = "#f0883e"
DANGER    = "#f85149"
TEXT      = "#e6edf3"
MUTED     = "#8b949e"
SUCCESS   = "#3fb950"
SEND_CLR  = "#1f6feb"


class TerminalText(scrolledtext.ScrolledText):
    def __init__(self, master, **kw):
        super().__init__(master,
            bg="#0a0e13", fg=TEXT,
            insertbackground=ACCENT,
            selectbackground=ACCENT2,
            selectforeground=BG,
            font=("Courier New", 10),
            relief="flat", bd=0,
            padx=8, pady=8,
            wrap="word",
            **kw)
        self.tag_config("sent",    foreground=ACCENT2)
        self.tag_config("recv",    foreground=ACCENT)
        self.tag_config("info",    foreground=MUTED)
        self.tag_config("warning", foreground=WARNING)
        self.tag_config("error",   foreground=DANGER)
        self.tag_config("success", foreground=SUCCESS)
        self.tag_config("ts",      foreground="#444c56")

    def append(self, text, tag="info"):
        self.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.insert("end", f"[{ts}] ", "ts")
        self.insert("end", text + "\n", tag)
        self.see("end")
        self.configure(state="disabled")


def styled_frame(parent, **kw):
    return tk.Frame(parent, bg=PANEL, **kw)

def styled_label(parent, text, size=9, color=MUTED, bold=False, **kw):
    font = ("Segoe UI", size, "bold" if bold else "normal")
    return tk.Label(parent, text=text, bg=PANEL, fg=color,
                    font=font, **kw)

def styled_entry(parent, width=16, **kw):
    e = tk.Entry(parent, width=width,
                 bg="#0a0e13", fg=TEXT,
                 insertbackground=ACCENT,
                 relief="flat", bd=0,
                 font=("Segoe UI", 9),
                 highlightthickness=1,
                 highlightbackground=BORDER,
                 highlightcolor=ACCENT,
                 **kw)
    return e

def styled_combo(parent, values, width=14, **kw):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TCombobox",
        fieldbackground="#0a0e13",
        background=PANEL,
        foreground=TEXT,
        selectbackground=ACCENT2,
        selectforeground=BG,
        bordercolor=BORDER,
        arrowcolor=MUTED,
        relief="flat")
    style.map("Dark.TCombobox",
        fieldbackground=[("readonly","#0a0e13")],
        foreground=[("readonly", TEXT)])
    c = ttk.Combobox(parent, values=values, width=width,
                     style="Dark.TCombobox", state="readonly", **kw)
    if values:
        c.current(0)
    return c

def make_btn(parent, text, cmd, color=ACCENT, width=14):
    btn = tk.Button(parent, text=text, command=cmd,
                    bg=color, fg=BG,
                    activebackground=TEXT, activeforeground=BG,
                    font=("Segoe UI", 9, "bold"),
                    relief="flat", bd=0, cursor="hand2",
                    padx=10, pady=5, width=width)
    btn.bind("<Enter>", lambda e: btn.config(bg=TEXT))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn

def divider(parent, pady=6):
    f = tk.Frame(parent, bg=BORDER, height=1)
    f.pack(fill="x", pady=pady)

def section_label(parent, text):
    styled_label(parent, text.upper(), size=8, color=ACCENT,
                 bold=True).pack(anchor="w", padx=12, pady=(10,4))


class Led(tk.Canvas):
    def __init__(self, parent, size=12):
        super().__init__(parent, width=size, height=size,
                         bg=PANEL, highlightthickness=0)
        self._size = size
        self._oval = self.create_oval(2, 2, size-2, size-2,
                                      fill="#333", outline="")
    def set(self, on, color=ACCENT):
        self.itemconfig(self._oval, fill=color if on else "#1a2030")


# main application
class RS232App:
    def __init__(self, root):
        self.root = root
        self.root.title("RS-232 Terminal")
        self.root.configure(bg=BG)
        self.root.minsize(900, 620)

        self.con = None
        self._receiving = False
        self._rx_thread  = None
        self._line_mode  = True

        self._build_layout()
        self._refresh_ports()

    def _build_layout(self):
        # title bar
        title_bar = tk.Frame(self.root, bg=BG, height=44)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="◈  RS-232 Terminal", bg=BG, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=16)
        self._status_label = tk.Label(title_bar, text="● disconnected",
                                      bg=BG, fg=DANGER,
                                      font=("Segoe UI", 9))
        self._status_label.pack(side="right", padx=16)

        panes = tk.PanedWindow(self.root, orient="horizontal",
                               bg=BG, bd=0, sashwidth=4,
                               sashrelief="flat", sashpad=0)
        panes.pack(fill="both", expand=True, padx=8, pady=(0,8))

        left  = tk.Frame(panes, bg=PANEL, width=240)
        right = tk.Frame(panes, bg=BG)
        panes.add(left,  minsize=220)
        panes.add(right, minsize=500)

        self._build_sidebar(left)
        self._build_terminal(right)

    def _build_sidebar(self, parent):
        parent.pack_propagate(False)
        canvas = tk.Canvas(parent, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=PANEL)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", on_resize)
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        self._build_port_section(inner)
        divider(inner)
        self._build_config_section(inner)
        divider(inner)
        self._build_flow_section(inner)
        divider(inner)
        self._build_lines_section(inner)
        divider(inner)
        self._build_terminator_section(inner)

    def _build_port_section(self, p):
        section_label(p, "Port")
        f = tk.Frame(p, bg=PANEL); f.pack(fill="x", padx=12, pady=4)

        styled_label(f, "PORT").grid(row=0, column=0, sticky="w")
        self._port_var = tk.StringVar()
        self._port_combo = styled_combo(f, [], width=12,
                                        textvariable=self._port_var)
        self._port_combo.grid(row=0, column=1, padx=(6,0))

        tk.Frame(p, bg=PANEL, height=4).pack()

        bf = tk.Frame(p, bg=PANEL); bf.pack(fill="x", padx=12)
        self._conn_btn = make_btn(bf, "CONNECT", self._toggle_connect,
                                  color=SUCCESS, width=10)
        self._conn_btn.pack(side="left")
        make_btn(bf, "↺", self._refresh_ports, color=BORDER, width=3
                 ).pack(side="left", padx=(6,0))

        lf = tk.Frame(p, bg=PANEL); lf.pack(fill="x", padx=12, pady=(8,4))
        for name, attr in [("CTS","_led_cts"),("DSR","_led_dsr"),
                           ("RTS","_led_rts"),("DTR","_led_dtr")]:
            col = tk.Frame(lf, bg=PANEL)
            col.pack(side="left", padx=4)
            led = Led(col); led.pack()
            setattr(self, attr, led)
            styled_label(col, name, size=7).pack()

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self._port_combo["values"] = ports if ports else ["(none)"]
        if ports: self._port_combo.current(0)

    def _toggle_connect(self):
        if self.con and self.con.connection.is_open:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        if not self.con: return
        port = self._port_var.get()
        if not port or port == "(none)":
            messagebox.showwarning("Brak portu", "Wybierz port COM.")
            return
        try:
            if self.con.connection.is_open:
                self.con.connection.close()
            self.con.connection.port = port
            self.con.connection.open()
            self._on_connected()
        except Exception as e:
            self.log(f"Błąd połączenia: {e}", "error")

    def _do_disconnect(self):
        self._receiving = False
        if self.con:
            try: self.con.close()
            except: pass
        self._on_disconnected()

    def _on_connected(self):
        self._status_label.config(text=f"● {self._port_var.get()}", fg=SUCCESS)
        self._conn_btn.config(text="DISCONNECT", bg=DANGER)
        self._conn_btn.bind("<Leave>", lambda e: self._conn_btn.config(bg=DANGER))
        self.log(f"Połączono z {self._port_var.get()}", "success")
        self._start_rx()
        self._start_led_poll()

    def _on_disconnected(self):
        self._status_label.config(text="● disconnected", fg=DANGER)
        self._conn_btn.config(text="CONNECT", bg=SUCCESS)
        self._conn_btn.bind("<Leave>", lambda e: self._conn_btn.config(bg=SUCCESS))
        self.log("Rozłączono.", "warning")
        for led in (self._led_cts, self._led_dsr,
                    self._led_rts, self._led_dtr):
            led.set(False)

    def _build_config_section(self, p):
        section_label(p, "Transmisja")
        f = tk.Frame(p, bg=PANEL); f.pack(fill="x", padx=12, pady=4)

        rows = [
            ("Baud",     "_baud_var",    ["300","600","1200","2400","4800",
                                          "9600","19200","38400","57600","115200"]),
            ("Bits",     "_bits_var",    ["7","8"]),
            ("Parzyst.", "_parity_var",  ["N – None","E – Even","O – Odd"]),
            ("Stop",     "_stop_var",    ["1","2"]),
        ]
        for i, (lbl, attr, vals) in enumerate(rows):
            styled_label(f, lbl, color=MUTED).grid(row=i, column=0,
                                                     sticky="w", pady=2)
            v = tk.StringVar(); setattr(self, attr, v)
            cb = styled_combo(f, vals, width=11, textvariable=v)
            cb.grid(row=i, column=1, padx=(6,0), pady=2)

        self._baud_var.set("9600")
        self._bits_var.set("8")
        self._parity_var.set("N – None")
        self._stop_var.set("1")

        make_btn(p, "ZASTOSUJ", self._apply_config, width=16
                 ).pack(padx=12, pady=(8,4), fill="x")

    def _apply_config(self):
        if not self.con:
            self.log("Brak połączenia SerialInterface.", "error"); return
        from enums import Parity, FlowControl
        baud  = int(self._baud_var.get())
        bits  = int(self._bits_var.get())
        par   = {"N":Parity.NONE,"E":Parity.EVEN,"O":Parity.ODD}[
                    self._parity_var.get()[0]]
        stop  = int(self._stop_var.get())
        flow  = {"NONE":FlowControl.NONE,
                 "XON/XOFF":FlowControl.XONXOFF,
                 "RTS/CTS":FlowControl.RTSCTS,
                 "DTR/DSR":FlowControl.DSRDTR}[self._flow_var.get()]
        try:
            self.con.configure_rs232(baudrate=baud, bytesize=bits,
                                     parity=par, stopbits=stop, flow=flow)
            self.log(f"Config: {baud}bps {bits}{par.name[0]}{stop} "
                     f"Flow:{flow.name}", "success")
        except Exception as e:
            self.log(f"Błąd konfiguracji: {e}", "error")

    def _build_flow_section(self, p):
        section_label(p, "Flow Control")
        f = tk.Frame(p, bg=PANEL); f.pack(fill="x", padx=12, pady=4)
        styled_label(f, "Tryb").grid(row=0, column=0, sticky="w")
        self._flow_var = tk.StringVar(value="NONE")
        styled_combo(f, ["NONE","XON/XOFF","RTS/CTS","DTR/DSR"],
                     textvariable=self._flow_var, width=11
                     ).grid(row=0, column=1, padx=(6,0))

    def _build_lines_section(self, p):
        section_label(p, "Linie ręczne (1.4)")
        f = tk.Frame(p, bg=PANEL); f.pack(fill="x", padx=12, pady=4)

        self._rts_var = tk.BooleanVar()
        self._dtr_var = tk.BooleanVar()

        for col, (lbl, var, color) in enumerate([
                ("RTS", self._rts_var, ACCENT2),
                ("DTR", self._dtr_var, WARNING)]):
            cb = tk.Checkbutton(f, text=lbl, variable=var,
                                bg=PANEL, fg=color, selectcolor="#0a0e13",
                                activebackground=PANEL, activeforeground=color,
                                font=("Segoe UI", 9, "bold"),
                                command=self._apply_lines)
            cb.grid(row=0, column=col, padx=(0,12))

        mf = tk.Frame(p, bg=PANEL); mf.pack(fill="x", padx=12, pady=(2,6))
        styled_label(mf, "CTS:").pack(side="left")
        self._cts_label = styled_label(mf, "—", color=MUTED)
        self._cts_label.pack(side="left", padx=4)
        styled_label(mf, "DSR:").pack(side="left", padx=(8,0))
        self._dsr_label = styled_label(mf, "—", color=MUTED)
        self._dsr_label.pack(side="left", padx=4)

    def _apply_lines(self):
        if not self.con or not self.con.connection.is_open: return
        self.con.set_manual_lines(rts=self._rts_var.get(),
                                  dtr=self._dtr_var.get())

    def _build_terminator_section(self, p):
        section_label(p, "Terminator (1.5)")
        f = tk.Frame(p, bg=PANEL); f.pack(fill="x", padx=12, pady=4)

        self._term_var = tk.StringVar(value="CRLF")
        for val, lbl in [("NONE","None"),("CR","CR"),
                         ("LF","LF"),("CRLF","CRLF"),("CUSTOM","Custom")]:
            rb = tk.Radiobutton(f, text=lbl, variable=self._term_var,
                                value=val, bg=PANEL, fg=TEXT,
                                selectcolor="#0a0e13",
                                activebackground=PANEL, activeforeground=ACCENT,
                                font=("Segoe UI", 9),
                                command=self._apply_terminator)
            rb.pack(side="left", padx=2)

        cf = tk.Frame(p, bg=PANEL); cf.pack(fill="x", padx=12, pady=(2,6))
        styled_label(cf, "Custom (max 2):").pack(side="left")
        self._custom_term = styled_entry(cf, width=4)
        self._custom_term.pack(side="left", padx=6)
        make_btn(cf, "SET", self._apply_terminator, width=4
                 ).pack(side="left")

    def _apply_terminator(self):
        if not self.con: return
        from enums import Terminator
        val = self._term_var.get()
        mapping = {"NONE":Terminator.NONE,"CR":Terminator.CR,
                   "LF":Terminator.LF,"CRLF":Terminator.CRLF,
                   "CUSTOM":Terminator.CUSTOM}
        custom = self._custom_term.get()
        self.con.set_terminator(mapping[val], custom=custom)
        self.log(f"Terminator: {val}" +
                 (f" = {repr(custom)}" if val=="CUSTOM" else ""), "info")

    def _build_terminal(self, parent):
        parent.configure(bg=BG)

        nb = ttk.Notebook(parent)
        style = ttk.Style()
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=PANEL, foreground=MUTED,
                        padding=[12,5], font=("Segoe UI",9))
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", TEXT)])
        nb.pack(fill="both", expand=True)

        tab1 = tk.Frame(nb, bg=BG)
        nb.add(tab1, text="  Terminal  ")
        self._build_text_tab(tab1)

        tab2 = tk.Frame(nb, bg=BG)
        nb.add(tab2, text="  Plik  ")
        self._build_file_tab(tab2)

        tab3 = tk.Frame(nb, bg=BG)
        nb.add(tab3, text="  Log  ")
        self._log_area = TerminalText(tab3, state="disabled", height=12)
        self._log_area.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_text_tab(self, parent):
        self._rx_area = TerminalText(parent, state="disabled")
        self._rx_area.pack(fill="both", expand=True, padx=4, pady=(4,0))

        bar = tk.Frame(parent, bg=PANEL); bar.pack(fill="x", padx=4, pady=4)

        self._hex_var = tk.BooleanVar()
        tk.Checkbutton(bar, text="HEX", variable=self._hex_var,
                       bg=PANEL, fg=MUTED, selectcolor="#0a0e13",
                       activebackground=PANEL, font=("Segoe UI",8)
                       ).pack(side="left", padx=4)

        make_btn(bar, "Wyczyść RX", lambda: self._clear_area(self._rx_area),
                 color=BORDER, width=11).pack(side="left", padx=4)

        sf = tk.Frame(parent, bg=PANEL, pady=6); sf.pack(fill="x", padx=4)
        sf.columnconfigure(0, weight=1)

        self._send_entry = styled_entry(sf)
        self._send_entry.config(width=40,
                                font=("Courier New", 10))
        self._send_entry.grid(row=0, column=0, sticky="ew", padx=(8,6), ipady=4)
        self._send_entry.bind("<Return>", lambda e: self._send_text())

        make_btn(sf, "WYŚLIJ ↑", self._send_text, color=SEND_CLR, width=10
                 ).grid(row=0, column=1, padx=(0,8))

    def _send_text(self):
        if not self.con or not self.con.connection.is_open:
            self.log("Brak aktywnego połączenia.", "error"); return
        text = self._send_entry.get()
        if not text: return
        try:
            self.con.send_message(text)
            self._rx_area.append(f"TX ▶ {text}", "sent")
            self._send_entry.delete(0, "end")
        except Exception as e:
            self.log(f"Błąd wysyłania: {e}", "error")

    def _clear_area(self, area):
        area.configure(state="normal")
        area.delete("1.0", "end")
        area.configure(state="disabled")

    def _build_file_tab(self, parent):
        outer = tk.Frame(parent, bg=BG); outer.pack(fill="both", expand=True,
                                                     padx=16, pady=16)

        sf = tk.LabelFrame(outer, text="  Wyślij plik  ",
                           bg=PANEL, fg=ACCENT,
                           font=("Segoe UI",9,"bold"),
                           bd=1, relief="solid",
                           highlightbackground=BORDER)
        sf.pack(fill="x", pady=(0,16))

        row1 = tk.Frame(sf, bg=PANEL); row1.pack(fill="x", padx=12, pady=8)
        self._send_path = styled_entry(row1, width=36)
        self._send_path.pack(side="left", padx=(0,8), ipady=3)
        make_btn(row1, "Przeglądaj…", self._browse_send, color=BORDER, width=10
                 ).pack(side="left")
        make_btn(sf, "WYŚLIJ PLIK ↑", self._send_file, color=SEND_CLR, width=16
                 ).pack(padx=12, pady=(0,12), anchor="w")

        rf = tk.LabelFrame(outer, text="  Odbierz do pliku  ",
                           bg=PANEL, fg=ACCENT,
                           font=("Segoe UI",9,"bold"),
                           bd=1, relief="solid",
                           highlightbackground=BORDER)
        rf.pack(fill="x")

        row2 = tk.Frame(rf, bg=PANEL); row2.pack(fill="x", padx=12, pady=8)
        self._recv_path = styled_entry(row2, width=36)
        self._recv_path.pack(side="left", padx=(0,8), ipady=3)
        make_btn(row2, "Przeglądaj…", self._browse_recv, color=BORDER, width=10
                 ).pack(side="left")
        make_btn(rf, "ODBIERZ DO PLIKU ↓", self._recv_file, color=ACCENT, width=18
                 ).pack(padx=12, pady=(0,12), anchor="w")

        self._file_status = styled_label(outer, "", color=MUTED, size=9)
        self._file_status.pack(anchor="w", pady=8)

    def _browse_send(self):
        path = filedialog.askopenfilename(filetypes=[("Pliki tekstowe","*.txt"),
                                                      ("Wszystkie","*.*")])
        if path:
            self._send_path.delete(0,"end")
            self._send_path.insert(0, path)

    def _browse_recv(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Pliki tekstowe","*.txt")])
        if path:
            self._recv_path.delete(0,"end")
            self._recv_path.insert(0, path)

    def _send_file(self):
        path = self._send_path.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Błąd", "Podaj prawidłową ścieżkę pliku."); return
        if not self.con or not self.con.connection.is_open:
            self.log("Brak aktywnego połączenia.", "error"); return
        def task():
            self._file_status.config(text="⏳ Wysyłanie…", fg=WARNING)
            try:
                self.con.send_file(path)
                self._file_status.config(text="✓ Plik wysłany.", fg=SUCCESS)
                self.log(f"Wysłano plik: {path}", "success")
            except Exception as e:
                self._file_status.config(text=f"✗ {e}", fg=DANGER)
                self.log(f"Błąd wysyłania pliku: {e}", "error")
        threading.Thread(target=task, daemon=True).start()

    def _recv_file(self):
        path = self._recv_path.get()
        if not path:
            messagebox.showwarning("Błąd", "Podaj ścieżkę zapisu."); return
        if not self.con or not self.con.connection.is_open:
            self.log("Brak aktywnego połączenia.", "error"); return
        def task():
            self._file_status.config(text="⏳ Oczekiwanie na dane…", fg=WARNING)
            try:
                self.con.receive_to_file(path)
                self._file_status.config(text=f"✓ Zapisano: {path}", fg=SUCCESS)
                self.log(f"Odebrano plik: {path}", "success")
            except Exception as e:
                self._file_status.config(text=f"✗ {e}", fg=DANGER)
                self.log(f"Błąd odbioru pliku: {e}", "error")
        threading.Thread(target=task, daemon=True).start()

    def _start_rx(self):
        self._receiving = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()

    def _rx_loop(self):
        while self._receiving:
            try:
                if self.con and self.con.connection.is_open:
                    msg = self.con.receive_message()
                    if msg:
                        display = msg.encode().hex(" ") if self._hex_var.get() \
                                  else msg.strip()
                        self._rx_area.after(0,
                            lambda m=display: self._rx_area.append(
                                f"RX ◀ {m}", "recv"))
            except Exception:
                pass
            time.sleep(0.05)

    def _start_led_poll(self):
        self._poll_signals()

    def _poll_signals(self):
        if not (self.con and self.con.connection.is_open):
            return
        try:
            s = self.con.get_input_monitoring()
            cts = s.get("CTS", False)
            dsr = s.get("DSR", False)
            self._led_cts.set(cts,  ACCENT2)
            self._led_dsr.set(dsr,  ACCENT)
            self._led_rts.set(self.con.connection.rts, WARNING)
            self._led_dtr.set(self.con.connection.dtr, SUCCESS)
            self._cts_label.config(text="ON" if cts else "OFF",
                                   fg=ACCENT2 if cts else MUTED)
            self._dsr_label.config(text="ON" if dsr else "OFF",
                                   fg=ACCENT  if dsr else MUTED)
        except Exception:
            pass
        self.root.after(500, self._poll_signals)

    def log(self, msg, tag="info"):
        self._log_area.after(0, lambda: self._log_area.append(msg, tag))

    def set_interface(self, serial_interface):
        """Attach a SerialInterface instance."""
        self.con = serial_interface

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._receiving = False
        if self.con:
            try: self.con.close()
            except: pass
        self.root.destroy()


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))

    root = tk.Tk()
    app = RS232App(root)

    try:
        from class_connection import SerialInterface
        con = SerialInterface()
        app.set_interface(con)
    except Exception as e:
        print(f"[WARN] SerialInterface nie załadowany: {e}")

    app.run()