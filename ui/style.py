"""Visual constants preserving the established compact layout."""

APPLY_STYLE = "background-color: rgb(77, 99, 120);"
RESET_STYLE = "background-color: rgb(87, 102, 120);"
DISCONNECT_STYLE = "background-color: rgb(107, 87, 87);"
FIELD_RANGES = {
    "uniform": (-10.0, 10.0), "scale": (-10.0, 10.0),
    "rotate": (-180.0, 180.0), "move": (-100.0, 100.0),
    "line_width": (-30.0, 30.0),
}
STANDARD_COLOR_COLUMNS = (
    ("#1A1A1A", "#424242", "#757575", "#9E9E9E", "#D0D0D0", "#F5F5F5"),
    ("#4A0D0D", "#8A1919", "#E53935", "#EF5350", "#F58A87", "#FFCDD2"),
    ("#4A2508", "#8A440F", "#FB8C00", "#FFA726", "#FFBE72", "#FFE0B2"),
    ("#4A4308", "#8A7D0F", "#FDD835", "#FFEE58", "#FFF59D", "#FFF9C4"),
    ("#084A22", "#0F8A3E", "#43A047", "#66BB6A", "#A5D6A7", "#C8E6C9"),
    ("#084A47", "#0F8A85", "#00ACC1", "#26C6DA", "#80DEEA", "#B2EBF2"),
    ("#08284A", "#0F4C8A", "#1E88E5", "#42A5F5", "#90CAF9", "#BBDEFB"),
    ("#42084A", "#7A0F8A", "#8E24AA", "#AB47BC", "#CE93D8", "#F8BBD0"),
)
STANDARD_COLORS = tuple(color for column in STANDARD_COLOR_COLUMNS for color in column)
