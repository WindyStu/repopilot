_ansi_colors = {
    "black": 30,
    "red": 31,
    "green": 32,
    "blue": 34,
    "white": 37,
    "reset": 39,
}


def _interpret_color(color, offset=0):
    if isinstance(color, int):
        return f"{38 + offset};5;{color:d}"
    if isinstance(color, (tuple, list)):
        red, green, blue = color
        return f"{38 + offset};2;{red:d};{green:d};{blue:d}"
    return str(_ansi_colors[color] + offset)


def style(text, *, fg=None, bg=None, reset=True):
    bits = []
    if fg:
        try:
            bits.append(f"\033[{_interpret_color(fg)}m")
        except KeyError:
            raise TypeError(f"Unknown color {fg!r}") from None
    if bg:
        try:
            bits.append(f"\033[{_interpret_color(bg, 10)}m")
        except KeyError:
            raise TypeError(f"Unknown color {bg!r}") from None
    bits.append(str(text))
    if reset:
        bits.append("\033[0m")
    return "".join(bits)
