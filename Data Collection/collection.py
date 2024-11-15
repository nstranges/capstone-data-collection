import serial
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import time

serial_port = 'COM3'
baud_rate = 115200

# Displays the image
def display_image(image_path):
    img = mpimg.imread(image_path)
    plt.imshow(img)
    plt.axis('off')
    plt.show()

# Makes a countdown
def countdown(seconds):
    print("Close your hand in...")
    for i in range(seconds, 0, -1):
        print(f"{i}...", end="\r", flush=True)
        time.sleep(1)
    print("Go!")

# Read value from the serial port
def readserial(comport, baudrate, num_samples=115200):
    ser = serial.Serial(comport, baudrate, timeout=0.000004)         # 1/timeout is the frequency at which the port is read
    data_df = pd.DataFrame(columns=['Timestamp', 'xaccel', 'yaccel', 'zaccel', 'xrot', 'yrot', 'zrot'])
    data = {"xaccel": None, "yaccel": None, "zaccel": None, "xrot": None, "yrot": None, "zrot": None}
    samples = 0

    while samples < num_samples:
        line = ser.readline().decode().strip()
        timestamp = time.strftime('%H:%M:%S')

        # Putting into dictonary
        if line.startswith("xaccel"):
            data["xaccel"] = float(line.split(" ")[1])
        elif line.startswith("yaccel"):
            data["yaccel"] = float(line.split(" ")[1])
        elif line.startswith("zaccel"):
            data["zaccel"] = float(line.split(" ")[1])
        elif line.startswith("xrot"):
            data["xrot"] = float(line.split(" ")[1])
        elif line.startswith("yrot"):
            data["yrot"] = float(line.split(" ")[1])
        elif line.startswith("zrot"):
            data["zrot"] = float(line.split(" ")[1])

        # Batch add to dataframe
        if all(data.values()):
            data_df.loc[len(data_df)] = [timestamp, *data.values()]
            data = {key: None for key in data}  # Resetting dictonary
            samples += 1

    ser.close()
    return data_df

# Data Collection loop
def collection():
    # Numbering by DOFS. 1 (thumb), 2 (index, middle), 3 (ring, pinky)
    # Numbering is based on what DoF is closed
    positions = [0, 1, 2, 3, 12, 13, 23, 123]
    pic_positions = {
        0: "/Pictures/pic_0.jpeg",
        1: "/Pictures/pic_1.jpeg",
        2: "/Pictures/pic_2.jpeg",
        3: "/Pictures/pic_3.jpeg",
        12: "/Pictures/pic_12.jpeg",
        13: "/Pictures/pic_13.jpeg",
        23: "/Pictures/pic_23.jpeg",
        123: "/Pictures/pic_123.jpeg"
    }
    orientations_per_pos = 10

    #Excel writer
    name = input(f"Enter User's name and press Enter...")
    writer = pd.ExcelWriter('/Data Collection/Data' + name + '_data.xlsx', engine='xlsxwriter')

    # Go through all positions and orientations
    for pos in positions:
        # Display the example image
        print("Please see the image on which fingers to close")
        display_image(pic_positions[pos])

        for ori in range(orientations_per_pos):
            if ori != 1:
                input("Change the orientation of your hand to a random position. Press enter...")

            countdown(3)

            data_df = readserial(serial_port, baud_rate)
            data_df['Position'] = pos
            data_df['Orientation'] = ori
            data_df.to_excel(writer, sheet_name=f'Position_{pos}', index=False)

    writer.save()

if __name__ == '__main__':
    collection()
