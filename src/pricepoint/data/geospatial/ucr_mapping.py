"""UCR (Uniform Crime Reporting) code mapping and fuzzy matching.

Provides a hardcoded UCR reference table and utilities for:
- Direct lookup by UCR code (``lookup_ucr``)
- Fuzzy matching of free-text offense descriptions (``fuzzy_match_ucr``)
"""

from __future__ import annotations

from difflib import SequenceMatcher

# UCR code → (description, group, category, crime_against, offense_class)
# Sources: FBI NIBRS User Manual (2025 spec), NC SBI NIBRS spec,
#          Raleigh PD local SRS-style codes
UCR_MAP: dict[str, tuple[str, str, str, str, str]] = {
    # --- Crimes Against Persons ---
    "09A": (
        "Murder & Nonnegligent Manslaughter",
        "Homicide",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "09B": ("Negligent Manslaughter", "Homicide", "Crimes Against Persons", "Person", "Group A"),
    "09C": ("Justifiable Homicide", "Homicide", "Crimes Against Persons", "Person", "Group A"),
    "100": (
        "Kidnapping/Abduction",
        "Kidnapping/Abduction",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "11A": ("Rape", "Sex Offenses", "Crimes Against Persons", "Person", "Group A"),
    "11B": ("Sodomy", "Sex Offenses", "Crimes Against Persons", "Person", "Group A"),
    "11C": (
        "Sexual Assault With An Object",
        "Sex Offenses",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "11D": ("Fondling", "Sex Offenses", "Crimes Against Persons", "Person", "Group A"),
    "36A": ("Incest", "Sex Offenses", "Crimes Against Persons", "Person", "Group A"),
    "36B": ("Statutory Rape", "Sex Offenses", "Crimes Against Persons", "Person", "Group A"),
    "360": (
        "Failure to Register as a Sex Offender",
        "Sex Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "13A": ("Aggravated Assault", "Assault", "Crimes Against Persons", "Person", "Group A"),
    "13B": ("Simple Assault", "Assault", "Crimes Against Persons", "Person", "Group A"),
    "13C": ("Intimidation", "Assault", "Crimes Against Persons", "Person", "Group A"),
    "64A": (
        "Human Trafficking - Commercial Sex Acts",
        "Human Trafficking",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "64B": (
        "Human Trafficking - Involuntary Servitude",
        "Human Trafficking",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    # --- Crimes Against Property ---
    "120": ("Robbery", "Robbery", "Crimes Against Property", "Property", "Group A"),
    "200": ("Arson", "Arson", "Crimes Against Property", "Property", "Group A"),
    "210": (
        "Extortion/Blackmail",
        "Extortion/Blackmail",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "220": (
        "Burglary/Breaking & Entering",
        "Burglary",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "23A": ("Pocket-picking", "Larceny/Theft", "Crimes Against Property", "Property", "Group A"),
    "23B": ("Purse-snatching", "Larceny/Theft", "Crimes Against Property", "Property", "Group A"),
    "23C": ("Shoplifting", "Larceny/Theft", "Crimes Against Property", "Property", "Group A"),
    "23D": (
        "Theft From Building",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "23E": (
        "Theft From Coin-Operated Machine or Device",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "23F": (
        "Theft From Motor Vehicle",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "23G": (
        "Theft of Motor Vehicle Parts or Accessories",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "23H": ("All Other Larceny", "Larceny/Theft", "Crimes Against Property", "Property", "Group A"),
    "240": (
        "Motor Vehicle Theft",
        "Motor Vehicle Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "250": ("Counterfeiting/Forgery", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "26A": (
        "False Pretenses/Swindle/Confidence Game",
        "Fraud",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "26B": (
        "Credit Card/Automated Teller Machine Fraud",
        "Fraud",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "26C": ("Impersonation", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "26D": ("Welfare Fraud", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "26E": ("Wire Fraud", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "26F": ("Identity Theft", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "26G": ("Hacking/Computer Invasion", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "26H": ("Money Laundering", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "270": ("Embezzlement", "Embezzlement", "Crimes Against Property", "Property", "Group A"),
    "280": (
        "Stolen Property Offenses",
        "Stolen Property",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "290": (
        "Destruction/Damage/Vandalism of Property",
        "Vandalism",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    # --- Crimes Against Society ---
    "35A": (
        "Drug/Narcotic Violations",
        "Drug Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "35B": (
        "Drug Equipment Violations",
        "Drug Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "370": (
        "Pornography/Obscene Material",
        "Pornography",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "40A": ("Prostitution", "Prostitution", "Crimes Against Society", "Society", "Group A"),
    "40B": (
        "Assisting or Promoting Prostitution",
        "Prostitution",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "40C": (
        "Purchasing Prostitution",
        "Prostitution",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "510": ("Bribery", "Bribery", "Crimes Against Property", "Property", "Group A"),
    "520": (
        "Weapon Law Violations",
        "Weapon Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "521": (
        "Violation of National Firearm Act",
        "Weapon Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "522": (
        "Weapons of Mass Destruction",
        "Weapon Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "526": ("Explosives", "Weapon Offenses", "Crimes Against Society", "Society", "Group A"),
    "39A": ("Betting/Wagering", "Gambling", "Crimes Against Society", "Society", "Group A"),
    "39B": (
        "Operating/Promoting/Assisting Gambling",
        "Gambling",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "39C": (
        "Gambling Equipment Violations",
        "Gambling",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "39D": ("Sports Tampering", "Gambling", "Crimes Against Society", "Society", "Group A"),
    "720": ("Animal Cruelty", "Animal Cruelty", "Crimes Against Society", "Society", "Group A"),
    "49A": (
        "Harboring Escapee/Concealing from Arrest",
        "Fugitive Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "49B": (
        "Flight to Avoid Prosecution",
        "Fugitive Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "49C": (
        "Flight to Avoid Deportation",
        "Fugitive Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "58A": (
        "Import Violations",
        "Commerce Violations",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "58B": (
        "Export Violations",
        "Commerce Violations",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "61A": (
        "Federal Liquor Offenses",
        "Commerce Violations",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "61B": (
        "Federal Tobacco Offenses",
        "Commerce Violations",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "620": (
        "Wildlife Trafficking",
        "Commerce Violations",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "101": ("Treason", "Treason", "Crimes Against Society", "Society", "Group A"),
    "103": ("Espionage", "Espionage", "Crimes Against Society", "Society", "Group A"),
    # --- Group B (arrest-only) ---
    "90A": ("Bad Checks", "All Other Offenses", "Group B", "Society", "Group B"),
    "90B": (
        "Curfew/Loitering/Vagrancy Violations",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    "90C": ("Disorderly Conduct", "All Other Offenses", "Group B", "Society", "Group B"),
    "90D": ("Driving Under the Influence", "All Other Offenses", "Group B", "Society", "Group B"),
    "90E": ("Drunkenness", "All Other Offenses", "Group B", "Society", "Group B"),
    "90F": ("Family Offenses, Nonviolent", "All Other Offenses", "Group B", "Society", "Group B"),
    "90G": ("Liquor Law Violations", "All Other Offenses", "Group B", "Society", "Group B"),
    "90H": ("Peeping Tom", "All Other Offenses", "Group B", "Society", "Group B"),
    "90I": ("Runaway", "All Other Offenses", "Group B", "Society", "Group B"),
    "90J": ("Trespass of Real Property", "All Other Offenses", "Group B", "Society", "Group B"),
    "90K": ("Failure to Appear", "All Other Offenses", "Group B", "Society", "Group B"),
    "90L": ("Federal Resource Violations", "All Other Offenses", "Group B", "Society", "Group B"),
    "90M": ("Perjury", "All Other Offenses", "Group B", "Society", "Group B"),
    "90Z": ("All Other Offenses", "All Other Offenses", "Group B", "Society", "Group B"),
    # --- Raleigh SRS-style local codes (Crimes Against Persons) ---
    "17D": (
        "Sex Offense/Forcible Fondling",
        "Sex Offenses",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "17M": (
        "Sex Offense/Indecent Exposure",
        "Sex Offenses",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "17N": (
        "Sex Offense/Peeping Tom",
        "Sex Offenses",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "20A": ("Robbery/From Business", "Robbery", "Crimes Against Property", "Property", "Group A"),
    "20B": ("Robbery/From Person", "Robbery", "Crimes Against Property", "Property", "Group A"),
    "25E": ("Assault/Simple", "Assault", "Crimes Against Persons", "Person", "Group A"),
    "25F": (
        "Assault/Intimidation-Communicating Threats",
        "Assault",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "25G": ("Assault/Aggravated", "Assault", "Crimes Against Persons", "Person", "Group A"),
    "25N": ("Child Abuse/Simple", "Assault", "Crimes Against Persons", "Person", "Group A"),
    "50A": (
        "Kidnapping/Abduction",
        "Kidnapping/Abduction",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "60A": (
        "Human Trafficking/Commercial Sex Acts",
        "Human Trafficking",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    "60B": (
        "Human Trafficking/Involuntary Servitude",
        "Human Trafficking",
        "Crimes Against Persons",
        "Person",
        "Group A",
    ),
    # --- Raleigh SRS-style local codes (Crimes Against Property) ---
    "30A": (
        "Burglary/Commercial or Non-Residential",
        "Burglary",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "30B": ("Burglary/Residential", "Burglary", "Crimes Against Property", "Property", "Group A"),
    "35C": (
        "Larceny/Shoplifting",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "35D": (
        "Larceny/Theft from Building",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "35F": (
        "Larceny/Theft from Motor Vehicle",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "35G": (
        "Larceny/Theft of MV Parts-Accessories",
        "Larceny/Theft",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "35H": ("Larceny/All Other", "Larceny/Theft", "Crimes Against Property", "Property", "Group A"),
    "45A": ("Arson", "Arson", "Crimes Against Property", "Property", "Group A"),
    "52A": (
        "Stolen Property/Possession (w/ Arrest)",
        "Stolen Property",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "52B": (
        "Stolen Property/Possess Stolen Vehicle (w/ Arrest)",
        "Stolen Property",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "52C": (
        "Stolen Property/Recover Stolen Property (no arrest)",
        "Stolen Property",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "52D": (
        "Stolen Property/Recover Stolen Vehicle (no arrest)",
        "Stolen Property",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "53A": (
        "Damage to Property (Group A)",
        "Vandalism",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "55A": ("Counterfeiting/Forgery", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "56A": (
        "Fraud/False Pretense or Swindle",
        "Fraud",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "56B": (
        "Fraud/Credit Card-ATM Fraud",
        "Fraud",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "56C": ("Fraud/ID Theft", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "56D": ("Fraud/Welfare Fraud", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "56E": ("Fraud/Wire Fraud", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "56F": (
        "Fraud/Worthless-Bad Checks",
        "Fraud",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "56G": (
        "Fraud/Rental Car Conversion",
        "Fraud",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "56H": (
        "Fraud/Impersonation of LEO",
        "Fraud",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "56I": ("Hacking/Computer Invasion", "Fraud", "Crimes Against Property", "Property", "Group A"),
    "61M": (
        "Extortion/Blackmail",
        "Extortion/Blackmail",
        "Crimes Against Property",
        "Property",
        "Group A",
    ),
    "63M": ("Embezzlement", "Embezzlement", "Crimes Against Property", "Property", "Group A"),
    # --- Raleigh SRS-style local codes (Crimes Against Society) ---
    "51A": (
        "Weapons/Carry Concealed Weapon",
        "Weapon Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "51B": (
        "Weapons/Illegal Possession of Weapon",
        "Weapon Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "51C": (
        "Weapons/Shots Fired (with evidence)",
        "Weapon Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "51D": ("Weapons/All Other", "Weapon Offenses", "Crimes Against Society", "Society", "Group A"),
    "54C": (
        "Drug Violation/Felony",
        "Drug Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "54D": (
        "Drug Violation/Misdemeanor",
        "Drug Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    "54Z": (
        "Drug Equipment/Paraphernalia",
        "Drug Offenses",
        "Crimes Against Society",
        "Society",
        "Group A",
    ),
    # --- Raleigh SRS-style local codes (Group B) ---
    "70B": ("Disorderly Conduct/Begging", "All Other Offenses", "Group B", "Society", "Group B"),
    "70C": (
        "Disorderly Conduct/Disturbing the Peace",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    "70D": (
        "Disorderly Conduct/Drunk-Disorderly",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    "70E": (
        "Disorderly Conduct/Resist-Delay-Obstruct Officer",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    "71A": ("Traffic/DWI", "All Other Offenses", "Group B", "Society", "Group B"),
    "71M": ("Liquor-Alcohol Law Violations", "All Other Offenses", "Group B", "Society", "Group B"),
    "80A": ("All Other/All Other Offenses", "All Other Offenses", "Group B", "Society", "Group B"),
    "80B": (
        "All Other/Damage to Property (minor)",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    "80C": (
        "All Other/Noise Ordinance Violation",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    "80D": ("All Other/Trespassing", "All Other Offenses", "Group B", "Society", "Group B"),
    "80E": (
        "All Other/Unauthorized Use of Vehicle",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    "80F": (
        "All Other/Harassing Telephone Calls",
        "All Other Offenses",
        "Group B",
        "Society",
        "Group B",
    ),
    # --- Raleigh SRS-style local codes (Animal Disturbance) ---
    "82B": (
        "Humane/Noisy Animal",
        "Animal Disturbance",
        "Crimes Against Society",
        "Society",
        "Animal Disturbance",
    ),
    "82E": (
        "Humane/Animal Bite",
        "Animal Disturbance",
        "Crimes Against Society",
        "Society",
        "Animal Disturbance",
    ),
    "82F": (
        "Humane/Vicious Animal",
        "Animal Disturbance",
        "Crimes Against Society",
        "Society",
        "Animal Disturbance",
    ),
    "82G": (
        "Humane/All Other Humane",
        "Animal Disturbance",
        "Crimes Against Society",
        "Society",
        "Animal Disturbance",
    ),
    "82H": (
        "Humane/Rabies Test",
        "Animal Disturbance",
        "Crimes Against Society",
        "Society",
        "Animal Disturbance",
    ),
    "82J": (
        "Humane/Chemical Deployment",
        "Animal Disturbance",
        "Crimes Against Society",
        "Society",
        "Animal Disturbance",
    ),
    "82K": (
        "Humane/Animal Cruelty",
        "Animal Disturbance",
        "Crimes Against Society",
        "Society",
        "Animal Disturbance",
    ),
}

# Pre-built description → code lookup for fuzzy matching
_DESCRIPTION_INDEX: list[tuple[str, str]] = [
    (desc.lower(), code) for code, (desc, _, _, _, _) in UCR_MAP.items()
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


def lookup_ucr(code: str | None) -> tuple[str | None, str | None, str | None]:
    """Look up crime group, category, and offense class by UCR code.

    Returns (group, category, offense_class) or (None, None, None) if not found.
    """
    if not code:
        return None, None, None

    normalized = _normalize_code(code)
    entry = UCR_MAP.get(normalized)
    if entry:
        return entry[1], entry[2], entry[4]
    return None, None, None


def fuzzy_match_ucr(
    offense: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Fuzzy-match a free-text offense description against UCR descriptions.

    Returns (matched_ucr_code, group, category, offense_class) or
    (None, None, None, None) if no match exceeds the 0.6 similarity threshold.
    """
    if not offense:
        return None, None, None, None

    target = offense.strip().lower()
    if not target:
        return None, None, None, None

    best_score = 0.0
    best_code: str | None = None

    for desc_lower, code in _DESCRIPTION_INDEX:
        score = SequenceMatcher(None, target, desc_lower).ratio()
        if score > best_score:
            best_score = score
            best_code = code

    if best_score >= 0.6 and best_code is not None:
        entry = UCR_MAP[best_code]
        return best_code, entry[1], entry[2], entry[4]

    return None, None, None, None
