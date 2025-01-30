import tkinter as tk

def calculate():
    try:
        global current_num  # Declare that we're modifying 'current_num'

        if operator == '+':
            result = float(current_num) + float(result)
        elif operator == '-':
            result = float(current_num) - float(result)
        elif operator == '*':
            result = float(current_num) * float(result)
        elif operator == '/':
            if float(result) != 0:
                result = float(current_num) / float(result)
            else:
                result = 0
     except Exception as e:
        print(f"Error: {e}")

def clear():
    global current_num  # Declare that we're modifying 'current_num'
    nonlocal result, display_result
    current_num = ""
    result = 0.0

def update_result():
    display_result.config(text=str(result))

def display(num):
    if not num:  # handles empty string case
        nonlocal current_num
        current_num = num
    else:
        if current_num == "0":  # replace leading zero with new number
            current_num = num
        elif "." in current_num and len(current_num) > 1:  # prevent double decimal
            current_num = num
    update_result()

def clear_all():
    global current_num, result
    current_num = "0"
    result = 0.0

root = tk.Tk()
root.title("Simple Calculator")
root.geometry("350pxx280px")

frame = tk.Frame(root)
frame.pack(pady=20)

display_result = tk.Label(frame, text="Result: ", font=('Arial', 14))
display_result.pack()

current_num_entry = tk.Entry(frame, width=15, font=('Arial', 14), justify='right')
current_num_entry.pack()
current_num_entry.bind("<Return>", update_result)
current_num_entry.bind(" ", update_result)

result_entry = tk.Entry(frame, width=15, textvariable=result, font=('Arial', 14))
result_entry.pack()

buttons_frame = tk.Frame(root)
buttons_frame.pack(pady=10)

buttons = [
    ('7', '8', '9', '+', '-', '*'),
    ('4', '5', '6', '/', '*', '**'),  # Fixed operator order
    ('1', '2', '3', '%', '//', '**'),  # Added additional operators
    ('0', '.', ' Clear', '(', ')', '=')  # Fixed "Clear" label
]

operator_index = 0

for i in range(4):
    row = []
    for j in range(3):
        if (i, j) == (2, 3):
            continue
        elif (i, j) == (3, 2):
            continue
        elif (i, j) == (1, 0):
            continue

        button_text = buttons[operator_index][j]
        operator_index += 1 if (i != 0 or j in [1, 2]) else 0

        if i < 3:
            if j < 3:
                row.append(tk.Button(buttons_frame, text=button_text,
                                    command=lambda opn=button_text: calculate(opn)))
            elif j == 3 and i != 0:
                row.append(tk.Button(buttons_frame, text=buttons[operator_index][j],
                                    command=lambda opn=buttons[operator_index][j]: calculate(opn)))
            elif j == 4 and i < 2:
                continue
        elif j in [1, 2] and i == 3:
            row.append(tk.Button(buttons_frame, text=button_text,
                                command=lambda opn=button_text: calculate(opn)))

    buttons_row = []
    for b in row[:3]:
        buttons_row.append(b)
    if len(row) > 3:
        buttons_row.append("Clear")
        buttons_row.append("(", ")")

    button_frame = tk.Frame(buttons_frame, width=100)
    button_frame.pack()

    for k in range(4):
        if k < (len(buttons_row)):
            buttons_row[k].pack(side=tk.LEFT, padx=5)
        else:
            break

clear_button = tk.Button(root, text="C", font=('Arial', 14), command=clear)
clear_button.pack(pady=5)

update_result()

root.mainloop()
