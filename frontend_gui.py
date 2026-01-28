import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from ledger_api import LedgerAPI
except ImportError as e:
    messagebox.showerror("Critical Error", f"Could not find 'ledger_api.py'.\n\nError: {e}")
    sys.exit(1)

COLORS = {
    "brand": "#15803D",
    "brand_dark": "#14532D", 
    "light_green": "#22C55E",
    "bg": "#F8FAFC",
    "sidebar": "#FFFFFF",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "border": "#E5E7EB",
    "card_bg": "#FFFFFF",
    "danger": "#DC2626",
}

FONT_H1 = ("Segoe UI", 24, "bold")
FONT_H2 = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")

class RoundedCard(tk.Canvas):
    def __init__(self, parent, width=300, height=150, radius=20, color="#ffffff", **kwargs):
        super().__init__(parent, width=width, height=height, bg=COLORS["bg"], highlightthickness=0, **kwargs)
        self.radius = radius
        self.color = color
        self.width = width
        self.height = height
        self._draw()

    def _draw(self):
        self.delete("all")
        r = self.radius
        w = self.width
        h = self.height
        self.create_polygon(
            r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0,
            smooth=True, fill=self.color, outline=COLORS["border"], width=1
        )

class ActivityChart(tk.Canvas):
    def __init__(self, parent, width=400, height=150, data=None):
        super().__init__(parent, width=width, height=height, bg=COLORS["card_bg"], highlightthickness=0)
        self.data = data or [10, 40, 30, 60, 50, 90, 80]
        self.width = width
        self.height = height
        self.draw_chart()

    def draw_chart(self):
        self.delete("all")
        if not self.data: return
        
        min_val, max_val = min(self.data), max(self.data)
        if min_val == max_val: max_val += 1
        
        points = []
        padding = 20
        chart_w = self.width - (padding * 2)
        chart_h = self.height - (padding * 2)
        step_x = chart_w / (len(self.data) - 1)
        
        for i, val in enumerate(self.data):
            x = padding + (i * step_x)
            normalized_h = (val - min_val) / (max_val - min_val)
            y = (self.height - padding) - (normalized_h * chart_h)
            points.append((x, y))

        self.create_line(points, fill=COLORS["brand"], width=3, smooth=True, capstyle="round")
        
        for x, y in points:
            self.create_oval(x-4, y-4, x+4, y+4, fill="white", outline=COLORS["brand"], width=2)

class SVWENApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("SVWEN - Crypto Dashboard") 
        self.geometry("1100x750")
        self.configure(bg=COLORS["bg"])
        
        self.center_window()
        
        self.api = LedgerAPI()
        
        self.token = None
        self.username = None
        
        self.setup_styles()
        self.show_login()

    def center_window(self):
        self.update_idletasks()
        w = 1100
        h = 750
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text_primary"], font=FONT_BODY)
        
        style.configure("TEntry", fieldbackground=COLORS["bg"], bordercolor=COLORS["border"])
        
        style.configure("Primary.TButton", background=COLORS["brand"], foreground="white", borderwidth=0, font=FONT_BOLD)
        style.map("Primary.TButton", background=[('active', COLORS["brand_dark"])])
        
        style.configure("Danger.TButton", background=COLORS["danger"], foreground="white", borderwidth=0, font=FONT_BOLD)
        style.map("Danger.TButton", background=[('active', "#b91c1c")])

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_screen()
        
        frame = ttk.Frame(self)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(frame, text="SVWEN", font=("Segoe UI", 36, "bold"), fg=COLORS["brand"], bg=COLORS["bg"]).pack(pady=(0, 10))
        tk.Label(frame, text="Private Crypto Dashboard", font=("Segoe UI", 12), fg=COLORS["text_secondary"], bg=COLORS["bg"]).pack(pady=(0, 40))

        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        tk.Label(frame, text="Username", bg=COLORS["bg"], fg=COLORS["text_primary"], font=FONT_BOLD).pack(anchor="w")
        ttk.Entry(frame, textvariable=self.user_var, width=35, font=("Segoe UI", 11)).pack(pady=(5, 15))
        
        tk.Label(frame, text="Password", bg=COLORS["bg"], fg=COLORS["text_primary"], font=FONT_BOLD).pack(anchor="w")
        ttk.Entry(frame, textvariable=self.pass_var, show="•", width=35, font=("Segoe UI", 11)).pack(pady=(5, 25))
        
        btn = tk.Button(frame, text="Sign In", bg=COLORS["brand"], fg="white", font=FONT_BOLD, 
                        relief="flat", pady=10, command=self.process_login)
        btn.pack(fill="x")

    def process_login(self):
        u = self.user_var.get()
        p = self.pass_var.get()
        
        res = self.api.login(u, p)
        if res.get("ok"):
            self.token = res["token"]
            self.username = res["username"]
            self.show_dashboard_layout()
        else:
            messagebox.showerror("Login Failed", res.get("error", "Invalid Credentials"))

    def show_dashboard_layout(self):
        self.clear_screen()
        
        # Enhanced header with better spacing and styling
        header = tk.Frame(self, bg=COLORS["brand"], height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Left side - Logo and title
        left_header = tk.Frame(header, bg=COLORS["brand"])
        left_header.pack(side="left", fill="both", expand=True, padx=25, pady=20)
        
        logo_text = " SVWEN"
        tk.Label(left_header, text=logo_text, font=("Segoe UI", 26, "bold"), 
                 fg="white", bg=COLORS["brand"]).pack(side="left", padx=(0, 12))
        
        tk.Label(left_header, text="Crypto Dashboard", font=("Segoe UI", 16, "bold"), 
                 fg="white", bg=COLORS["brand"]).pack(side="left", padx=(12, 0))
        
        # Right side - User info with better styling
        user_frame = tk.Frame(header, bg=COLORS["brand"])
        user_frame.pack(side="right", padx=30, pady=25)
        
        user_label = tk.Label(user_frame, text=f"👤 {self.username}", 
                            font=("Segoe UI", 13, "bold"), 
                            fg="white", bg=COLORS["brand"],
                            padx=18, pady=10)
        user_label.pack()
        
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=250)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="SVWEN", font=("Segoe UI", 20, "bold"), 
                 fg=COLORS["brand"], bg=COLORS["sidebar"]).pack(pady=(40, 30), padx=30, anchor="w")

        nav_items = ["Dashboard", "Transactions", "Search", "Wallet"]
        for item in nav_items:
            btn = tk.Button(sidebar, text=f"  {item}", font=("Segoe UI", 11), 
                           bg=COLORS["sidebar"], fg=COLORS["text_primary"],
                           bd=0, anchor="w", padx=30, pady=12, relief="flat",
                           command=lambda i=item: self.switch_view(i))
            btn.pack(fill="x", pady=2)
            
            def on_enter(e, b=btn): 
                b.config(bg=COLORS["light_green"], fg=COLORS["brand"])
            def on_leave(e, b=btn): 
                b.config(bg=COLORS["sidebar"], fg=COLORS["text_primary"])
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

        tk.Button(sidebar, text="  Logout", font=("Segoe UI", 11), 
                 bg=COLORS["sidebar"], fg=COLORS["text_secondary"],
                 bd=0, anchor="w", padx=30, pady=20, relief="flat", 
                 command=self.show_login).pack(side="bottom", fill="x", pady=10)

        self.main_area = ttk.Frame(self)
        self.main_area.pack(side="right", fill="both", expand=True)
        
        self.content_frame = ttk.Frame(self.main_area, padding=30)
        self.content_frame.pack(fill="both", expand=True)

        self.render_dashboard()

    def switch_view(self, view_name):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        if view_name == "Dashboard": self.render_dashboard()
        elif view_name == "Transactions": self.render_transactions()
        elif view_name == "Search": self.render_search()
        elif view_name == "Wallet": self.render_wallet()

    def render_dashboard(self):
        me = self.api.me(self.token)
        balance = me.get("balance", "0.00")
        
        # Enhanced cards container with better spacing
        cards_container = tk.Frame(self.content_frame, bg=COLORS["bg"])
        cards_container.pack(fill="x", pady=(0, 25))
        
        # Balance card with enhanced styling
        balance_card = tk.Frame(cards_container, bg=COLORS["brand"], relief="flat", bd=0)
        balance_card.pack(side="left", padx=(0, 15), pady=10)
        balance_card.pack_propagate(False)
        
        # Balance card content
        balance_content = tk.Frame(balance_card, bg=COLORS["brand"])
        balance_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(balance_content, text=" Total Balance", 
                 font=("Segoe UI", 12), fg=COLORS["light_green"], 
                 bg=COLORS["brand"]).pack(anchor="w", pady=(0, 5))
        
        tk.Label(balance_content, text=f"${balance}", 
                 font=("Segoe UI", 28, "bold"), fg="white", 
                 bg=COLORS["brand"]).pack(anchor="w", pady=(5, 15))
        
        # Activity card with enhanced styling
        activity_card = tk.Frame(cards_container, bg=COLORS["card_bg"], relief="flat", bd=1, highlightbackground=COLORS["border"])
        activity_card.pack(side="right", fill="both", expand=True, padx=(15, 0), pady=10)
        activity_card.pack_propagate(False)
        
        # Activity card content
        activity_content = tk.Frame(activity_card, bg=COLORS["card_bg"])
        activity_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(activity_content, text=" Activity (7 Days)", 
                 font=("Segoe UI", 12), fg=COLORS["text_secondary"], 
                 bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 5))
        
        chart = ActivityChart(activity_content, width=400, height=100, data=[10, 25, 18, 40, 35, 60, 55])
        chart.pack(pady=(10, 0))
        
        # Quick Actions section
        quick_actions_frame = tk.Frame(self.content_frame, bg=COLORS["card_bg"], relief="flat", bd=1, highlightbackground=COLORS["border"])
        quick_actions_frame.pack(fill="x", pady=(20, 20))
        
        quick_actions_content = tk.Frame(quick_actions_frame, bg=COLORS["card_bg"])
        quick_actions_content.pack(fill="both", expand=True, padx=25, pady=20)
        
        tk.Label(quick_actions_content, text="⚡ Quick Actions", font=FONT_H2, 
                 fg=COLORS["text_primary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 15))
        
        actions_container = tk.Frame(quick_actions_content, bg=COLORS["card_bg"])
        actions_container.pack(fill="x")
        
        # Search button
        btn_search = tk.Button(actions_container, text="🔍 Search Transactions", bg=COLORS["brand"], fg="white", 
                             font=FONT_BOLD, relief="flat", pady=12, padx=20, 
                             command=lambda: self.switch_view("Search"), cursor="hand2")
        btn_search.pack(side="left", padx=(0, 15))
        
        # Transfer button
        btn_transfer = tk.Button(actions_container, text="💸 Send SOL", bg=COLORS["brand"], fg="white", 
                               font=FONT_BOLD, relief="flat", pady=12, padx=20, 
                               command=lambda: self.switch_view("Transactions"), cursor="hand2")
        btn_transfer.pack(side="left", padx=(0, 15))
        
        # Wallet button
        btn_wallet = tk.Button(actions_container, text="👛 Wallet", bg=COLORS["brand"], fg="white", 
                            font=FONT_BOLD, relief="flat", pady=12, padx=20, 
                            command=lambda: self.switch_view("Wallet"), cursor="hand2")
        btn_wallet.pack(side="left")
        
        # Recent transactions section with enhanced styling
        transactions_frame = tk.Frame(self.content_frame, bg=COLORS["bg"])
        transactions_frame.pack(fill="both", expand=True, pady=(0, 0))
        
        section_header = tk.Frame(transactions_frame, bg=COLORS["bg"])
        section_header.pack(fill="x", pady=(0, 10))
        
        tk.Label(section_header, text=" Recent Transactions", 
                 font=FONT_H2, fg=COLORS["text_primary"], 
                 bg=COLORS["bg"]).pack(side="left", pady=(0, 5))
        
        # Enhanced treeview with better styling
        cols = ("Type", "Counterparty", "Date", "Amount")
        tree = ttk.Treeview(transactions_frame, columns=cols, show="headings", height=8)
        
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), 
                    background=COLORS["bg"], foreground=COLORS["text_secondary"],
                    relief="flat", borderwidth=1)
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=25, 
                    background=COLORS["card_bg"], fieldbackground=COLORS["card_bg"], 
                    borderwidth=1, relief="solid")
        style.map("Treeview", background=[('selected', COLORS["light_green"])])
        
        # Configure column widths for better spacing
        tree.column("Type", width=100, minwidth=80)
        tree.column("Counterparty", width=200, minwidth=150)
        tree.column("Date", width=150, minwidth=120)
        tree.column("Amount", width=120, minwidth=100)
        
        for col in cols: 
            tree.heading(col, text=col, anchor="w")
        tree.pack(fill="both", expand=True, pady=(15, 0))

        # Load recent transactions
        try:
            res = self.api.search_transactions(self.token, self.username)
            if res.get("ok"):
                for tx_wrap in res.get("transactions", [])[:5]:
                    tx = tx_wrap["tx"]
                    t_type = "Received" if tx["To"] == self.username else "Sent"
                    party = tx["From"] if t_type == "Received" else tx["To"]
                    tree.insert("", "end", values=(t_type, party, tx.get("Time", "N/A"), f"{tx['Amount']} SOL"))
        except: pass

    def render_transactions(self):
        container = tk.Frame(self.content_frame, bg=COLORS["card_bg"], relief="flat", bd=1, highlightbackground=COLORS["border"])
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Form content with better spacing and visibility
        form_content = tk.Frame(container, bg=COLORS["card_bg"])
        form_content.pack(fill="both", expand=True, padx=40, pady=40)
        
        tk.Label(form_content, text="💸 Send SOL", font=FONT_H2, 
                 fg=COLORS["text_primary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 20))
        
        # Recipient field
        recipient_frame = tk.Frame(form_content, bg=COLORS["card_bg"])
        recipient_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(recipient_frame, text="Recipient Username", font=FONT_BOLD, 
                 fg=COLORS["text_primary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 8))
        
        self.tx_user = ttk.Entry(recipient_frame, font=("Segoe UI", 11), width=50)
        self.tx_user.pack(fill="x", ipady=10)
        
        # Amount field
        amount_frame = tk.Frame(form_content, bg=COLORS["card_bg"])
        amount_frame.pack(fill="x", pady=(0, 25))
        
        tk.Label(amount_frame, text="Amount", font=FONT_BOLD, 
                 fg=COLORS["text_primary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 8))
        
        self.tx_amt = ttk.Entry(amount_frame, font=("Segoe UI", 11), width=50)
        self.tx_amt.pack(fill="x", ipady=10)
        
        # Submit button with better visibility
        btn = tk.Button(form_content, text="Confirm Transfer", bg=COLORS["brand"], fg="white", 
                       font=FONT_BOLD, relief="flat", pady=15, padx=30, 
                       command=self.do_transfer, cursor="hand2")
        btn.pack(fill="x", pady=(10, 0))

    def do_transfer(self):
        u = self.tx_user.get()
        a = self.tx_amt.get()
        res = self.api.send_sol_to_username(self.token, u, a)
        if res.get("ok"):
            messagebox.showinfo("Success", f"Sent {a} SOL to {u}\nTxHash: {res.get('tx_hash')}")
            self.tx_user.delete(0, 'end')
            self.tx_amt.delete(0, 'end')
        else:
            messagebox.showerror("Error", res.get("error"))

    def render_search(self):
        search_container = tk.Frame(self.content_frame, bg=COLORS["card_bg"], relief="flat", bd=1, highlightbackground=COLORS["border"])
        search_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        search_frame = tk.Frame(search_container, bg=COLORS["card_bg"])
        search_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        tk.Label(search_frame, text="🔍 Search Ledger", font=FONT_H2, 
                 fg=COLORS["text_primary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 20))
        
        search_input_frame = tk.Frame(search_frame, bg=COLORS["card_bg"])
        search_input_frame.pack(fill="x", pady=(0, 20))
        
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_input_frame, textvariable=self.search_var, font=("Segoe UI", 11), width=60)
        entry.pack(side="left", fill="x", expand=True, ipady=12)
        
        btn = tk.Button(search_input_frame, text="Search", bg=COLORS["brand"], fg="white", 
                       font=FONT_BOLD, relief="flat", padx=30, pady=12, 
                       command=self.do_search, cursor="hand2")
        btn.pack(side="left", padx=(20, 0))
        
        # Enhanced results tree
        results_container = tk.Frame(search_frame, bg=COLORS["card_bg"])
        results_container.pack(fill="both", expand=True, pady=(20, 0))
        
        tk.Label(results_container, text="Search Results", font=("Segoe UI", 12, "bold"), 
                 fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 10))
        
        self.results_tree = ttk.Treeview(results_container, columns=("Hash", "From", "To", "Amount"), show="headings", height=10)
        self.results_tree.heading("Hash", text="Tx Hash")
        self.results_tree.heading("From", text="From")
        self.results_tree.heading("To", text="To")
        self.results_tree.heading("Amount", text="Amount")
        
        # Apply same table styling as dashboard
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), 
                    background=COLORS["bg"], foreground=COLORS["text_secondary"],
                    relief="flat", borderwidth=1)
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=25, 
                    background=COLORS["card_bg"], fieldbackground=COLORS["card_bg"], 
                    borderwidth=1, relief="solid")
        style.map("Treeview", background=[('selected', COLORS["light_green"])])
        
        self.results_tree.pack(fill="both", expand=True)

    def do_search(self):
        q = self.search_var.get()
        res = self.api.search_transactions(self.token, q)
        for i in self.results_tree.get_children(): self.results_tree.delete(i)
        
        if res.get("ok"):
            for tx_wrap in res.get("transactions", []):
                tx = tx_wrap["tx"]
                self.results_tree.insert("", "end", values=(tx["TxHash"], tx["From"], tx["To"], tx["Amount"]))
        else:
            messagebox.showinfo("Info", "No transactions found.")

    def render_wallet(self):
        me = self.api.me(self.token)
        
        # Enhanced wallet info container
        wallet_container = tk.Frame(self.content_frame, bg=COLORS["card_bg"], relief="flat", bd=1, highlightbackground=COLORS["border"])
        wallet_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        wallet_content = tk.Frame(wallet_container, bg=COLORS["card_bg"])
        wallet_content.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Section header
        tk.Label(wallet_content, text="👛 Wallet Information", font=FONT_H2, 
                 fg=COLORS["text_primary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 25))
        
        # Enhanced info rows with better spacing
        def row(label, val):
            row_frame = tk.Frame(wallet_content, bg=COLORS["card_bg"])
            row_frame.pack(fill="x", pady=12)
            
            tk.Label(row_frame, text=label, font=("Segoe UI", 11, "bold"), width=20, anchor="w", 
                     fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 20))
            
            tk.Label(row_frame, text=val, font=("Segoe UI", 11), bg=COLORS["card_bg"], 
                     fg=COLORS["text_primary"]).pack(side="left", anchor="w")
        
        row("Username", self.username)
        row("Role", me.get("role", "User"))
        row("Wallet Address", me.get("wallet_address", "Loading..."))
        row("Balance", f"{me.get('balance')} SOL")

        if me.get("role") == "tester":
            self.render_tester_tools()

    def render_tester_tools(self):
        tk.Label(self.content_frame, text="Admin Controls (Tester Only)", font=FONT_H2, bg=COLORS["bg"]).pack(anchor="w", pady=(30, 10))
        
        btn_verify = tk.Button(self.content_frame, text="Verify Blockchain Integrity", bg="#2563eb", fg="white",
                              font=FONT_BOLD, relief="flat", pady=8, padx=15, command=self.do_verify)
        btn_verify.pack(anchor="w")
        
        tk.Label(self.content_frame, text="Tamper Blockchain Block", font=("Segoe UI", 11, "bold"), bg=COLORS["bg"]).pack(anchor="w", pady=(20, 5))
        
        tamper_frame = tk.Frame(self.content_frame, bg=COLORS["bg"])
        tamper_frame.pack(anchor="w", fill="x")
        
        self.tamper_idx = ttk.Entry(tamper_frame, width=15)
        self.tamper_idx.pack(side="left", padx=(0, 10))
        self.tamper_idx.insert(0, "Block Index")
        
        self.tamper_data = ttk.Entry(tamper_frame, width=40)
        self.tamper_data.pack(side="left", padx=(0, 10))
        self.tamper_data.insert(0, "New Fake Data")
        
        btn_tamper = tk.Button(tamper_frame, text="Tamper Block", bg=COLORS["danger"], fg="white",
                              font=FONT_BOLD, relief="flat", padx=15, command=self.do_tamper)
        btn_tamper.pack(side="left")

    def do_verify(self):
        res = self.api.verify_blockchain(self.token)
        valid = res.get("valid", False)
        msg = f"Blockchain Integrity: {'VALID' if valid else 'CORRUPTED'}\n\n{res.get('output')}"
        messagebox.showinfo("Verification Result", msg)

    def do_tamper(self):
        idx = self.tamper_idx.get()
        data = self.tamper_data.get()
        
        if not idx.isdigit():
            messagebox.showerror("Error", "Block Index must be a number")
            return
            
        res = self.api.tamper_blockchain(self.token, int(idx), data)
        if res.get("ok"):
            messagebox.showinfo("Success", res.get("message"))
        else:
            messagebox.showerror("Error", res.get("error"))

if __name__ == "__main__":
    app = SVWENApp()
    app.mainloop()
