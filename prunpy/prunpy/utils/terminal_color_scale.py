import math

def terminal_color_scale(value, min_value, max_value, format_spec, value_override=None, inverse=False, logarithmic=False, color_map=None):
    """
    Applies color to the formatted value based on the given range and color map.
    Supports coloration for values outside the min and max range.
    If 'inverse' is True or if min_value > max_value, the colors are applied in reverse.
    """
    # Define the color map with positions and corresponding colors
    if color_map is None:
        color_map = {
            -1: (40, 40, 40),           # Dark gray for values far below min
            0: (255, 0, 0),             # Red at min
            0.25: (255, 165, 0),        # Orange
            0.5: (255, 255, 0),         # Yellow
            0.75: (0, 255, 0),          # Green
            1: (0, 255, 255),           # Cyan at max
            2: (255, 0, 255),           # Magenta for values far above max
        }

    # Handle inverse logic by reversing the mapping
    if min_value > max_value:
        inverse = not inverse
    if inverse:
        min_value, max_value = min(max_value, min_value), max(max_value, min_value)
        color_map = {
            -1: color_map[2],
            0: color_map[1],
            0.25: color_map[0.75],
            0.5: color_map[0.5],
            0.75: color_map[0.25],
            1: color_map[0],
            2: color_map[-1],
        }

    # Apply logarithmic scaling if requested
    placement_value = value
    if logarithmic:
        if value == 0:
            placement_value = 1e-32
        else:
            placement_value = math.log10(value)

    # Calculate the span and normalized value key
    span = max_value - min_value
    normalized_value = (placement_value - min_value) / span

    # Clamp normalized_value to the min and max keys in color_map
    min_key = min(color_map.keys())
    max_key = max(color_map.keys())

    if normalized_value < min_key:
        normalized_value = min_key
    elif normalized_value > max_key:
        normalized_value = max_key

    # Get the two keys to interpolate between
    sorted_keys = sorted(color_map.keys())

    lower_key = max(k for k in sorted_keys if k <= normalized_value)
    upper_key = min(k for k in sorted_keys if k >= normalized_value)

    if lower_key == upper_key:
        r, g, b = color_map[lower_key]
    else:
        # Interpolate between the lower and upper color
        lower_color = color_map[lower_key]
        upper_color = color_map[upper_key]
        segment_ratio = (normalized_value - lower_key) / (upper_key - lower_key)

        r = int(lower_color[0] + (upper_color[0] - lower_color[0]) * segment_ratio)
        g = int(lower_color[1] + (upper_color[1] - lower_color[1]) * segment_ratio)
        b = int(lower_color[2] + (upper_color[2] - lower_color[2]) * segment_ratio)

    if value_override is not None:
        value = value_override

    # Format the value using the specified format
    formatted_value = format(value, format_spec)

    # Apply color using ANSI escape codes for RGB
    colored_value = f"\033[38;2;{r};{g};{b}m{formatted_value}\033[0m"

    return colored_value
