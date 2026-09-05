"""Re-Export der bepreisten Devis – delegiert an die Format-Module."""
from .parsers import crb, json_if


def export(devis, path: str, fmt: str = "crb") -> None:
    if fmt == "crb":
        crb.export(devis, path)
    elif fmt == "json":
        json_if.export(devis, path)
    else:
        raise ValueError(f"Unbekanntes Format: {fmt}")
