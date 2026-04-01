import tkinter as tk
from tkinter import scrolledtext
import threading
import time


class RS232Gui:
    def __init__(self, send_callback, receive_callback):
        """
        GUI nie wie nic o RS-232. Dostaje tylko dwie funkcje 'z zewnątrz':
        send_callback: co zrobić, gdy kliknę wyślij
        receive_callback: skąd brać dane do wyświetlenia
        """
        self.send_command = send_callback
        self.receive_command = receive_callback
        self.root = None
        self.running = False

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Interfejs RS-232 - Zadanie 5")

        tk.Label(self.root, text="Nadawanie (Bufor):").pack(pady=5)
        self.buffer_entry = tk.Entry(self.root, width=50)
        self.buffer_entry.pack(padx=10, pady=5)

        self.send_btn = tk.Button(self.root, text="WYŚLIJ", command=self.handle_send)
        self.send_btn.pack(pady=5)

        tk.Label(self.root, text="Odbiór:").pack(pady=5)
        self.receive_area = scrolledtext.ScrolledText(self.root, width=50, height=10, state='disabled')
        self.receive_area.pack(padx=10, pady=5)

    def handle_send(self):
        """Pobiera tekst z pola i 'wyrzuca' go do zewnętrznej metody."""
        text = self.buffer_entry.get()
        if text:
            self.send_command(text)  # Tu wywołujemy np. con.send_message
            self.buffer_entry.delete(0, tk.END)

    def run(self):
        """Uruchamia okno i wątek nasłuchiwania."""
        if self.root is None:
            self.setup_gui()

        self.running = True
        # Wątek tła, który pyta zewnętrzną metodę o nowe dane
        self.thread = threading.Thread(target=self.continuous_receive, daemon=True)
        self.thread.start()

        self.root.mainloop()

    def continuous_receive(self):
        """Pętla w tle korzystająca z zewnętrznego odbiornika."""
        while self.running:
            # Tu wywołujemy np. con.receive_message
            msg = self.receive_command()
            if msg:
                self.update_receive_area(msg)
            time.sleep(0.1)

    def update_receive_area(self, text):
        """Wpisuje odebrane dane do okna."""
        self.receive_area.configure(state='normal')
        self.receive_area.insert(tk.END, text + "\n")
        self.receive_area.configure(state='disabled')
        self.receive_area.see(tk.END)