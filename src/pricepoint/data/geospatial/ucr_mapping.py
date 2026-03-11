"""UCR (Uniform Crime Reporting) code mapping and fuzzy matching.

Provides a hardcoded 57-row UCR reference table and utilities for:
- Direct lookup by UCR code (``lookup_ucr``)
- Fuzzy matching of free-text offense descriptions (``fuzzy_match_ucr``)
"""

from __future__ import annotations

from difflib import SequenceMatcher

# UCR code → (description, group, category, crime_against)
# Sources: FBI NIBRS User Manual, NC SBI NIBRS spec
UCR_MAP: dict[str, tuple[str, str, str, str]] = {
    # --- Crimes Against Persons ---
    "09A": ("Murder & Nonnegligent Manslaughter", "Homicide", "Crimes Against Persons", "Person"),
    "09B": ("Negligent Manslaughter", "Homicide", "Crimes Against Persons", "Person"),
    "09C": ("Justifiable Homicide", "Homicide", "Crimes Against Persons", "Person"),
    "100": ("Kidnapping/Abduction", "Kidnapping/Abduction", "Crimes Against Persons", "Person"),
    "11A": ("Rape", "Sex Offenses", "Crimes Against Persons", "Person"),
    "11B": ("Sodomy", "Sex Offenses", "Crimes Against Persons", "Person"),
    "11C": ("Sexual Assault With An Object", "Sex Offenses", "Crimes Against Persons", "Person"),
    "11D": ("Fondling", "Sex Offenses", "Crimes Against Persons", "Person"),
    "36A": ("Incest", "Sex Offenses", "Crimes Against Persons", "Person"),
    "36B": ("Statutory Rape", "Sex Offenses", "Crimes Against Persons", "Person"),
    "13A": ("Aggravated Assault", "Assault", "Crimes Against Persons", "Person"),
    "13B": ("Simple Assault", "Assault", "Crimes Against Persons", "Person"),
    "13C": ("Intimidation", "Assault", "Crimes Against Persons", "Person"),
    "64A": (
        "Human Trafficking - Commercial Sex Acts",
        "Human Trafficking",
        "Crimes Against Persons",
        "Person",
    ),
    "64B": (
        "Human Trafficking - Involuntary Servitude",
        "Human Trafficking",
        "Crimes Against Persons",
        "Person",
    ),
    # --- Crimes Against Property ---
    "120": ("Robbery", "Robbery", "Crimes Against Property", "Property"),
    "200": ("Arson", "Arson", "Crimes Against Property", "Property"),
    "210": ("Extortion/Blackmail", "Extortion/Blackmail", "Crimes Against Property", "Property"),
    "220": ("Burglary/Breaking & Entering", "Burglary", "Crimes Against Property", "Property"),
    "23A": ("Pocket-picking", "Larceny/Theft", "Crimes Against Property", "Property"),
    "23B": ("Purse-snatching", "Larceny/Theft", "Crimes Against Property", "Property"),
    "23C": ("Shoplifting", "Larceny/Theft", "Crimes Against Property", "Property"),
    "23D": ("Theft From Building", "Larceny/Theft", "Crimes Against Property", "Property"),
    "23E": (
        "Theft From Coin-Operated Machine or Device",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
    ),
    "23F": ("Theft From Motor Vehicle", "Larceny/Theft", "Crimes Against Property", "Property"),
    "23G": (
        "Theft of Motor Vehicle Parts or Accessories",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
    ),
    "23H": ("All Other Larceny", "Larceny/Theft", "Crimes Against Property", "Property"),
    "240": ("Motor Vehicle Theft", "Motor Vehicle Theft", "Crimes Against Property", "Property"),
    "250": ("Counterfeiting/Forgery", "Fraud", "Crimes Against Property", "Property"),
    "26A": (
        "False Pretenses/Swindle/Confidence Game",
        "Fraud",
        "Crimes Against Property",
        "Property",
    ),
    "26B": (
        "Credit Card/Automated Teller Machine Fraud",
        "Fraud",
        "Crimes Against Property",
        "Property",
    ),
    "26C": ("Impersonation", "Fraud", "Crimes Against Property", "Property"),
    "26D": ("Welfare Fraud", "Fraud", "Crimes Against Property", "Property"),
    "26E": ("Wire Fraud", "Fraud", "Crimes Against Property", "Property"),
    "26F": ("Identity Theft", "Fraud", "Crimes Against Property", "Property"),
    "26G": ("Hacking/Computer Invasion", "Fraud", "Crimes Against Property", "Property"),
    "270": ("Embezzlement", "Embezzlement", "Crimes Against Property", "Property"),
    "280": ("Stolen Property Offenses", "Stolen Property", "Crimes Against Property", "Property"),
    "290": (
        "Destruction/Damage/Vandalism of Property",
        "Vandalism",
        "Crimes Against Property",
        "Property",
    ),
    # --- Crimes Against Society ---
    "35A": ("Drug/Narcotic Violations", "Drug Offenses", "Crimes Against Society", "Society"),
    "35B": ("Drug Equipment Violations", "Drug Offenses", "Crimes Against Society", "Society"),
    "370": ("Pornography/Obscene Material", "Pornography", "Crimes Against Society", "Society"),
    "40A": ("Prostitution", "Prostitution", "Crimes Against Society", "Society"),
    "40B": (
        "Assisting or Promoting Prostitution",
        "Prostitution",
        "Crimes Against Society",
        "Society",
    ),
    "40C": ("Purchasing Prostitution", "Prostitution", "Crimes Against Society", "Society"),
    "510": ("Bribery", "Bribery", "Crimes Against Society", "Society"),
    "520": ("Weapon Law Violations", "Weapon Offenses", "Crimes Against Society", "Society"),
    "39A": ("Betting/Wagering", "Gambling", "Crimes Against Society", "Society"),
    "39B": (
        "Operating/Promoting/Assisting Gambling",
        "Gambling",
        "Crimes Against Society",
        "Society",
    ),
    "39C": ("Gambling Equipment Violations", "Gambling", "Crimes Against Society", "Society"),
    "39D": ("Sports Tampering", "Gambling", "Crimes Against Society", "Society"),
    "720": ("Animal Cruelty", "Animal Cruelty", "Crimes Against Society", "Society"),
    # --- Group B (arrest-only) ---
    "90A": ("Bad Checks", "All Other Offenses", "Group B", "Society"),
    "90B": ("Curfew/Loitering/Vagrancy Violations", "All Other Offenses", "Group B", "Society"),
    "90C": ("Disorderly Conduct", "All Other Offenses", "Group B", "Society"),
    "90D": ("Driving Under the Influence", "All Other Offenses", "Group B", "Society"),
    "90E": ("Drunkenness", "All Other Offenses", "Group B", "Society"),
    "90F": ("Family Offenses, Nonviolent", "All Other Offenses", "Group B", "Society"),
    "90G": ("Liquor Law Violations", "All Other Offenses", "Group B", "Society"),
    "90H": ("Peeping Tom", "All Other Offenses", "Group B", "Society"),
    "90I": ("Runaway", "All Other Offenses", "Group B", "Society"),
    "90J": ("Trespass of Real Property", "All Other Offenses", "Group B", "Society"),
    "90Z": ("All Other Offenses", "All Other Offenses", "Group B", "Society"),
}

# Pre-built description → code lookup for fuzzy matching
_DESCRIPTION_INDEX: list[tuple[str, str]] = [
    (desc.lower(), code) for code, (desc, _, _, _) in UCR_MAP.items()
]


def _normalize_code(code: str) -> str:
    """Normalize a UCR code string: strip whitespace, uppercase, zero-pad pure ints."""
    code = code.strip().upper()
    try:
        numeric = int(code)
        # Pad to 2 or 3 digits to match map keys like "200", "100"
        if numeric < 100:
            return str(numeric).zfill(2)
        return str(numeric)
    except ValueError:
        return code


def lookup_ucr(code: str | None) -> tuple[str | None, str | None]:
    """Look up crime group and category by UCR code.

    Returns (group, category) or (None, None) if not found.
    """
    if not code:
        return None, None

    normalized = _normalize_code(code)
    entry = UCR_MAP.get(normalized)
    if entry:
        return entry[1], entry[2]
    return None, None


def fuzzy_match_ucr(
    offense: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Fuzzy-match a free-text offense description against UCR descriptions.

    Returns (matched_ucr_code, group, category) or (None, None, None) if no
    match exceeds the 0.6 similarity threshold.
    """
    if not offense:
        return None, None, None

    target = offense.strip().lower()
    if not target:
        return None, None, None

    best_score = 0.0
    best_code: str | None = None

    for desc_lower, code in _DESCRIPTION_INDEX:
        score = SequenceMatcher(None, target, desc_lower).ratio()
        if score > best_score:
            best_score = score
            best_code = code

    if best_score >= 0.6 and best_code is not None:
        entry = UCR_MAP[best_code]
        return best_code, entry[1], entry[2]

    return None, None, None
