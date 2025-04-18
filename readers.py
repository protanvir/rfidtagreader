import csv
import threading
import time
import logging
from datetime import datetime
from sllurp import llrp
from tkinter import Tk, Button, Label, Listbox, Scrollbar, END, RIGHT, LEFT, Y, BOTH, Frame
import queue

# Configuration
READER_IP = '192.168.2.2'
CSV_FILE = 'rfid_reads.csv'
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 500

# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global state
reading = False
seen_tags = set()
reader = None
config = llrp.LLRPReaderConfig()
gui_update_queue = queue.Queue()

def tag_report_callback(reader, tag_reports):
    """Handle incoming RFID tag reports."""
    for tag in tag_reports:
        epc = next((value for key, value in tag.items() if 'EPC' in key), 'UNKNOWN')
        
        if epc != 'UNKNOWN':
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_to_csv(epc, timestamp)

            if epc not in seen_tags:
                seen_tags.add(epc)
                gui_update_queue.put((epc, timestamp))
        else:
            logging.warning("EPC is UNKNOWN, skipping...")

def process_gui_updates():
    """Process updates from the queue and reflect them in the GUI."""
    while not gui_update_queue.empty():
        epc, timestamp = gui_update_queue.get()
        try:
            listbox.insert(END, f"{epc} — {timestamp}")
            listbox.yview(END)
            tag_count_label.config(text=f"Total Tags: {len(seen_tags)}")
        except Exception as e:
            logging.error(f"GUI Update Failed: {e}")
    window.after(100, process_gui_updates)

def save_to_csv(epc, timestamp):
    """Append a new EPC and timestamp to the CSV file."""
    try:
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([epc, timestamp])
        logging.info(f"Saved to CSV: EPC={epc}, Timestamp={timestamp}")
    except IOError as e:
        logging.error(f"Failed to write to CSV: {e}")

def read_tags():
    """Main reading logic for processing RFID tags."""
    global reading, reader
    try:
        reader = llrp.LLRPReaderClient(host=READER_IP, port=5084, config=config)
        reader.add_tag_report_callback(tag_report_callback)
        reader.connect()
        
        while reading:
            time.sleep(0.1)
        reader.disconnect()
    except Exception as e:
        logging.error(f"An error occurred: {e}")

def start_reading():
    """Start the RFID reading process."""
    global reading, seen_tags
    if not reading:
        reading = True
        seen_tags.clear()
        listbox.delete(0, END)
        tag_count_label.config(text="Total Tags: 0")
        threading.Thread(target=read_tags, daemon=True).start()
        status_label.config(text="Status: Reading")

def stop_reading():
    """Stop the RFID reading process."""
    global reading
    if reading:
        reading = False
        status_label.config(text="Status: Idle")

# GUI Setup
window = Tk()
window.title("RFID Reader Controller")
window.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

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

# Start processing GUI updates
window.after(100, process_gui_updates)

# Run the GUI
window.mainloop()