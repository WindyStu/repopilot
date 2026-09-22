def make_default_short_help(help_text: str, max_length: int = 45) -> str:
    paragraph_end = help_text.find("\n\n")
    if paragraph_end != -1:
        help_text = help_text[:paragraph_end]
    words = help_text.split()
    if not words:
        return ""
    if words[0] == "\b":
        words = words[1:]

    total_length = 0
    last_index = len(words) - 1
    for index, word in enumerate(words):
        total_length += len(word) + (index > 0)
        if total_length > max_length:
            break
        if word[-1] == ".":
            return " ".join(words[: index + 1])
        if total_length == max_length and index != last_index:
            break
    else:
        return " ".join(words)

    total_length += len("...")
    while index > 0:
        total_length -= len(words[index]) + (index > 0)
        if total_length <= max_length:
            break
        index -= 1
    return " ".join(words[:index]) + "..."
