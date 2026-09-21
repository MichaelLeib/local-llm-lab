def parse_records(text):
    """Parse lines of the form NAME=INTEGER into a dict.

    Nonempty lines are required to match NAME=INTEGER. Whitespace around
    names and values is stripped. Repeated names are summed. Any nonempty
    malformed line (missing '=', empty name, empty value, non-integer
    value) raises ValueError.
    """
    result = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if '=' not in line:
            raise ValueError(f"malformed line (missing '='): {line!r}")
        name, sep, value = line.partition('=')
        name = name.strip()
        value = value.strip()
        if not name:
            raise ValueError(f"malformed line (empty name): {line!r}")
        if not value:
            raise ValueError(f"malformed line (empty value): {line!r}")
        try:
            number = int(value)
        except ValueError:
            raise ValueError(f"malformed line (non-integer value): {line!r}")
        result[name] = result.get(name, 0) + number
    return result
