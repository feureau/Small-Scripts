import pandas as pd
import plotly.graph_objects as go
import tkinter as tk
from tkinter import ttk

# Data for Competitive mode (Grandmaster and Above)
competitive_grandmaster_data = [
    {"name": "Doctor Strange", "role": "Vanguard", "pick_rate": 34.02, "win_rate": 51.87},
    {"name": "Mantis", "role": "Strategist", "pick_rate": 27.03, "win_rate": 53.34},
    {"name": "Luna Snow", "role": "Strategist", "pick_rate": 21.61, "win_rate": 50.28},
    {"name": "Magneto", "role": "Vanguard", "pick_rate": 20.38, "win_rate": 49.40},
    {"name": "Cloak&Dagger", "role": "Strategist", "pick_rate": 15.93, "win_rate": 43.18},
    {"name": "Rocket Raccoon", "role": "Strategist", "pick_rate": 14.62, "win_rate": 51.84},
    {"name": "Psylocke", "role": "Duelist", "pick_rate": 13.55, "win_rate": 51.92},
    {"name": "Groot", "role": "Vanguard", "pick_rate": 13.02, "win_rate": 49.17},
    {"name": "The Punisher", "role": "Duelist", "pick_rate": 12.52, "win_rate": 47.30},
    {"name": "Namor", "role": "Duelist", "pick_rate": 10.39, "win_rate": 49.13},
    {"name": "Winter Soldier", "role": "Duelist", "pick_rate": 10.27, "win_rate": 45.21},
    {"name": "Hulk", "role": "Vanguard", "pick_rate": 10.22, "win_rate": 54.17},
    {"name": "Star-Lord", "role": "Duelist", "pick_rate": 9.13, "win_rate": 51.00},
    {"name": "Loki", "role": "Strategist", "pick_rate": 8.77, "win_rate": 51.03},
    {"name": "Adam Warlock", "role": "Strategist", "pick_rate": 8.09, "win_rate": 53.42},
    {"name": "Peni Parker", "role": "Vanguard", "pick_rate": 7.85, "win_rate": 50.09},
    {"name": "Thor", "role": "Vanguard", "pick_rate": 7.69, "win_rate": 49.59},
    {"name": "Iron Man", "role": "Duelist", "pick_rate": 6.69, "win_rate": 52.70},
    {"name": "Hela", "role": "Duelist", "pick_rate": 6.31, "win_rate": 51.26},
    {"name": "Black Panther", "role": "Duelist", "pick_rate": 5.76, "win_rate": 52.34},
    {"name": "Magik", "role": "Duelist", "pick_rate": 4.93, "win_rate": 54.15},
    {"name": "Moon Knight", "role": "Duelist", "pick_rate": 4.59, "win_rate": 42.99},
    {"name": "Venom", "role": "Vanguard", "pick_rate": 4.56, "win_rate": 45.29},
    {"name": "Wolverine", "role": "Duelist", "pick_rate": 4.48, "win_rate": 52.16},
    {"name": "Jeff the Land Shark", "role": "Strategist", "pick_rate": 3.94, "win_rate": 44.21},
    {"name": "Hawkeye", "role": "Duelist", "pick_rate": 3.60, "win_rate": 49.89},
    {"name": "Spider- Man", "role": "Duelist", "pick_rate": 2.47, "win_rate": 49.13},
    {"name": "Captain America", "role": "Vanguard", "pick_rate": 2.27, "win_rate": 47.98},
    {"name": "Iron Fist", "role": "Duelist", "pick_rate": 1.60, "win_rate": 54.00},
    {"name": "Squirrel Girl", "role": "Duelist", "pick_rate": 1.27, "win_rate": 41.57},
    {"name": "Storm", "role": "Duelist", "pick_rate": 0.94, "win_rate": 50.37},
    {"name": "Black Widow", "role": "Duelist", "pick_rate": 0.80, "win_rate": 39.41},
    {"name": "Scarlet Witch", "role": "Duelist", "pick_rate": 0.69, "win_rate": 43.02}
]

# Convert to DataFrame
competitive_grandmaster_df = pd.DataFrame(competitive_grandmaster_data)

# Function to create interactive bar chart for each role
def create_plotly_chart(df, role):
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['name'],
        y=df['pick_rate'],
        name='Pick Rate (%)',
        marker_color='blue'
    ))
    
    fig.add_trace(go.Bar(
        x=df['name'],
        y=df['win_rate'],
        name='Win Rate (%)',
        marker_color='green'
    ))
    
    fig.update_layout(
        title=f"{role} - Pick Rate and Win Rate in Competitive Mode (Grandmaster and Above)",
        xaxis_title="Character",
        yaxis_title="Rate (%)",
        barmode='group',
        xaxis_tickangle=-45
    )
    
    fig.show()

# Group data by role
duelist_grandmaster = competitive_grandmaster_df[competitive_grandmaster_df['role'] == 'Duelist']
strategist_grandmaster = competitive_grandmaster_df[competitive_grandmaster_df['role'] == 'Strategist']
vanguard_grandmaster = competitive_grandmaster_df[competitive_grandmaster_df['role'] == 'Vanguard']

# GUI setup
def launch_gui():
    root = tk.Tk()
    root.title("Competitive Mode Analysis")
    root.geometry("400x200")

    def show_chart(role):
        if role == "Duelist":
            create_plotly_chart(duelist_grandmaster, "Duelist")
        elif role == "Strategist":
            create_plotly_chart(strategist_grandmaster, "Strategist")
        elif role == "Vanguard":
            create_plotly_chart(vanguard_grandmaster, "Vanguard")

    label = tk.Label(root, text="Select Role to View Chart:", font=("Arial", 14))
    label.pack(pady=10)

    role_selector = ttk.Combobox(root, values=["Duelist", "Strategist", "Vanguard"], font=("Arial", 12))
    role_selector.pack(pady=10)

    button = tk.Button(root, text="Show Chart", command=lambda: show_chart(role_selector.get()), font=("Arial", 12))
    button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    launch_gui()
