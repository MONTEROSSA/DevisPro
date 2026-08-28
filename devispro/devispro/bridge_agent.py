"""Bridge Agent - stub for Windows build compatibility."""

def chat(cmd: str) -> str:
    """Simple command handler stub."""
    cmd_lower = cmd.lower().strip()
    
    if "kanton" in cmd_lower:
        return "Kanton geändert. Bitte in Stammdaten speichern."
    elif "export" in cmd_lower and "abacus" in cmd_lower:
        return "Abacus-Export vorbereitet. Nutzen Sie den Export-Button."
    elif "bepreis" in cmd_lower:
        return "Bepreisung gestartet. Nutzen Sie Import → Eigene Preise."
    elif "hilfe" in cmd_lower or "help" in cmd_lower:
        return "Verfügbare Befehle: kanton, export abacus, bepreise, hilfe"
    else:
        return f"Unbekannter Befehl: {cmd}. Tippen Sie 'hilfe' für Optionen."