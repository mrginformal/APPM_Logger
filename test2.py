import tkinter as tk

def show_tooltip(event):
    tooltip_label.place(x=event.x_root + 15, y=event.y_root + 10)
    tooltip_label.config(text="Hover Text Here")

def hide_tooltip(event):
    tooltip_label.place_forget()

root = tk.Tk()
root.title("Tooltip Example")

tooltip_label = tk.Label(root, text="", bg="lightyellow", relief="solid", borderwidth=1)
tooltip_label.place_forget()

target_widget = tk.Label(root, text="Hover over me!")
target_widget.pack()

target_widget.bind("<Enter>", show_tooltip)
target_widget.bind("<Leave>", hide_tooltip)

root.mainloop()
