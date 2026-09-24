def enum_value(value: object) -> str:
    if value is None:
        return ""
    raw_value = getattr(value, "value", value)
    return str(raw_value)
