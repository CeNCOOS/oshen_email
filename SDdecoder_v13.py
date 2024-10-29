import struct
import csv
import os
from datetime import datetime
import re
import sys

cpp_struct = '''
struct SDFixedMessage
{
    uint8_t MSG_FORMAT_CODE;
    uint8_t CONTROL_MODE;
    int8_t SAT_TX_ERR;
    uint16_t N_SAT_TX_ATTEMPTS;
    int16_t SAIL_TARGET_ANGLE;
    int16_t SAIL_MEASURED_ANGLE;
    int16_t RUDDER_TARGET_ANGLE;
    int16_t RUDDER_MEASURED_ANGLE;
    uint16_t TARGET_HEADING;
    uint16_t DIRECT_BEARING_TO_WAYPOINT;
    uint16_t MEASURED_HEADING;
    int16_t SAIL_PWM;
    int16_t RUDDER_PWM;
    float WIND_DIRECTION_INST;
    uint16_t VESSEL_WIND_DIRECTION;
    float GILL_WIND_SPEED;
    float GILL_WIND_DIR;
    float GILL_PRESSURE;
    float GILL_HUMIDITY;
    float GILL_AIRTEMP;
    uint16_t GILL_COMPASS;
    float HULL_SST;
    float KEEL_SST;
    uint16_t TARGET_RADIUS;
    uint16_t CORRIDOR_WIDTH;
    int16_t CROSSTRACK_DIST;
    float CORRIDOR_START_LAT;
    float CORRIDOR_START_LONG;
    float NEXT_WAYPOINT_LAT;
    float NEXT_WAYPOINT_LONG;
    uint32_t DIST_TO_NEXT_WAYPOINT;
    uint32_t SECS_SINCE_CONTROLLER_RESPONSE;
    uint32_t SECS_SINCE_WIND_READING;
    float GPS_LAT;
    float GPS_LONG;
    int32_t GPS_Z;
    float GPS_COURSE;
    float GPS_VELOCITY;
    uint32_t SECS_SINCE_GPS_FIX;
    uint32_t TIME;
    uint16_t MILLIS;
    float POWER_BATT_1s;
    float VOLTAGE_BATT;
    float PID_P;
    float PID_I;
    float PID_D;
    float IMU_HEADING;
    float IMU_PITCH;
    float IMU_ROLL;
    float GYRO_DATA_X;
    float GYRO_DATA_Y;
    float GYRO_DATA_Z;
    float ACC_DATA_X;
    float ACC_DATA_Y;
    float ACC_DATA_Z;
    float MAG_DATA_X;
    float MAG_DATA_Y;
    float MAG_DATA_Z;
};
'''

# Map C++ types to struct format characters and sizes
type_mapping = {
    'uint8_t': ('B', 1),
    'int8_t': ('b', 1),
    'uint16_t': ('H', 2),
    'int16_t': ('h', 2),
    'uint32_t': ('L', 4),
    'int32_t': ('l', 4),
    'float': ('f', 4)
}

# Parse the C++ struct definition
def parse_cpp_struct(cpp_struct):
    field_names = []
    struct_format = '='  # Start with little-endian format
    offset = 0

    for line in cpp_struct.splitlines():
        match = re.search(r'\s*(\w+)\s+(\w+);', line)
        if match:
            c_type, name = match.groups()
            field_names.append(name)
            type_format, size = type_mapping[c_type]
            
            # Calculate padding
            padding = (size - (offset % size)) % size
            if padding > 0:
                struct_format += f'{padding}x'
                offset += padding
            
            struct_format += type_format
            offset += size

    return field_names, struct_format

FIELD_NAMES, STRUCT_FORMAT = parse_cpp_struct(cpp_struct)
STRUCT_SIZE = struct.calcsize(STRUCT_FORMAT)

print("STRUCT_FORMAT:", STRUCT_FORMAT)
print("FIELD_NAMES:", FIELD_NAMES)
print("STRUCT_SIZE:", STRUCT_SIZE)

def read_struct_from_bin(filename):
    with open(filename, 'rb') as f:
        while True:
            data = f.read(STRUCT_SIZE)
            if len(data) < STRUCT_SIZE:  # EOF or not a complete struct
                break
            unpacked_data = list(struct.unpack(STRUCT_FORMAT, data))
            
            # Convert Unix timestamp (assuming it's the 'TIMESTAMP' field)
            timestamp_index = FIELD_NAMES.index('TIME')
            unix_timestamp = unpacked_data[timestamp_index]
            datetime_str = datetime.utcfromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            unpacked_data[timestamp_index] = datetime_str
            
            yield tuple(unpacked_data)

def write_to_csv(filename, data):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(FIELD_NAMES)  # Writing headers
        writer.writerows(data)

def main():
    if len(sys.argv) > 1:
        # If a directory is passed as a command line argument
        directory = sys.argv[1]
    else:
        # If no argument is passed, use the current directory
        directory = "./"	  
    for file in os.listdir(directory):
        if file.startswith("LOG") and (not file.endswith('.csv')):
            data = list(read_struct_from_bin(directory+file))
            csv_filename = directory+file+".csv"
            if os.path.exists(csv_filename):
                print("File exists. Not overwriting:" + csv_filename)            
            else:
                write_to_csv(csv_filename, data)
                print(f"Transcribed {file} to {csv_filename}")

if __name__ == "__main__":
    main()
