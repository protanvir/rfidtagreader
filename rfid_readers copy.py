import csv
import threading
import time
from datetime import datetime
from sllurp import llrp
from tkinter import Tk, Button, Label, Listbox, Scrollbar, END, RIGHT, LEFT, Y, BOTH, Frame
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient  # Updated import
import queue  # Import the queue module

# Configuration
READER_IP = '192.168.2.2'
CSV_FILE = 'rfid_reads.csv'

# Global state
reading = False
seen_tags = set()
reader = None

# Create a configuration for the LLRP client
config = LLRPReaderConfig()

# Create a thread-safe queue for GUI updates
gui_update_queue = queue.Queue()

# Handle incoming tags
def tag_report_callback(reader, tag_reports):  # Updated to handle tag_reports as a list
    for tag in tag_reports:
        print(f"[DEBUG] Raw Tag Data: {tag}")  # Debugging: Print the raw tag data
        epc = next((value for key, value in tag.items() if 'EPC' in key), 'UNKNOWN')  # Dynamically extract any EPC field
        print(f"[DEBUG] Extracted EPC: {epc}")  # Debugging: Log the extracted EPC

        if epc != 'UNKNOWN':  # Only process valid EPCs
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_to_csv(epc, timestamp)

            if epc not in seen_tags:
                seen_tags.add(epc)
                gui_update_queue.put((epc, timestamp))  # Add updates to the queue
        else:
            print("[WARN] EPC is UNKNOWN, skipping...")  # Debugging: Warn about unknown EPCs

# Add a function to process the queue and update the GUI
def process_gui_updates():
    while not gui_update_queue.empty():
        epc, timestamp = gui_update_queue.get()
        listbox.insert(END, f"{epc} — {timestamp}")
        listbox.yview(END)  # Automatically scroll to the latest entry
        tag_count_label.config(text=f"Total Tags: {len(seen_tags)}")  # Dynamically update the tag count
    window.after(100, process_gui_updates)  # Schedule the next check

# Save to CSV immediately
def save_to_csv(epc, timestamp):
    try:
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:  # Ensure proper encoding
            writer = csv.writer(file)
            writer.writerow([epc, timestamp])
        print(f"[INFO] Saved to CSV: EPC={epc}, Timestamp={timestamp}")  # Debugging: Log successful writes
    except Exception as e:
        print(f"[ERROR] Failed to write to CSV: {e}")  # Debugging: Log any errors

# RFID reading logic
def read_tags():
    global reading, reader
    try:
        reader = LLRPReaderClient(host=READER_IP, port=5084, config=config)  # Use LLRPReaderClient
        reader.add_tag_report_callback(tag_report_callback)  # Register the callback

        print("[INFO] Connecting to reader...")
        reader.connect()
        print("[INFO] Reader connected and processing tags...")

        while reading:
            time.sleep(0.1)  # Allow the loop to periodically check the `reading` flag

        print("[INFO] Stopping reader...")
        reader.disconnect()  # Gracefully disconnect the reader
        print("[INFO] Reader disconnected.")
    except Exception as e:
        print(f"[ERROR] {e}")

# GUI button logic
def start_reading():
    global reading, seen_tags
    if not reading:
        reading = True
        seen_tags.clear()
        listbox.delete(0, END)
        tag_count_label.config(text="Total Tags: 0")
        threading.Thread(target=read_tags, daemon=True).start()
        status_label.config(text="Status: Reading")
    else:
        print("[WARN] Already reading.")

def stop_reading():
    global reading
    if reading:
        reading = False
        status_label.config(text="Status: Idle")
    else:
        print("[WARN] Not currently reading.")

# GUI Setup
window = Tk()
window.title("RFID Reader Controller")
window.geometry("400x500")

start_button = Button(window, text="START", command=start_reading, width=20, height=2, bg='green', fg='white')
start_button.pack(pady=10)

stop_button = Button(window, text="STOP", command=stop_reading, width=20, height=2, bg='red', fg='white')
stop_button.pack(pady=5)

status_label = Label(window, text="Status: Idle")
status_label.pack(pady=5)

tag_count_label = Label(window, text="Total Tags: 0")
tag_count_label.pack(pady=5)

# Frame for tag list
frame = Frame(window)
frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

scrollbar = Scrollbar(frame)
scrollbar.pack(side=RIGHT, fill=Y)

listbox = Listbox(frame, yscrollcommand=scrollbar.set)
listbox.pack(side=LEFT, fill=BOTH, expand=True)
scrollbar.config(command=listbox.yview)

# Start processing GUI updates after the `window` object is created
window.after(100, process_gui_updates)

# Run the GUI
window.mainloop()
