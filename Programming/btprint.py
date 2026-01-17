import serial
import serial.tools.list_ports
import winreg
import time
import re

# ==============================================================================
# 1. SCANNER (Find Real Names via Registry)
# ==============================================================================
def get_port_map_via_mac():
    mac_to_name = {}
    reg_path = r"SYSTEM\CurrentControlSet\Enum\BTHENUM"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            num_keys = winreg.QueryInfoKey(key)[0]
            for i in range(num_keys):
                try:
                    sub_key = winreg.EnumKey(key, i)
                    if sub_key.startswith("Dev_"):
                        mac = sub_key.split("_")[1]
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{reg_path}\\{sub_key}") as dev_key:
                            num_inst = winreg.QueryInfoKey(dev_key)[0]
                            for j in range(num_inst):
                                inst = winreg.EnumKey(dev_key, j)
                                with winreg.OpenKey(dev_key, inst) as inst_key:
                                    try:
                                        name, _ = winreg.QueryValueEx(inst_key, "FriendlyName")
                                        mac_to_name[mac] = name
                                    except: pass
                except: continue
    except: pass

    final_map = {}
    ports = serial.tools.list_ports.comports()
    for p in ports:
        found = False
        for mac, name in mac_to_name.items():
            if mac.upper() in re.sub(r'[^A-F0-9]', '', p.hwid.upper()):
                final_map[p.device] = name
                found = True
                break
        if not found:
            final_map[p.device] = p.description
    return final_map

# ==============================================================================
# 2. A6 SPEC LABEL (With FEED/EJECT)
# ==============================================================================
def get_a6_label():
    cmds = [
        # 1. PAGE SETUP
        "CLS",
        "SIZE 105 mm, 148 mm",  # A6 Size
        "GAP 0,0",              # Continuous Mode (Ignore sensor)
        "DIRECTION 1",
        
        # 2. CONTENT
        'TEXT 20,50,"3",0,1,1,"Model: LP-9200UB"',
        'TEXT 20,90,"2",0,1,1,"Printer Speed: 160mm/s"',
        'TEXT 20,130,"2",0,1,1,"Paper Width: 110mm/MAX"',
        'TEXT 20,170,"2",0,1,1,"Power Input: DC24V/2.5A"',
        'TEXT 20,210,"2",0,1,1,"Interface: USB / Bluetooth"',
        'TEXT 20,250,"2",0,1,1,"Certifications: CE, FCC, RoHS"',
        
        # Footer
        'TEXT 20,320,"3",0,1,1,"Barcode Label Printer"',
        'BARCODE 20,380,"128",80,1,0,2,2,"LP-9200UB"',
        
        # 3. PRINT
        "PRINT 1",
        
        # 4. EJECT (Crucial for Continuous Paper)
        # 240 dots = ~30mm feed. Adjust this if it's too short/long.
        "FEED 240"
    ]
    return "\r\n".join(cmds).encode('utf-8') + b"\r\n"

# ==============================================================================
# 3. MAIN (Select & Print)
# ==============================================================================
def main():
    print("--- Scanning Bluetooth Ports ---")
    friendly_map = get_port_map_via_mac()
    
    # Sort by COM number
    sorted_ports = sorted(friendly_map.keys(), key=lambda x: int(x.replace("COM","")) if "COM" in x else x)
    
    print(f"\n{'ID':<4} | {'PORT':<7} | {'DEVICE'}")
    print("-" * 50)
    
    valid_ports = []
    for i, port in enumerate(sorted_ports):
        name = friendly_map[port]
        # Highlight the likely printer
        prefix = "**" if "BlueTooth Printer" in name or "LP-" in name else "  "
        print(f"[{i}]  | {port:<7} | {prefix} {name}")
        valid_ports.append(port)
    print("-" * 50)

    # USER SELECTION
    sel = input("\nEnter ID number (Look for '**'): ")
    try:
        idx = int(sel)
        target_port = valid_ports[idx]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    print(f"\nConnecting to {target_port}...")
    try:
        with serial.Serial(target_port, 9600, timeout=3, dsrdtr=True) as p:
            print("Connected. Stabilizing...")
            time.sleep(2)
            
            print("Sending A6 Spec Sheet + Eject Command...")
            p.write(get_a6_label())
            p.flush()
            print("Done. Paper should feed out.")

    except Exception as e:
        print(f"[ERROR] {e}")
        if "semaphore" in str(e).lower():
            print(">> FIX: Remove device from Windows Settings and Re-Pair.")

if __name__ == "__main__":
    main()