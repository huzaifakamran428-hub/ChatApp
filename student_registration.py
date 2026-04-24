"""
Assignment 2: Tkinter Desktop Application
Student Registration Form
"""

import tkinter as tk
from tkinter import messagebox, ttk


# ── Main Window Setup ──────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Student Registration Form")
root.geometry("520x600")
root.resizable(False, False)
root.configure(bg="#f0f4f8")

# ── Colour / Font constants ────────────────────────────────────────────────────
HEADING_FONT  = ("Helvetica", 16, "bold")
LABEL_FONT    = ("Helvetica", 11)
ENTRY_FONT    = ("Helvetica", 11)
BTN_FONT      = ("Helvetica", 11, "bold")
BG            = "#f0f4f8"
CARD_BG       = "#ffffff"
ACCENT        = "#3a86ff"
BTN_RED       = "#e63946"

# ── Storage list for registered students ──────────────────────────────────────
students = []

# ─────────────────────────────────────────────────────────────────────────────
# Helper — create a labelled entry row
# ─────────────────────────────────────────────────────────────────────────────
def make_row(parent, label_text, row, widget=None):
    tk.Label(parent, text=label_text, font=LABEL_FONT,
             bg=CARD_BG, anchor="w").grid(
        row=row, column=0, sticky="w", padx=16, pady=(10, 2))

    if widget is None:
        entry = tk.Entry(parent, font=ENTRY_FONT, width=30,
                         relief="flat", highlightthickness=1,
                         highlightbackground="#ccd6f6",
                         highlightcolor=ACCENT)
        entry.grid(row=row, column=1, padx=16, pady=(10, 2), sticky="w")
        return entry
    else:
        widget.grid(row=row, column=1, padx=16, pady=(10, 2), sticky="w")
        return widget


# ─────────────────────────────────────────────────────────────────────────────
# Card frame (white rounded-ish box)
# ─────────────────────────────────────────────────────────────────────────────
tk.Label(root, text="🎓  Student Registration", font=HEADING_FONT,
         bg=BG, fg=ACCENT).pack(pady=(24, 8))

card = tk.Frame(root, bg=CARD_BG, bd=0, relief="flat",
                highlightthickness=1, highlightbackground="#dce3f0")
card.pack(padx=30, pady=8, fill="both")

# ── Form fields ───────────────────────────────────────────────────────────────
entry_name    = make_row(card, "Full Name *",      0)
entry_roll    = make_row(card, "Roll Number *",    1)
entry_email   = make_row(card, "Email Address",    2)
entry_phone   = make_row(card, "Phone Number",     3)

# Department dropdown
dept_var = tk.StringVar(value="Select Department")
dept_menu = ttk.Combobox(card, textvariable=dept_var, font=ENTRY_FONT,
                         width=27, state="readonly",
                         values=["Computer Science", "Software Engineering",
                                 "Information Technology", "Electrical Engineering",
                                 "Business Administration"])
entry_dept = make_row(card, "Department *", 4, dept_menu)

# Gender radio buttons
gender_var = tk.StringVar(value="")
gender_frame = tk.Frame(card, bg=CARD_BG)
tk.Radiobutton(gender_frame, text="Male",   variable=gender_var,
               value="Male",   bg=CARD_BG, font=LABEL_FONT).pack(side="left")
tk.Radiobutton(gender_frame, text="Female", variable=gender_var,
               value="Female", bg=CARD_BG, font=LABEL_FONT).pack(side="left", padx=12)
tk.Radiobutton(gender_frame, text="Other",  variable=gender_var,
               value="Other",  bg=CARD_BG, font=LABEL_FONT).pack(side="left")
make_row(card, "Gender", 5, gender_frame)

# Semester spinbox
sem_var = tk.IntVar(value=1)
sem_spin = tk.Spinbox(card, from_=1, to=8, textvariable=sem_var,
                      font=ENTRY_FONT, width=5, relief="flat",
                      highlightthickness=1, highlightbackground="#ccd6f6")
make_row(card, "Semester", 6, sem_spin)


# ─────────────────────────────────────────────────────────────────────────────
# Logic functions
# ─────────────────────────────────────────────────────────────────────────────
def validate_email(email):
    """Simple e-mail format check."""
    return "@" in email and "." in email.split("@")[-1]


def register():
    """Validate inputs and save the student record."""
    name  = entry_name.get().strip()
    roll  = entry_roll.get().strip()
    email = entry_email.get().strip()
    phone = entry_phone.get().strip()
    dept  = dept_var.get()
    gender= gender_var.get()
    sem   = sem_var.get()

    # ── Validation ──────────────────────────────────────────────────────────
    if not name or not roll:
        messagebox.showerror("Missing Fields",
                             "Full Name and Roll Number are required.")
        return
    if dept == "Select Department":
        messagebox.showerror("Missing Fields", "Please select a Department.")
        return
    if email and not validate_email(email):
        messagebox.showerror("Invalid Email",
                             "Please enter a valid email address.")
        return
    if phone and not phone.isdigit():
        messagebox.showerror("Invalid Phone",
                             "Phone number should contain digits only.")
        return

    # ── Save ────────────────────────────────────────────────────────────────
    record = {
        "Name": name, "Roll": roll, "Email": email or "—",
        "Phone": phone or "—", "Dept": dept,
        "Gender": gender or "—", "Semester": sem
    }
    students.append(record)

    messagebox.showinfo("Success",
                        f"✅ Student '{name}' registered successfully!\n"
                        f"Total students registered: {len(students)}")
    clear_form()


def clear_form():
    """Reset all fields to default values."""
    entry_name.delete(0, tk.END)
    entry_roll.delete(0, tk.END)
    entry_email.delete(0, tk.END)
    entry_phone.delete(0, tk.END)
    dept_var.set("Select Department")
    gender_var.set("")
    sem_var.set(1)


def show_records():
    """Open a popup window listing all registered students."""
    if not students:
        messagebox.showinfo("No Records", "No students registered yet.")
        return

    win = tk.Toplevel(root)
    win.title("Registered Students")
    win.geometry("620x380")
    win.configure(bg=BG)

    tk.Label(win, text="Registered Students", font=HEADING_FONT,
             bg=BG, fg=ACCENT).pack(pady=10)

    cols = ("Name", "Roll", "Department", "Gender", "Semester", "Email")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=95, anchor="center")
    tree.column("Name", width=120)
    tree.column("Email", width=140)

    for s in students:
        tree.insert("", tk.END,
                    values=(s["Name"], s["Roll"], s["Dept"],
                            s["Gender"], s["Semester"], s["Email"]))

    scrollbar = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=8)
    scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 16))


# ─────────────────────────────────────────────────────────────────────────────
# Buttons
# ─────────────────────────────────────────────────────────────────────────────
btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=16)

tk.Button(btn_frame, text="  Register  ", font=BTN_FONT,
          bg=ACCENT, fg="white", relief="flat", cursor="hand2",
          padx=12, pady=6, command=register).grid(row=0, column=0, padx=8)

tk.Button(btn_frame, text="  Clear  ", font=BTN_FONT,
          bg="#6c757d", fg="white", relief="flat", cursor="hand2",
          padx=12, pady=6, command=clear_form).grid(row=0, column=1, padx=8)

tk.Button(btn_frame, text="  View Records  ", font=BTN_FONT,
          bg="#2ecc71", fg="white", relief="flat", cursor="hand2",
          padx=12, pady=6, command=show_records).grid(row=0, column=2, padx=8)

# ── Status bar ────────────────────────────────────────────────────────────────
tk.Label(root, text="* Required fields", font=("Helvetica", 9),
         bg=BG, fg="#6c757d").pack(side="bottom", pady=6)

# ─────────────────────────────────────────────────────────────────────────────
root.mainloop()
