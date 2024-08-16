import csv
import re

def parse_time(time_string):
    """Convert time string to total minutes and decimal hours."""
    hours = 0
    minutes = 0
    if 'h' in time_string:
        hours = int(re.search(r'(\d+)h', time_string).group(1))
    if 'm' in time_string:
        minutes = int(re.search(r'(\d+)m', time_string).group(1))
    total_minutes = hours * 60 + minutes
    decimal_hours = hours + minutes / 60
    return total_minutes, decimal_hours

def preprocess_lines(lines):
    """Preprocess lines according to user instructions."""
    cleaned_lines = []
    prev_line = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        if 'STL fuel' in line or '\tTO\t' in line or 'APP' in line or 'LND' in line:
            continue
        if 'DEP' in line:
            line = line.replace('DEP', 'CHRG')

        if 'FTL fuel' in line:
            # If the previous line was already processed, add this FTL fuel line to it
            if prev_line:
                cleaned_lines.append(prev_line + '\t' + line)
                prev_line = None
            else:
                # Handle case where FTL fuel is the first relevant line (shouldn't happen with correct data)
                prev_line = line
        else:
            if prev_line:
                cleaned_lines.append(prev_line)
            prev_line = line

    if prev_line:
        cleaned_lines.append(prev_line)

    return cleaned_lines


def parse_chrg_line(line):
    """Parse a CHRG line to extract origin and fuel."""
    parts = re.split(r'\s+', line)

    # Set origin to the split between 'CHRG ' and '(orbit)'
    origin = parts[2]
    fuel = int(re.search(r'(\d+)\s+units FTL fuel', line).group(1))
    return origin, fuel

def parse_jmp_line(line):
    """Parse a JMP line to extract destination, time, and parsecs."""
    parts = re.split(r'\s+', line) 
    destination = parts[2]
    hours = parts[4].strip()
    minutes = ''
    if parts[5].strip()[-1] == 'm':
        minutes = parts[5].strip()
    time_string = hours + ' ' + minutes
    
    # Find the index of 'parsecs' and get the value before it
    parsecs_index = parts.index([part for part in parts if 'parsecs' in part][0])
    parsecs = int(parts[parsecs_index - 1].strip())
    
    total_minutes, decimal_hours = parse_time(time_string)
    return destination, total_minutes, decimal_hours, parsecs

def main(input_file, output_file):
    current_reactor_usage = None
    
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        csv_writer = csv.writer(outfile)
        csv_writer.writerow(['origin', 'destination', 'minutes', 'hours', 'parsecs', 'fuel', 'reactor'])

        lines = infile.readlines()
        cleaned_lines = preprocess_lines(lines)
        
        # Initialize variables to track the last CHRG data
        last_origin = None
        last_fuel = None

        for line in cleaned_lines:
            line = line.strip()

            if 'Reactor usage' in line:
                # Extract reactor usage percentage and convert it to a decimal
                current_reactor_usage = float(re.search(r'Reactor usage (\d+)%', line).group(1)) / 100

            elif 'CHRG' in line:
                # Parse the CHRG line to get the origin and fuel
                last_origin, last_fuel = parse_chrg_line(line)
                
            elif 'JMP' in line and last_origin and last_fuel is not None:
                # Parse the JMP line to get the destination, time, and parsecs
                destination, minutes, hours, parsecs = parse_jmp_line(line)

                # Write the parsed data to the CSV file
                csv_writer.writerow([last_origin, destination, minutes, round(hours, 3), parsecs, last_fuel, current_reactor_usage])
                
                # Reset the last origin and fuel after processing
                last_origin = None
                last_fuel = None

if __name__ == '__main__':
    input_file = 'flight-calculation-dump.txt'  # Input file name
    output_file = 'jump-data.csv'  # Output CSV file name
    main(input_file, output_file)
