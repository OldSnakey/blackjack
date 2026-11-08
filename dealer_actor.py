"""
DealerActor Layered Sprite Compositor and Character Roster.

Provides:
- CharacterProfile metadata for all 8 dealer personas:
  Julian, Tiffany, Malphas, Uriel, Mortimer, Selene, Vladimir, and Dummy.
- Dynamic alpha-compositing across 7 sprite strata:
  0. Shadow (ambient backdrop depth silhouette)
  1. Torso (suit / gown / mantle / armor / robes / mannequin frame)
  2. Neck (collar / neck articulation bridge)
  3. Head (facial structure / hair / horns / halo / top hat)
  4. Eyes (open / half-lidded / closed)
  5. Mouth (neutral / talk / smirk / gasp + phonetic visemes 'a', 'o', 'e', 'f')
  6. Arms (rested / deal sweep / hole-card peek)
- In-memory PhotoImage caching for high-framerate rendering (25-30 FPS).
- High-DPI 1x <-> 2x display scaling.
- Costume switching with backwards-compatible alias normalization and `character_id` property.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).resolve().parent
HAUNTED_ASSETS_DIR = BASE_DIR / "assets" / "haunted"
CHARACTERS_DIR = HAUNTED_ASSETS_DIR / "characters"


@dataclass(frozen=True)
class CostumeVariant:
    costume_id: str
    name: str
    bust_image_key: Optional[str] = None
    audio_cue: Optional[str] = None
    unlock_criteria: str = ""
    unlocked_by_default: bool = False


@dataclass(frozen=True)
class CharacterProfile:
    id: str
    name: str
    title: str
    theme: str
    nameplate_fg: str
    speech_bg: str
    audio_cue: str
    unlock_key: str
    lore: str
    is_puppet: bool = False
    costumes: tuple[CostumeVariant, ...] = ()

    def get_costumes(self) -> tuple[CostumeVariant, ...]:
        if self.costumes:
            return self.costumes
        default_name = f"Classic {self.name}" if self.id in ("julian", "tiffany") else f"Default {self.name}"
        return (
            CostumeVariant(
                costume_id=self.id,
                name=default_name,
                audio_cue=self.audio_cue,
                unlocked_by_default=(self.id in ("julian", "tiffany", "dummy")),
            ),
        )


CHARACTERS: Dict[str, CharacterProfile] = {
    "julian": CharacterProfile(
        id="julian",
        name="Julian",
        title="The Classic Croupier",
        theme="casino",
        nameplate_fg="#ffd700",
        speech_bg="#141014",
        audio_cue="dealer_julian.ogg",
        unlock_key="classic",
        lore="Consummate casino gentleman who deals cards with effortless elegance and calm composure.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="julian",
                name="Classic Tuxedo",
                bust_image_key="bust",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="julian_monte_carlo",
                name="Monte Carlo",
                bust_image_key="bust_monte_carlo",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="julian_high_roller",
                name="High Roller",
                bust_image_key="bust_high_roller",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="julian_emerald",
                name="Emerald Club",
                bust_image_key="bust_emerald",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="julian_bond",
                name="Secret Agent 007",
                bust_image_key="bust_bond",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="julian_godfather",
                name="1920s Speakeasy",
                bust_image_key="bust_godfather",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="julian_maverick",
                name="Wild West Maverick",
                bust_image_key="bust_maverick",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="julian_miami",
                name="80s Miami Vice",
                bust_image_key="bust_miami",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
        ),
    ),
    "malphas": CharacterProfile(
        id="malphas",
        name="Malphas",
        title="☠ The Pit Fiend",
        theme="hell",
        nameplate_fg="#ff1744",
        speech_bg="#140508",
        audio_cue="dealer_malphas.ogg",
        unlock_key="pit_fiend",
        lore="Menacing archfiend whose molten ram horns and smoldering embers crave mortal soul fragments.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="malphas",
                name="Ashen Pit Boss",
                bust_image_key="bust",
                audio_cue="dealer_malphas.ogg",
            ),
            CostumeVariant(
                costume_id="malphas_hellfire",
                name="Hellfire Ember",
                bust_image_key="bust_hellfire",
                audio_cue="dealer_malphas.ogg",
            ),
            CostumeVariant(
                costume_id="malphas_brimstone",
                name="Brimstone Gold",
                bust_image_key="bust_brimstone",
                audio_cue="dealer_malphas.ogg",
            ),
            CostumeVariant(
                costume_id="malphas_abyssal",
                name="Abyssal Void",
                bust_image_key="bust_abyssal",
                audio_cue="dealer_malphas.ogg",
            ),
            CostumeVariant(
                costume_id="malphas_warlord",
                name="Infernal Warlord",
                bust_image_key="bust_warlord",
                audio_cue="dealer_malphas.ogg",
            ),
            CostumeVariant(
                costume_id="malphas_mephisto",
                name="Faustian Gentleman",
                bust_image_key="bust_mephisto",
                audio_cue="dealer_malphas.ogg",
            ),
            CostumeVariant(
                costume_id="malphas_biker",
                name="Hell's Highway",
                bust_image_key="bust_biker",
                audio_cue="dealer_malphas.ogg",
            ),
            CostumeVariant(
                costume_id="malphas_pharaoh",
                name="Underworld Anubis",
                bust_image_key="bust_pharaoh",
                audio_cue="dealer_malphas.ogg",
            ),
        ),
    ),
    "uriel": CharacterProfile(
        id="uriel",
        name="Uriel",
        title="✨ Celestial Seraph",
        theme="celestial",
        nameplate_fg="#00e5ff",
        speech_bg="#0d2b26",
        audio_cue="dealer_uriel.ogg",
        unlock_key="seraph",
        lore="Radiant heavenly messenger whose luminous halo and divine vestments banish ancient infernal curses.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="uriel",
                name="Seraphic Sky",
                bust_image_key="bust",
                audio_cue="dealer_uriel.ogg",
            ),
            CostumeVariant(
                costume_id="uriel_alabaster",
                name="Pearl Alabaster",
                bust_image_key="bust_alabaster",
                audio_cue="dealer_uriel.ogg",
            ),
            CostumeVariant(
                costume_id="uriel_sapphire",
                name="Royal Sapphire",
                bust_image_key="bust_sapphire",
                audio_cue="dealer_uriel.ogg",
            ),
            CostumeVariant(
                costume_id="uriel_obsidian",
                name="Obsidian Vest",
                bust_image_key="bust_obsidian",
                audio_cue="dealer_uriel.ogg",
            ),
            CostumeVariant(
                costume_id="uriel_archangel",
                name="Crusader Battleplate",
                bust_image_key="bust_archangel",
                audio_cue="dealer_uriel.ogg",
            ),
            CostumeVariant(
                costume_id="uriel_olympian",
                name="Olympian Apollo",
                bust_image_key="bust_olympian",
                audio_cue="dealer_uriel.ogg",
            ),
            CostumeVariant(
                costume_id="uriel_pontiff",
                name="Marble Statue",
                bust_image_key="bust_pontiff",
                audio_cue="dealer_uriel.ogg",
            ),
            CostumeVariant(
                costume_id="uriel_fallen",
                name="70s Disco King",
                bust_image_key="bust_fallen",
                audio_cue="dealer_uriel.ogg",
            ),
        ),
    ),
    "mortimer": CharacterProfile(
        id="mortimer",
        name="Mortimer",
        title="🎩 Grim Bones",
        theme="crypt",
        nameplate_fg="#ce93d8",
        speech_bg="#1a0924",
        audio_cue="dealer_mortimer.ogg",
        unlock_key="grim_bones",
        lore="Dapper skeleton croupier sporting a purple silk top hat who dryly chuckles at the roll of the bones.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="mortimer",
                name="Crypt Pinstripe",
                bust_image_key="bust",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="mortimer_baron",
                name="Baron Crimson",
                bust_image_key="bust_baron",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="mortimer_lich",
                name="Soulfire Emerald",
                bust_image_key="bust_lich",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="mortimer_gilded",
                name="Gilded Reaper",
                bust_image_key="bust_gilded",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="mortimer_pirate",
                name="Ghost Pirate Captain",
                bust_image_key="bust_pirate",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="mortimer_mariachi",
                name="Día de los Muertos",
                bust_image_key="bust_mariachi",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="mortimer_jester",
                name="Court of Fools",
                bust_image_key="bust_jester",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="mortimer_reaper",
                name="Hooded Ferryman",
                bust_image_key="bust_reaper",
                audio_cue="dealer_mortimer.ogg",
            ),
        ),
    ),
    "tiffany": CharacterProfile(
        id="tiffany",
        name="Tiffany",
        title="♥ The Velvet Croupier",
        theme="casino",
        nameplate_fg="#ff4081",
        speech_bg="#240a1b",
        audio_cue="dealer_tiffany.ogg",
        unlock_key="tiffany",
        lore="Glamorous and quick-witted croupier whose velvet touch and radiant smile charm even the sharpest card counters.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="tiffany",
                name="Obsidian Velvet",
                bust_image_key="bust",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_sequin",
                name="Sequin Cocktail",
                bust_image_key="bust_sequin",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_rose",
                name="Velvet Corset",
                bust_image_key="bust_rose",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_champagne",
                name="Gold Halter",
                bust_image_key="bust_champagne",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_amethyst",
                name="Midnight Bustier",
                bust_image_key="bust_amethyst",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_bunny",
                name="VIP Bunny Girl",
                bust_image_key="bust_bunny",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_showgirl",
                name="Vegas Showgirl",
                bust_image_key="bust_showgirl",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_cheongsam",
                name="Macau Silk Qipao",
                bust_image_key="bust_cheongsam",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
            CostumeVariant(
                costume_id="tiffany_noir",
                name="Femme Fatale Noir",
                bust_image_key="bust_noir",
                audio_cue="dealer_tiffany.ogg",
                unlocked_by_default=True,
            ),
        ),
    ),
    "selene": CharacterProfile(
        id="selene",
        name="Selene",
        title="⚡ Cyber Croupier",
        theme="cyber",
        nameplate_fg="#00e5ff",
        speech_bg="#0d1a24",
        audio_cue="dealer_tiffany.ogg",
        unlock_key="selene",
        lore="High-tech synth dealer from the year 2088 whose ocular scanner detects split-second card count shifts.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="selene",
                name="Neon Runner",
                bust_image_key="bust",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_chrome",
                name="Liquid Chrome",
                bust_image_key="bust_chrome",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_netrunner",
                name="Cyber Magenta",
                bust_image_key="bust_netrunner",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_arasaka",
                name="Corp Executive",
                bust_image_key="bust_arasaka",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_ghost",
                name="Ghost Protocol",
                bust_image_key="bust_ghost",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_kunoichi",
                name="Cyber Kunoichi",
                bust_image_key="bust_kunoichi",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_valkyrie",
                name="Mecha Valkyrie",
                bust_image_key="bust_valkyrie",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_synthwave",
                name="Retro Arcade Idol",
                bust_image_key="bust_synthwave",
                audio_cue="dealer_tiffany.ogg",
            ),
            CostumeVariant(
                costume_id="selene_bounty",
                name="Void Bounty Hunter",
                bust_image_key="bust_bounty",
                audio_cue="dealer_tiffany.ogg",
            ),
        ),
    ),
    "vladimir": CharacterProfile(
        id="vladimir",
        name="Vladimir",
        title="🩸 Crimson Nocturne",
        theme="crypt",
        nameplate_fg="#e91e63",
        speech_bg="#240a14",
        audio_cue="dealer_mortimer.ogg",
        unlock_key="vladimir",
        lore="Victorian vampire count who has dealt cards for centuries across the shadowy gaming salons of Europe.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="vladimir",
                name="Crimson Nocturne",
                bust_image_key="bust",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="vladimir_nosferatu",
                name="Shadow Count",
                bust_image_key="bust_nosferatu",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="vladimir_royal",
                name="Wallachian Gold",
                bust_image_key="bust_royal",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="vladimir_frost",
                name="Carpathian Frost",
                bust_image_key="bust_frost",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="vladimir_dracul",
                name="Vlad the Impaler",
                bust_image_key="bust_dracul",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="vladimir_phantom",
                name="Opera Phantom",
                bust_image_key="bust_phantom",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="vladimir_alucard",
                name="Crimson Gunslinger",
                bust_image_key="bust_alucard",
                audio_cue="dealer_mortimer.ogg",
            ),
            CostumeVariant(
                costume_id="vladimir_masquerade",
                name="Venetian Casanova",
                bust_image_key="bust_masquerade",
                audio_cue="dealer_mortimer.ogg",
            ),
        ),
    ),
    "professor": CharacterProfile(
        id="professor",
        name="Professor Edward",
        title="🎓 The MIT Card Professor",
        theme="academy",
        nameplate_fg="#80cbc4",
        speech_bg="#0d1f1a",
        audio_cue="dealer_professor.ogg",
        unlock_key="professor",
        lore="Master mathematician and MIT Blackjack Team mentor who turns running counts and true-count ramps into pure science.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="professor",
                name="MIT Seminar Tweed",
                bust_image_key="bust",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
            CostumeVariant(
                costume_id="professor_ivy",
                name="Cambridge Chestnut",
                bust_image_key="bust_ivy",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
            CostumeVariant(
                costume_id="professor_oxford",
                name="Oxford Navy",
                bust_image_key="bust_oxford",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
            CostumeVariant(
                costume_id="professor_vegas",
                name="Vegas Undercover",
                bust_image_key="bust_vegas",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
            CostumeVariant(
                costume_id="professor_vegas_disguise",
                name="Vegas High-Roller",
                bust_image_key="bust_vegas_disguise",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
            CostumeVariant(
                costume_id="professor_sherlock",
                name="Baker Street Detective",
                bust_image_key="bust_sherlock",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
            CostumeVariant(
                costume_id="professor_mad_scientist",
                name="Quantum Lab Coat",
                bust_image_key="bust_mad_scientist",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
            CostumeVariant(
                costume_id="professor_dean",
                name="Grand Chancellor",
                bust_image_key="bust_dean",
                audio_cue="dealer_professor.ogg",
                unlocked_by_default=False,
            ),
        ),
    ),
    "dummy": CharacterProfile(
        id="dummy",
        name="Puppet Dummy",
        title="🧪 Test Puppet Dummy",
        theme="casino",
        nameplate_fg="#00e5ff",
        speech_bg="#0a1520",
        audio_cue="dealer_julian.ogg",
        unlock_key="dummy_test",
        lore="High-contrast multi-layer dummy puppet rigged to verify layer stacking, Z-order, and articulation.",
        is_puppet=True,
        costumes=(
            CostumeVariant(
                costume_id="dummy",
                name="Lab Test Rig",
                audio_cue="dealer_julian.ogg",
                unlocked_by_default=True,
            ),
        ),
    ),
}

COSTUME_ALIASES: Dict[str, str] = {
    "classic": "julian",
    "dealer": "julian",
    "julian_monte_carlo": "julian",
    "julian_high_roller": "julian",
    "julian_emerald": "julian",
    "tiffany": "tiffany",
    "velvet": "tiffany",
    "tiffany_sequin": "tiffany",
    "tiffany_rose": "tiffany",
    "tiffany_champagne": "tiffany",
    "tiffany_amethyst": "tiffany",
    "pit_fiend": "malphas",
    "demon": "malphas",
    "hell": "malphas",
    "malphas_hellfire": "malphas",
    "malphas_brimstone": "malphas",
    "malphas_abyssal": "malphas",
    "seraph": "uriel",
    "angel": "uriel",
    "celestial": "uriel",
    "uriel_alabaster": "uriel",
    "uriel_sapphire": "uriel",
    "uriel_obsidian": "uriel",
    "uriel_sky": "uriel",
    "grim_bones": "mortimer",
    "skeleton": "mortimer",
    "bones": "mortimer",
    "crypt": "mortimer",
    "mortimer_baron": "mortimer",
    "mortimer_lich": "mortimer",
    "mortimer_gilded": "mortimer",
    "selene": "selene",
    "cyber": "selene",
    "cyberpunk": "selene",
    "selene_chrome": "selene",
    "selene_netrunner": "selene",
    "selene_arasaka": "selene",
    "selene_ghost": "selene",
    "vladimir": "vladimir",
    "vampire": "vladimir",
    "blood": "vladimir",
    "nocturne": "vladimir",
    "vladimir_nosferatu": "vladimir",
    "vladimir_royal": "vladimir",
    "vladimir_frost": "vladimir",
    "professor": "professor",
    "professor_classic": "professor",
    "professor_ivy": "professor",
    "professor_oxford": "professor",
    "professor_vegas": "professor",
    "edward": "professor",
    "mit": "professor",
    "coach": "professor",
    "dummy": "dummy",
    "puppet": "dummy",
    "test": "dummy",
}
for _char_key, _char_prof in CHARACTERS.items():
    for _c_var in _char_prof.costumes:
        COSTUME_ALIASES[_c_var.costume_id] = _char_key

VISEME_STATES = ("neutral", "talk", "a", "o", "e", "f", "smirk", "gasp")

CHARACTER_OUTCOME_DIALOGUE: Dict[str, Dict[str, str]] = {
    "julian": {
        "NATURAL_BLACKJACK": "Blackjack! Natural 21 pays 3 to 2. Splendid hand.",
        "DEALER_BUST": "Dealer busts! The table pays all active hands.",
        "PLAYER_WINS": "Winner! Excellent play.",
        "PLAYER_BUST": "Bust! House takes the cards.",
        "DEALER_WINS": "House wins this hand.",
        "PUSH": "Push! Bets are returned.",
        "SURRENDER": "Surrendered. Live to wager another day.",
        "IDLE": "Place your bets, cards on the felt.",
    },
    "tiffany": {
        "NATURAL_BLACKJACK": "Ooh, a Natural 21! Sparkling luck at the velvet table!",
        "DEALER_BUST": "Oops, I went over! Chips are all yours, darling!",
        "PLAYER_WINS": "Beautifully played! You beat my hand fair and square.",
        "PLAYER_BUST": "Oh honey, over 21! Better luck on the next deal.",
        "DEALER_WINS": "The velvet house takes this one! Care to try again?",
        "PUSH": "A clean tie! Your chips stay right where they are.",
        "SURRENDER": "Smart retreat, darling. Save those chips for a hotter hand.",
        "IDLE": "Place your bets, darling! Let's see what the shoe brings.",
    },
    "mortimer": {
        "NATURAL_BLACKJACK": "Cackle! A natural 21—rattled my very ribs!",
        "DEALER_BUST": "Busted my own funny bone! Take your gold, mortal!",
        "PLAYER_WINS": "You outplayed old Grim Bones this round!",
        "PLAYER_BUST": "Dust to dust, bust to bust! Into the crypt your chips go.",
        "DEALER_WINS": "The house of bones always collects its due.",
        "PUSH": "Dead even! Neither grave nor glory claims this hand.",
        "SURRENDER": "Fleeing the reaper early? Half your wager survives.",
        "IDLE": "Step up to the crypt felt and stake your bones!",
    },
    "selene": {
        "NATURAL_BLACKJACK": "21.0 confirmed! Probability matrix breached—3 to 2 payout!",
        "DEALER_BUST": "System overflow on dealer hand! Crediting your terminal.",
        "PLAYER_WINS": "Optimal vector executed. You take the pot, runner.",
        "PLAYER_BUST": "Score exceeded 21! Neural link registers a bust.",
        "DEALER_WINS": "House algorithm prevails. Recalibrate your next wager.",
        "PUSH": "Equilibrium reached. Credits returned to your stack.",
        "SURRENDER": "Tactical abort logged. Fifty percent of stake recovered.",
        "IDLE": "Ocular scanner online. Lock in your credits, runner.",
    },
    "vladimir": {
        "NATURAL_BLACKJACK": "Magnificent! A natural 21—fresh blood on the crimson felt!",
        "DEALER_BUST": "A rare miscalculation... enjoy your spoils tonight.",
        "PLAYER_WINS": "Impressive poise, mortal. You claim this hand.",
        "PLAYER_BUST": "Too greedy! Your hand crumbles into the night.",
        "DEALER_WINS": "The nocturnal house feasts upon your wager.",
        "PUSH": "A stalemate across the centuries. Your stake remains.",
        "SURRENDER": "Yielding to the shadows? Wise—keep half your fortune.",
        "IDLE": "The night is young. Place your wagers on the crimson felt.",
    },
    "malphas": {
        "NATURAL_BLACKJACK": "A natural 21?! Insolent mortal, you test my wrath!",
        "DEALER_BUST": "Arrrgh! The fire consumes me... but only for a moment!",
        "PLAYER_WINS": "Curse your fortune! The flames recoil from your hand!",
        "PLAYER_BUST": "Claimed! Another fragment of your soul burns in the pit!",
        "DEALER_WINS": "The abyss devours your pathetic hand!",
        "PUSH": "A standoff... the abyss is patient.",
        "SURRENDER": "Cowardly retreat! Half your tribute feeds the furnace.",
        "IDLE": "Stake your next breath, mortal!",
    },
    "uriel": {
        "NATURAL_BLACKJACK": "Radiant grace! A natural 21 blessed by the heavens!",
        "DEALER_BUST": "The light yields before your steadfast spirit!",
        "PLAYER_WINS": "Victory shines upon your hand, favored soul.",
        "PLAYER_BUST": "Your reach exceeded the sacred measure of 21.",
        "DEALER_WINS": "The celestial order prevails this round.",
        "PUSH": "Harmony in balance—your offering is returned.",
        "SURRENDER": "Prudent humility preserves half your stake.",
        "IDLE": "Let light guide your wager upon the table.",
    },
    "professor": {
        "NATURAL_BLACKJACK": "Natural 21! Notice how those two high cards just shifted the Running Count by -2.",
        "DEALER_BUST": "A dealer bust—classic high-count payoff when the remaining shoe is rich in tens!",
        "PLAYER_WINS": "Positive expectation realized! Keep tracking those low cards as they leave the shoe.",
        "PLAYER_BUST": "Variance happens, scholar. Check whether the True Count justified that hit.",
        "DEALER_WINS": "The house edge takes this hand, but over a thousand hands, math beats luck.",
        "PUSH": "A statistical standoff. Zero net change to bankroll—stay locked on the Running Count.",
        "SURRENDER": "Disciplined surrender! Saving half your wager on a negative-EV hand is textbook Thorp.",
        "IDLE": "Eyes on the shoe, scholar. Track the Running Count from the very first card.",
    },
    "dummy": {
        "NATURAL_BLACKJACK": "Diagnostic alert: Natural 21 detected! Payout 3 to 2!",
        "DEALER_BUST": "Dealer test rig exceeded 21! Player wins!",
        "PLAYER_WINS": "Player hand victorious. Articulation nominal.",
        "PLAYER_BUST": "Player hand busted over 21. Resetting test state.",
        "DEALER_WINS": "Dealer rig wins this cycle.",
        "PUSH": "Equal scores verified. Push state confirmed.",
        "SURRENDER": "Surrender sequence verified. Half bet refunded.",
        "IDLE": "Place your bets, test rig calibrated.",
    },
}

CHARACTER_TACTICAL_DIALOGUE: Dict[str, Dict[str, str]] = {
    "julian": {
        "RISKY_HIT": "Hitting on a stiff hand? Bold nerve at the felt!",
        "DOUBLE_ELEVEN": "Doubling down on eleven—textbook high-stakes play!",
        "SPLIT_PAIR": "Splitting the pair! Two hands in action now.",
        "INSURANCE_TAKEN": "Insurance placed against the Ace. Prudent hedge.",
    },
    "tiffany": {
        "RISKY_HIT": "Ooh, hitting on that total? You like living dangerously!",
        "DOUBLE_ELEVEN": "Doubling on eleven! Go get that ten, darling!",
        "SPLIT_PAIR": "Double the hands, double the glamour!",
        "INSURANCE_TAKEN": "Tucking away a little insurance? Smart move, honey.",
    },
    "mortimer": {
        "RISKY_HIT": "Hitting that hand?! You're dancing on the grave's edge!",
        "DOUBLE_ELEVEN": "Doubling on eleven! Rattling the bones for a paint card!",
        "SPLIT_PAIR": "Cleaving the pair in twain! Twice the peril!",
        "INSURANCE_TAKEN": "Buying grave insurance against my Ace? Hehehe!",
    },
    "selene": {
        "RISKY_HIT": "Warning: High bust probability on that hit—gutsy call!",
        "DOUBLE_ELEVEN": "Doubling on 11: peak expected-value spike detected!",
        "SPLIT_PAIR": "Bifurcating hand stream into dual parallel threads!",
        "INSURANCE_TAKEN": "Firewall hedge deployed against dealer Ace.",
    },
    "vladimir": {
        "RISKY_HIT": "Tempting fate on a perilous total? I admire your thirst!",
        "DOUBLE_ELEVEN": "Doubling on eleven—striking straight for the jugular!",
        "SPLIT_PAIR": "Dividing your forces into twin fangs upon the felt!",
        "INSURANCE_TAKEN": "A cautious ward against my Ace... let us see if it holds.",
    },
    "malphas": {
        "RISKY_HIT": "Reckless mortal! Hitting on the brink of ruin!",
        "DOUBLE_ELEVEN": "Doubling your stake on eleven?! Feed the inferno!",
        "SPLIT_PAIR": "Two hands?! Twice the soul fragments to burn!",
        "INSURANCE_TAKEN": "No mortal insurance can shield you from the Pit!",
    },
    "uriel": {
        "RISKY_HIT": "Faith guides your hand through a perilous draw!",
        "DOUBLE_ELEVEN": "Doubling upon eleven—fortune favors the righteous!",
        "SPLIT_PAIR": "Two paths diverge in radiant symmetry!",
        "INSURANCE_TAKEN": "A shield of caution raised against the Ace.",
    },
    "professor": {
        "RISKY_HIT": "Hitting a stiff total? Make sure the True Count isn't deeply positive first!",
        "DOUBLE_ELEVEN": "Doubling on eleven! Peak expected value when the shoe is rich in tens.",
        "SPLIT_PAIR": "Splitting the pair—maximizing edge across two independent hands!",
        "INSURANCE_TAKEN": "Insurance is only +EV when the True Count is +3.0 or higher, scholar!",
    },
    "dummy": {
        "RISKY_HIT": "High-risk hit input detected on stiff total!",
        "DOUBLE_ELEVEN": "Double-down on 11 command executed!",
        "SPLIT_PAIR": "Split pair branch activated!",
        "INSURANCE_TAKEN": "Insurance side-bet flag enabled.",
    },
}


def map_char_to_viseme(char: str) -> str:
    """
    Maps an individual character to its corresponding mouth viseme shape:
    - Rounded vowels ('o', 'u', 'w', 'q') -> 'o'
    - Open vowels ('a', 'i', 'y', 'h') -> 'a'
    - Wide dental / palatal consonants & vowels ('e', 'c', 'd', 'g', 'j', 'k', 'l', 'n', 'r', 's', 't', 'z') -> 'e'
    - Labiodental fricatives ('f', 'v') -> 'f'
    - Bilabials ('m', 'b', 'p'), whitespace, and punctuation -> 'neutral'
    - Fallback -> 'talk'
    """
    if not char:
        return "neutral"
    c = char.lower()
    if c in (" ", "\t", "\n", ".", ",", "!", "?", "-", "—", ";", ":", "'", '"', "(", ")", "m", "b", "p"):
        return "neutral"
    if c in ("o", "u", "w", "q"):
        return "o"
    if c in ("a", "i", "y", "h"):
        return "a"
    if c in ("e", "c", "d", "g", "j", "k", "l", "n", "r", "s", "t", "z"):
        return "e"
    if c in ("f", "v"):
        return "f"
    return "talk"


class DealerActor:
    """
    Dynamic 5-layer sprite compositor for the live dealer actor.
    Handles asset caching, layer state assembly, Tkinter PhotoImage caching,
    and responsive 1x / 2x coordinate scaling.
    """

    def __init__(
        self,
        master: Any,
        characters_dir: Optional[Path] = None,
        scale_factor: float = 1.0,
        initial_character: str = "julian",
    ):
        self.master = master
        self.characters_dir = characters_dir or CHARACTERS_DIR
        self.scale_factor = scale_factor

        self.current_character = self._resolve_character_id(initial_character)
        self.eye_state = "open"
        self.mouth_state = "neutral"
        self.arm_state = "rest"

        # Independent multi-layer puppet kinematics offsets (in 2x pixel units)
        self.torso_offset: tuple[int, int] = (0, 0)
        self.head_offset: tuple[int, int] = (0, 0)
        self.arm_offset: tuple[int, int] = (0, 0)
        self.eye_gaze_offset: tuple[int, int] = (0, 0)
        self.current_costume: str = self._resolve_costume_id(self.current_character, initial_character)

        # Asset and composite caches
        self._raw_layers_cache: Dict[str, Image.Image] = {}
        self._cached_composite_pil: Optional[Image.Image] = None
        self._cached_composite_2x_pil: Optional[Image.Image] = None
        self._cached_composite_photo: Optional[ImageTk.PhotoImage] = None

    @property
    def character_id(self) -> str:
        """Returns the active character ID for AnimaleseVoiceEngine and UI callers."""
        return self.current_character

    @staticmethod
    def _resolve_character_id(char_id: str) -> str:
        cid = (char_id or "").lower().strip()
        if cid in CHARACTERS:
            return cid
        return COSTUME_ALIASES.get(cid, "julian")

    @staticmethod
    def _resolve_costume_id(resolved_char: str, raw_costume: Optional[str] = None) -> str:
        cand = (raw_costume or "").lower().strip()
        if not cand:
            return resolved_char
        prof = CHARACTERS.get(resolved_char)
        if prof:
            for c in prof.get_costumes():
                if c.costume_id == cand:
                    return cand
        if cand.startswith(f"{resolved_char}_"):
            return cand
        return resolved_char

    def equip_costume(self, character_id: str, costume_id: Optional[str] = None) -> None:
        """Swaps active character persona and costume variant. Guarantees game state immutability."""
        resolved = self._resolve_character_id(character_id)
        cid = self._resolve_costume_id(resolved, costume_id or character_id)
        changed = False
        if resolved != self.current_character:
            self.current_character = resolved
            changed = True
        if getattr(self, "current_costume", None) != cid:
            self.current_costume = cid
            changed = True
        if changed:
            self._invalidate_composite()

    def set_eye_state(self, state: str) -> None:
        """Sets eye layer: 'open', 'half', or 'closed'."""
        if state not in ("open", "half", "closed"):
            state = "open"
        if self.eye_state != state:
            self.eye_state = state
            self._invalidate_composite()

    def set_mouth_state(self, state: str) -> None:
        """Sets mouth layer: 'neutral', 'talk', 'a', 'o', 'e', 'f', 'smirk', or 'gasp'."""
        if state not in VISEME_STATES:
            state = "neutral"
        if self.mouth_state != state:
            self.mouth_state = state
            self._invalidate_composite()

    def set_mouth_for_char(self, char: str) -> str:
        """Derives phonetic viseme mouth shape from typed character and updates mouth state."""
        viseme = map_char_to_viseme(char)
        self.set_mouth_state(viseme)
        return viseme

    def set_arm_state(self, state: str) -> None:
        """Sets arm layer: 'rest', 'deal', or 'peek'."""
        if state not in ("rest", "deal", "peek"):
            state = "rest"
        if self.arm_state != state:
            self.arm_state = state
            self._invalidate_composite()

    def reset_kinematics(self) -> None:
        """Resets all independent sub-layer offsets and gaze tracking to resting (0, 0)."""
        if (
            self.torso_offset != (0, 0)
            or self.head_offset != (0, 0)
            or self.arm_offset != (0, 0)
            or self.eye_gaze_offset != (0, 0)
        ):
            self.torso_offset = (0, 0)
            self.head_offset = (0, 0)
            self.arm_offset = (0, 0)
            self.eye_gaze_offset = (0, 0)
            self._invalidate_composite()

    def set_layer_offsets(
        self,
        torso_offset: Optional[tuple[int, int]] = None,
        head_offset: Optional[tuple[int, int]] = None,
        arm_offset: Optional[tuple[int, int]] = None,
        eye_gaze_offset: Optional[tuple[int, int]] = None,
    ) -> None:
        """Updates independent sub-layer kinematic offsets (clamped to safe anatomical bounds)."""
        changed = False
        if torso_offset is not None:
            clamped = (max(-6, min(6, int(torso_offset[0]))), max(-6, min(6, int(torso_offset[1]))))
            if clamped != self.torso_offset:
                self.torso_offset = clamped
                changed = True
        if head_offset is not None:
            clamped = (max(-6, min(6, int(head_offset[0]))), max(-6, min(6, int(head_offset[1]))))
            if clamped != self.head_offset:
                self.head_offset = clamped
                changed = True
        if arm_offset is not None:
            clamped = (max(-8, min(8, int(arm_offset[0]))), max(-8, min(8, int(arm_offset[1]))))
            if clamped != self.arm_offset:
                self.arm_offset = clamped
                changed = True
        if eye_gaze_offset is not None:
            clamped = (max(-3, min(3, int(eye_gaze_offset[0]))), max(-2, min(2, int(eye_gaze_offset[1]))))
            if clamped != self.eye_gaze_offset:
                self.eye_gaze_offset = clamped
                changed = True
        if changed:
            self._invalidate_composite()

    def set_gaze_target(self, dx: int = 0, dy: int = 0) -> None:
        """Shifts dealer eye gaze by (dx, dy) pixels toward active cards on the felt."""
        self.set_layer_offsets(eye_gaze_offset=(dx, dy))

    def set_scale(self, scale_factor: float) -> None:
        """Updates scale factor (1.0 vs 2.0) and clears cached images."""
        if self.scale_factor != scale_factor:
            self.scale_factor = scale_factor
            self._raw_layers_cache.clear()
            if hasattr(self, "_bust_photo_cache"):
                self._bust_photo_cache.clear()
            self._invalidate_composite()

    def _invalidate_composite(self) -> None:
        self._cached_composite_pil = None
        self._cached_composite_2x_pil = None
        self._cached_composite_photo = None

    def get_profile(self, character_id: Optional[str] = None) -> CharacterProfile:
        """Returns the CharacterProfile for the current (or specified) character."""
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        return CHARACTERS.get(cid, CHARACTERS["julian"])

    def get_outcome_dialogue(self, outcome: str, character_id: Optional[str] = None) -> str:
        """Returns persona-specific dealer dialogue for a round outcome."""
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        bank = CHARACTER_OUTCOME_DIALOGUE.get(cid, CHARACTER_OUTCOME_DIALOGUE["julian"])
        return bank.get(outcome, bank.get("IDLE", "Place your bets, cards on the felt."))

    def get_tactical_dialogue(self, trigger: str, character_id: Optional[str] = None) -> str:
        """Returns persona-specific dealer reaction to a mid-hand tactical or risky play."""
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        bank = CHARACTER_TACTICAL_DIALOGUE.get(cid, CHARACTER_TACTICAL_DIALOGUE["julian"])
        return bank.get(trigger, "")

    def get_layer_image(self, layer_name: str, force_2x: bool = False) -> Optional[Image.Image]:
        """Public accessor for discrete layer images."""
        return self._get_layer_image(layer_name, force_2x=force_2x)

    def _get_layer_image(self, layer_name: str, force_2x: bool = False) -> Optional[Image.Image]:
        suffix = "_2x" if (force_2x or self.scale_factor > 1.5) else ""
        active_costume = getattr(self, "current_costume", self.current_character) or self.current_character
        cache_key = f"{active_costume}_{layer_name}{suffix}"
        if cache_key in self._raw_layers_cache:
            return self._raw_layers_cache[cache_key]

        char_dir = self.characters_dir / self.current_character
        file_path = None
        if active_costume != self.current_character and active_costume.startswith(f"{self.current_character}_"):
            v_suffix = active_costume[len(self.current_character) :]
            cand_2x = char_dir / f"{layer_name}{v_suffix}{suffix}.png"
            cand_1x = char_dir / f"{layer_name}{v_suffix}.png"
            if cand_2x.exists():
                file_path = cand_2x
            elif cand_1x.exists():
                file_path = cand_1x

        if file_path is None:
            file_path = char_dir / f"{layer_name}{suffix}.png"
            if not file_path.exists():
                # Fallback to 1x file if 2x not found
                file_path = char_dir / f"{layer_name}.png"

        # Viseme graceful degradation fallback for characters without phonetic visemes
        if not file_path.exists() and layer_name.startswith("mouth_") and layer_name not in ("mouth_talk", "mouth_neutral"):
            fallback_path = char_dir / f"mouth_talk{suffix}.png"
            if not fallback_path.exists():
                fallback_path = char_dir / "mouth_talk.png"
            if fallback_path.exists():
                file_path = fallback_path
            else:
                fallback_neutral = char_dir / f"mouth_neutral{suffix}.png"
                if not fallback_neutral.exists():
                    fallback_neutral = char_dir / "mouth_neutral.png"
                if fallback_neutral.exists():
                    file_path = fallback_neutral

        if file_path.exists():
            try:
                img = Image.open(file_path).convert("RGBA")
                self._raw_layers_cache[cache_key] = img
                return img
            except Exception:
                return None
        return None

    @staticmethod
    def _shift_layer(img: Image.Image, dx: int, dy: int, clamp_bottom: bool = False) -> Image.Image:
        """
        Returns a translated copy of `img` shifted by (dx, dy) pixels without wrapping.
        When `clamp_bottom=True` and `dy < 0`, extrudes the bottom-most pixel row into
        the newly exposed bottom rows so the sprite remains flush with the horizon rail.
        """
        if dx == 0 and dy == 0:
            return img
        w, h = img.size
        shifted = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        shifted.paste(img, (dx, dy))
        if clamp_bottom and dy < 0 and h > 0:
            bottom_strip = img.crop((0, h - 1, w, h))
            if dx != 0:
                shifted_strip = Image.new("RGBA", (w, 1), (0, 0, 0, 0))
                shifted_strip.paste(bottom_strip, (dx, 0))
                bottom_strip = shifted_strip
            for fill_y in range(max(0, h + dy), h):
                shifted.paste(bottom_strip, (0, fill_y))
        return shifted

    @staticmethod
    def _apply_intra_sclera_gaze(
        img: Image.Image, gaze_dx: int, gaze_dy: int, use_2x: bool, char_id: str = "julian"
    ) -> Image.Image:
        """
        Shifts only the iris/pupil block inside the sclera aperture
        while keeping eyebrows, glasses frames, and eyelid skin anchored to `head_offset`.
        """
        if gaze_dx == 0 and gaze_dy == 0:
            return img
        s = 2 if use_2x else 1
        gdx = max(-s, min(s, int(round(gaze_dx)) if use_2x else (1 if gaze_dx > 0 else (-1 if gaze_dx < 0 else 0))))
        if gdx == 0:
            return img

        out = img.copy()
        if char_id == "tiffany":
            # Left socket sclera+iris: 1x x=44..49, y=42..44; Right socket: 1x x=62..67, y=42..44
            y0, y1 = 42 * s, 45 * s
            sockets = ((44 * s, 50 * s), (62 * s, 68 * s))
            iris_cols = (1 * s, 5 * s)
        elif char_id == "selene":
            # Left socket sclera+iris: 1x x=40..48, y=47..50; Right socket: 1x x=63..71, y=47..50
            y0, y1 = 47 * s, 51 * s
            sockets = ((40 * s, 49 * s), (63 * s, 72 * s))
            iris_cols = (2 * s, 7 * s)
        elif char_id == "malphas":
            # Left socket sclera+iris: 1x x=45..50, y=37..38; Right socket: 1x x=61..66, y=37..38
            y0, y1 = 37 * s, 39 * s
            sockets = ((45 * s, 51 * s), (61 * s, 67 * s))
            iris_cols = (1 * s, 5 * s)
        elif char_id == "mortimer":
            # Left socket soul-fire pupil: 1x x=45..51, y=36..39; Right socket: 1x x=60..66, y=36..39
            y0, y1 = 36 * s, 40 * s
            sockets = ((45 * s, 52 * s), (60 * s, 67 * s))
            iris_cols = (2 * s, 6 * s)
        elif char_id == "uriel":
            # Left socket sapphire eye: 1x x=44..49, y=45..47; Right socket: 1x x=60..65, y=45..47
            y0, y1 = 45 * s, 48 * s
            sockets = ((44 * s, 50 * s), (60 * s, 66 * s))
            iris_cols = (1 * s, 5 * s)
        elif char_id == "vladimir":
            # Left socket crimson eye: 1x x=45..51, y=35..37; Right socket: 1x x=60..66, y=35..37
            y0, y1 = 35 * s, 38 * s
            sockets = ((45 * s, 52 * s), (60 * s, 67 * s))
            iris_cols = (1 * s, 6 * s)
        else:
            # Left socket 5x2 sclera+iris aperture: 1x x=46..50, y=34..35
            # Right socket 5x2 sclera+iris aperture: 1x x=61..65, y=34..35
            y0, y1 = 34 * s, 36 * s
            sockets = ((46 * s, 51 * s), (61 * s, 66 * s))
            iris_cols = (1 * s, 4 * s)

        for sx0, sx1 in sockets:
            band = img.crop((sx0, y0, sx1, y1))
            for by in range(y1 - y0):
                if char_id == "tiffany":
                    sclera_rgba = (42, 18, 14, 255) if by < s else (252, 252, 252, 255)
                elif char_id == "selene":
                    sclera_rgba = (26, 26, 26, 255) if by < s else (185, 186, 192, 255)
                elif char_id == "malphas":
                    sclera_rgba = (255, 255, 255, 255)
                elif char_id == "mortimer":
                    sclera_rgba = (19, 18, 19, 255)
                elif char_id == "uriel":
                    sclera_rgba = (16, 27, 43, 255) if by < s else (235, 232, 245, 255)
                elif char_id == "vladimir":
                    sclera_rgba = (82, 12, 18, 255)
                else:
                    sclera_rgba = (185, 190, 196, 255) if by < s else (252, 252, 252, 255)
                for bx in range(sx1 - sx0):
                    if char_id in ("tiffany", "selene") and by < s and (bx < s or bx >= sx1 - sx0 - s):
                        continue
                    out.putpixel((sx0 + bx, y0 + by), sclera_rgba)
            for by in range(y1 - y0):
                for bx in range(iris_cols[0], iris_cols[1]):
                    px_rgba = band.getpixel((bx, by))
                    nx = max(sx0, min(sx1 - 1, sx0 + bx + gdx))
                    out.putpixel((nx, y0 + by), px_rgba)
        return out

    def get_composite_image(self, force_2x: bool = False) -> Image.Image:
        """Assembles active 7-layer discrete puppet strata with independent sub-layer offsets."""
        use_2x = force_2x or (self.scale_factor > 1.5)
        if use_2x and not (self.scale_factor > 1.5):
            if getattr(self, "_cached_composite_2x_pil", None) is not None:
                return self._cached_composite_2x_pil
        elif self._cached_composite_pil is not None:
            return self._cached_composite_pil

        # Determine canvas size
        target_size = (224, 224) if use_2x else (112, 112)
        composite = Image.new("RGBA", target_size, (0, 0, 0, 0))

        # Universal discrete 7-layer puppet strata with per-layer kinematics:
        # 1. Shadow -> grounded at (0, 0)
        # 2. Neck   -> torso_offset
        # 3. Torso  -> torso_offset
        # 4. Head   -> head_offset
        # 5. Eyes   -> head_offset (+ intra-sclera or layer eye_gaze_offset when eyes are open)
        # 6. Mouth  -> head_offset
        # 7. Arms   -> torso_offset + arm_offset
        use_intra_sclera = (
            self.current_character
            in (
                "julian",
                "professor",
                "tiffany",
                "selene",
                "malphas",
                "mortimer",
                "uriel",
                "vladimir",
            )
            and getattr(self, "current_costume", "")
            not in (
                "julian_bond",
                "julian_miami",
                "professor_vegas_disguise",
                "malphas_biker",
                "uriel_pontiff",
                "uriel_fallen",
                "vladimir_alucard",
            )
        )
        eye_off = (
            self.head_offset
            if (use_intra_sclera or self.eye_state != "open")
            else (self.head_offset[0] + self.eye_gaze_offset[0], self.head_offset[1] + self.eye_gaze_offset[1])
        )
        arm_off = (self.torso_offset[0] + self.arm_offset[0], self.torso_offset[1] + self.arm_offset[1])

        layer_plan = [
            ("shadow", (0, 0)),
            ("neck", (self.head_offset[0], 0)),
            ("torso", self.torso_offset),
            ("head", self.head_offset),
            (f"eyes_{self.eye_state}", eye_off),
            (f"mouth_{self.mouth_state}", self.head_offset),
            (f"arm_{self.arm_state}", arm_off),
        ]

        scale_mult = 1.0 if use_2x else 0.5
        for lname, (ox, oy) in layer_plan:
            l_img = self._get_layer_image(lname, force_2x=use_2x)
            if l_img is not None:
                if l_img.size != target_size:
                    try:
                        from ui_layout import resolve_pil_resample
                        is_pass, resample = resolve_pil_resample("dealer", l_img.size, target_size)
                    except Exception:
                        is_pass = (l_img.size == target_size)
                        resample = getattr(Image, "Resampling", Image).LANCZOS
                    if not is_pass:
                        l_img = l_img.resize(target_size, resample)
                if lname == "eyes_open" and use_intra_sclera and self.eye_gaze_offset != (0, 0):
                    l_img = self._apply_intra_sclera_gaze(
                        l_img,
                        self.eye_gaze_offset[0],
                        self.eye_gaze_offset[1],
                        use_2x=use_2x,
                        char_id=self.current_character,
                    )
                dx = int(round(ox * scale_mult)) if (ox == 0 or use_2x) else (1 if ox > 0 else -1)
                dy = int(round(oy * scale_mult)) if (oy == 0 or use_2x) else (1 if oy > 0 else -1)
                if dx != 0 or dy != 0:
                    clamp_b = lname == "torso" or lname.startswith("arm_")
                    l_img = self._shift_layer(l_img, dx, dy, clamp_bottom=clamp_b)
                composite.alpha_composite(l_img)

        if use_2x and not (self.scale_factor > 1.5):
            self._cached_composite_2x_pil = composite
        else:
            self._cached_composite_pil = composite
        return composite

    def get_photo_image(self) -> Optional[ImageTk.PhotoImage]:
        """Returns a cached Tkinter PhotoImage for fast canvas or label rendering."""
        if self._cached_composite_photo is not None:
            return self._cached_composite_photo

        pil_img = self.get_composite_image()
        try:
            self._cached_composite_photo = ImageTk.PhotoImage(pil_img, master=self.master)
            return self._cached_composite_photo
        except Exception:
            return None

    def get_bust_image(
        self,
        character_id: Optional[str] = None,
        scale_factor: Optional[float] = None,
        costume_id: Optional[str] = None,
    ) -> Optional[Image.Image]:
        """Returns the pre-rendered bust portrait for a character or costume variant."""
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        resolved_costume = self._resolve_costume_id(
            cid,
            costume_id or character_id or (self.current_costume if cid == self.current_character else cid),
        )
        s = scale_factor if scale_factor is not None else self.scale_factor
        suffix = "_2x" if s > 1.5 else ""
        char_dir = self.characters_dir / cid
        path = None
        if resolved_costume != cid and resolved_costume.startswith(f"{cid}_"):
            v_suffix = resolved_costume[len(cid) :]
            cand_2x = char_dir / f"bust{v_suffix}{suffix}.png"
            cand_1x = char_dir / f"bust{v_suffix}.png"
            if cand_2x.exists():
                path = cand_2x
            elif cand_1x.exists():
                path = cand_1x
        if path is None:
            path = char_dir / f"bust{suffix}.png"
            if not path.exists():
                path = char_dir / "bust.png"
        if path.exists():
            try:
                return Image.open(path).convert("RGBA")
            except Exception:
                return None
        return None

    def get_bust_photo_image(
        self,
        character_id: Optional[str] = None,
        scale_factor: Optional[float] = None,
        costume_id: Optional[str] = None,
    ) -> Optional[ImageTk.PhotoImage]:
        """Returns a cached Tkinter PhotoImage bust for dialog portraits or UI cards."""
        pil_img = self.get_bust_image(character_id, scale_factor, costume_id=costume_id)
        if pil_img is None:
            return None
        if not hasattr(self, "_bust_photo_cache"):
            self._bust_photo_cache = {}
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        resolved_costume = self._resolve_costume_id(
            cid,
            costume_id or character_id or (self.current_costume if cid == self.current_character else cid),
        )
        s = scale_factor if scale_factor is not None else self.scale_factor
        cache_key = f"{resolved_costume}_{s}"
        if cache_key in self._bust_photo_cache:
            return self._bust_photo_cache[cache_key]
        try:
            photo = ImageTk.PhotoImage(pil_img, master=self.master)
            self._bust_photo_cache[cache_key] = photo
            return photo
        except Exception:
            return None

