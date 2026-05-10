from enum import StrEnum


def enum_values(enum: type[StrEnum]) -> list[str]:
    return [item.value for item in enum]
