"""
Pure Domain Model for Track 6: Bankroll-Gated 2.5D Casino Venue Tour (`tour_domain.py`).

Maintains zero Tkinter or PIL dependencies so all salon rules, bankroll gates,
Forgiving/Ironman progression invariants, and mode transitions can be tested
deterministically in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from rules import HouseRules, estimate_house_edge_pct
from save_manager import VenueTourProgress

TOUR_COORDINATOR_COSTUME: str = "julian_monte_carlo"
TOUR_STARTING_BANKROLL: int = 500
TOUR_VICTORY_TARGET: int = 150000
EXORCIST_BOUNTY_AMOUNT: int = 666
TOP_UP_DRAWDOWN_RATIO: float = 0.80


@dataclass(frozen=True)
class TourSalonSpec:
    """Immutable specification for one stop along the 8-Salon Casino Venue Tour."""

    index: int
    salon_id: str
    name: str
    short_name: str
    dealer_id: str
    costume_id: str
    stage_backdrop_theme: str
    entry_bankroll: int
    exit_bankroll: int
    rules: HouseRules
    map_pos: Tuple[int, int]
    landmark_kind: str
    coordinator_intro: str
    host_greeting: str

    @property
    def house_edge_pct(self) -> float:
        return estimate_house_edge_pct(self.rules)


@dataclass(frozen=True)
class TourSettlementResult:
    """Outcome of evaluating a settled Tour hand against salon promotion/bust gates."""

    mode: str
    salon_idx: int
    bankroll_after: int
    promoted: bool = False
    newly_unlocked_salon_idx: Optional[int] = None
    tour_completed: bool = False
    ironman_busted: bool = False
    forgiving_busted: bool = False


@dataclass(frozen=True)
class SalonVisualState:
    """Computed UI presentation state for a single Overworld Map node."""

    index: int
    discovered: bool
    selectable: bool
    is_selected: bool
    is_current_frontier: bool
    velvet_rope_promoted: bool
    forgiving_cleared: bool
    ironman_cleared: bool


SALON_SPECS: Tuple[TourSalonSpec, ...] = (
    TourSalonSpec(
        index=0,
        salon_id="salon_1_training_pit",
        name="Training Pit",
        short_name="Training Pit",
        dealer_id="dummy",
        costume_id="dummy",
        stage_backdrop_theme="casino",
        entry_bankroll=500,
        exit_bankroll=1500,
        rules=HouseRules(
            preset_id="custom",
            deck_count=2,
            dealer_hits_soft_17=False,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="any",
            allow_surrender=True,
            minimum_bet=5,
            maximum_bet=100,
        ),
        map_pos=(96, 240),
        landmark_kind="pit_gazebo",
        coordinator_intro=(
            "Welcome to the Grand Casino Tour! Start at Dummy's $500 Training Pit "
            "and build your stack to $1,500."
        ),
        host_greeting="CLACK-WHIRR! Welcome to the Training Pit—friendly 2-deck S17 rules. Reach $1,500!",
    ),
    TourSalonSpec(
        index=1,
        salon_id="salon_2_golden_floor",
        name="Golden Floor",
        short_name="Golden Floor",
        dealer_id="julian",
        costume_id="julian_high_roller",
        stage_backdrop_theme="casino",
        entry_bankroll=1500,
        exit_bankroll=4000,
        rules=HouseRules(
            preset_id="custom",
            deck_count=4,
            dealer_hits_soft_17=False,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="any",
            allow_surrender=True,
            minimum_bet=10,
            maximum_bet=250,
        ),
        map_pos=(204, 138),
        landmark_kind="grand_rotunda",
        coordinator_intro=(
            "Splendid—$1,500 reached! The Golden Floor opens with 4-deck S17 tables. "
            "Build to $4,000 for the next stop!"
        ),
        host_greeting="Welcome to the Golden Floor. Crisp 4-deck shoe, $10 to $250 limits—play with poise.",
    ),
    TourSalonSpec(
        index=2,
        salon_id="salon_3_downtown_lounge",
        name="Downtown Lounge",
        short_name="Downtown",
        dealer_id="tiffany",
        costume_id="tiffany",
        stage_backdrop_theme="creep",
        entry_bankroll=4000,
        exit_bankroll=8000,
        rules=HouseRules(
            preset_id="custom",
            deck_count=2,
            dealer_hits_soft_17=True,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="any",
            allow_surrender=False,
            minimum_bet=25,
            maximum_bet=400,
        ),
        map_pos=(312, 244),
        landmark_kind="neon_marquee",
        coordinator_intro=(
            "$4,000 banked! Tiffany hosts the 2-deck Downtown Lounge—watch out: "
            "she hits Soft 17 and surrender is off!"
        ),
        host_greeting="Hey high roller! Two decks, no surrender, and I hit Soft 17. Show me $8,000!",
    ),
    TourSalonSpec(
        index=3,
        salon_id="salon_4_faculty_club",
        name="Faculty Club",
        short_name="Faculty Club",
        dealer_id="professor",
        costume_id="professor",
        stage_backdrop_theme="academy",
        entry_bankroll=8000,
        exit_bankroll=15000,
        rules=HouseRules(
            preset_id="custom",
            deck_count=6,
            dealer_hits_soft_17=False,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="any",
            allow_surrender=True,
            minimum_bet=50,
            maximum_bet=700,
        ),
        map_pos=(420, 134),
        landmark_kind="ivy_hall",
        coordinator_intro=(
            "Bravo—$8,000 unlocks Professor Edward's 6-deck Faculty Club! "
            "Use Late Surrender and climb to $15,000."
        ),
        host_greeting="Take a seat at the Faculty Club. Six decks, $50 minimum—trust the math to $15,000.",
    ),
    TourSalonSpec(
        index=4,
        salon_id="salon_5_bone_vault",
        name="Bone Vault",
        short_name="Bone Vault",
        dealer_id="mortimer",
        costume_id="mortimer",
        stage_backdrop_theme="crypt",
        entry_bankroll=15000,
        exit_bankroll=30000,
        rules=HouseRules(
            preset_id="custom",
            deck_count=4,
            dealer_hits_soft_17=True,
            blackjack_payout=(3, 2),
            allow_das=False,
            double_restriction="any",
            allow_surrender=False,
            minimum_bet=100,
            maximum_bet=1500,
        ),
        map_pos=(528, 244),
        landmark_kind="gothic_crypt",
        coordinator_intro=(
            "$15,000 opens Mortimer's Bone Vault! Toughest table on the tour: "
            "H17, no DAS, no Surrender. Reach $30,000!"
        ),
        host_greeting="Heh-heh! Welcome to the Bone Vault—no DAS, no Surrender, $100 minimum. Roll them bones!",
    ),
    TourSalonSpec(
        index=5,
        salon_id="salon_6_neon_cyber_deck",
        name="Neon Cyber-Deck",
        short_name="Cyber-Deck",
        dealer_id="selene",
        costume_id="selene",
        stage_backdrop_theme="cyber",
        entry_bankroll=30000,
        exit_bankroll=50000,
        rules=HouseRules(
            preset_id="custom",
            deck_count=6,
            dealer_hits_soft_17=False,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="9_10_11",
            allow_surrender=False,
            minimum_bet=200,
            maximum_bet=2000,
        ),
        map_pos=(636, 134),
        landmark_kind="cyber_spire",
        coordinator_intro=(
            "$30,000 unlocks Selene's Neon Cyber-Deck! Doubles are restricted to "
            "hard 9, 10, and 11. Climb to $50,000!"
        ),
        host_greeting="Optics locked. Doubles restricted to 9–11 on this 6-deck grid. Target: $50,000.",
    ),
    TourSalonSpec(
        index=6,
        salon_id="salon_7_crimson_salon",
        name="Crimson Salon",
        short_name="Crimson Salon",
        dealer_id="vladimir",
        costume_id="vladimir",
        stage_backdrop_theme="hell",
        entry_bankroll=50000,
        exit_bankroll=75000,
        rules=HouseRules(
            preset_id="custom",
            deck_count=6,
            dealer_hits_soft_17=True,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="any",
            allow_surrender=True,
            minimum_bet=250,
            maximum_bet=2500,
        ),
        map_pos=(740, 238),
        landmark_kind="crimson_manor",
        coordinator_intro=(
            "$50,000! Count Vladimir hosts the Crimson Salon—$250 min with H17 "
            "and Late Surrender. Reach $75,000!"
        ),
        host_greeting="Good evening. Few mortals bring $50,000 to my Crimson Salon. Prove your nerve to $75,000.",
    ),
    TourSalonSpec(
        index=7,
        salon_id="salon_8_sanctum_of_light",
        name="Sanctum of Light",
        short_name="Sanctum",
        dealer_id="uriel",
        costume_id="uriel",
        stage_backdrop_theme="celestial",
        entry_bankroll=75000,
        exit_bankroll=150000,
        rules=HouseRules(
            preset_id="custom",
            deck_count=1,
            dealer_hits_soft_17=False,
            blackjack_payout=(3, 2),
            allow_das=False,
            double_restriction="10_11",
            allow_surrender=False,
            minimum_bet=500,
            maximum_bet=5000,
        ),
        map_pos=(794, 110),
        landmark_kind="celestial_sanctum",
        coordinator_intro=(
            "The summit: Uriel's Sanctum of Light! Reno single-deck ($500–$5,000, "
            "10–11 double). Reach $150,000 to win!"
        ),
        host_greeting="Step into the Sanctum of Light. One pure deck, $500 minimum—ascend to $150,000!",
    ),
)


def get_salon_spec(index: int) -> TourSalonSpec:
    clamped = max(0, min(len(SALON_SPECS) - 1, int(index)))
    return SALON_SPECS[clamped]


def get_forgiving_frontier_idx(progress: VenueTourProgress) -> int:
    """Returns the highest unlocked salon index (0..7) in Standard (Forgiving) Mode."""
    return min(len(SALON_SPECS) - 1, max(0, int(progress.forgiving_salons_cleared)))


def get_forgiving_checkpoint_floor(progress: VenueTourProgress) -> int:
    """Returns the ratcheted entry-bankroll floor for the highest unlocked Standard salon."""
    frontier_idx = get_forgiving_frontier_idx(progress)
    return SALON_SPECS[frontier_idx].entry_bankroll


def get_top_up_threshold(progress: VenueTourProgress) -> int:
    """Returns the maximum bankroll at which Standard Mode Top-Up becomes active (80% of floor)."""
    floor_amt = get_forgiving_checkpoint_floor(progress)
    return int(floor_amt * TOP_UP_DRAWDOWN_RATIO)


def can_top_up_forgiving(progress: VenueTourProgress) -> bool:
    """
    Returns True if Standard Mode Top-Up is permitted:
    - Active mode must be 'forgiving'
    - forgiving_bankroll <= 80% of checkpoint floor (prevents Hand-1 freeroll count-fishing)
    """
    if progress.active_mode != "forgiving":
        return False
    return int(progress.forgiving_bankroll) <= get_top_up_threshold(progress)


def apply_forgiving_top_up(progress: VenueTourProgress) -> bool:
    """Restores forgiving_bankroll to checkpoint floor and increments forgiving_rebuys."""
    if not can_top_up_forgiving(progress):
        return False
    floor_amt = get_forgiving_checkpoint_floor(progress)
    progress.forgiving_bankroll = floor_amt
    progress.forgiving_rebuys = max(0, int(progress.forgiving_rebuys)) + 1
    return True


def get_active_tour_bankroll(progress: VenueTourProgress) -> int:
    if progress.active_mode == "ironman":
        return max(0, int(progress.ironman_bankroll))
    return max(0, int(progress.forgiving_bankroll))


def set_active_tour_bankroll(progress: VenueTourProgress, amount: int) -> None:
    clean = max(0, int(amount))
    if progress.active_mode == "ironman":
        progress.ironman_bankroll = clean
    else:
        progress.forgiving_bankroll = clean


def _is_forgiving_frontier_capped(progress: VenueTourProgress, salon_idx: int) -> bool:
    """
    Returns True when Standard Mode has NOT yet been completed and the player's bankroll
    already meets or exceeds their active Frontier Salon's exit target, roping off earlier
    lower-edge salons so they cannot farm $150k+ in Salon 1 before clearing the Frontier.
    """
    if progress.active_mode != "forgiving":
        return False
    if bool(progress.forgiving_completed) or int(progress.forgiving_salons_cleared) >= len(SALON_SPECS):
        return False
    frontier_idx = get_forgiving_frontier_idx(progress)
    if salon_idx >= frontier_idx:
        return False
    return int(progress.forgiving_bankroll) >= SALON_SPECS[frontier_idx].exit_bankroll


def get_active_salon_index(progress: VenueTourProgress) -> int:
    """Returns the currently focused/playable salon index (0..7) for the active mode."""
    if progress.active_mode == "ironman":
        if progress.ironman_stage_idx >= len(SALON_SPECS):
            return len(SALON_SPECS) - 1
        return max(0, min(len(SALON_SPECS) - 1, int(progress.ironman_stage_idx)))
    max_sel = get_forgiving_frontier_idx(progress)
    sel = max(0, min(max_sel, int(progress.forgiving_selected_idx)))
    if _is_forgiving_frontier_capped(progress, sel):
        return max_sel
    return sel


def can_select_salon(progress: VenueTourProgress, salon_idx: int) -> bool:
    """
    Checks whether `salon_idx` (0..7) can be entered in the active mode:
    - Standard ('forgiving'): any unlocked salon 0 .. min(7, forgiving_salons_cleared),
      except earlier salons when `forgiving_bankroll >= frontier.exit_bankroll` during an
      uncompleted climb (all 8 salons open permanently once `forgiving_completed`).
    - Ironman ('ironman'): strictly `salon_idx == ironman_stage_idx` during an active climb
      (earlier salons are velvet-roped as 'PROMOTED'), or any salon 0..7 once `ironman_stage_idx >= 8`.
    """
    if not (0 <= salon_idx < len(SALON_SPECS)):
        return False
    if progress.active_mode == "ironman":
        if int(progress.ironman_stage_idx) >= len(SALON_SPECS):
            return True
        return salon_idx == int(progress.ironman_stage_idx)
    if bool(progress.forgiving_completed) or int(progress.forgiving_salons_cleared) >= len(SALON_SPECS):
        return True
    if _is_forgiving_frontier_capped(progress, salon_idx):
        return False
    return salon_idx <= get_forgiving_frontier_idx(progress)


def switch_tour_mode(progress: VenueTourProgress, mode: str) -> bool:
    """Switches non-destructively between 'forgiving' and 'ironman' without altering either slot."""
    if mode not in ("forgiving", "ironman"):
        return False
    progress.active_mode = mode
    return True


def reset_ironman_run(progress: VenueTourProgress) -> None:
    """Starts a fresh Ironman gauntlet climb from Salon 1 ($500) while preserving permanent stamps."""
    if int(progress.ironman_stage_idx) > 0 or int(progress.ironman_bankroll) != TOUR_STARTING_BANKROLL:
        progress.ironman_runs_attempted = max(0, int(progress.ironman_runs_attempted)) + 1
    progress.ironman_bankroll = TOUR_STARTING_BANKROLL
    progress.ironman_stage_idx = 0


def get_discovered_salon_count(progress: VenueTourProgress) -> int:
    """
    Returns how many salons (1..8) have ever been visually unveiled across either mode,
    guaranteeing that toggling into Ironman never reverts discovered salons to '???'.
    """
    highest_cleared = max(int(progress.forgiving_salons_cleared), int(progress.ironman_salons_cleared))
    return max(1, min(len(SALON_SPECS), highest_cleared + 1))


def get_salon_visual_state(
    progress: VenueTourProgress,
    salon_idx: int,
    focused_idx: Optional[int] = None,
) -> SalonVisualState:
    """Computes the Overworld Map visual state for `salon_idx`."""
    discovered_count = get_discovered_salon_count(progress)
    discovered = salon_idx < discovered_count
    selectable = can_select_salon(progress, salon_idx)
    sel_idx = get_active_salon_index(progress) if focused_idx is None else int(focused_idx)
    is_ironman = progress.active_mode == "ironman"
    velvet_rope = (
        (is_ironman and int(progress.ironman_stage_idx) < len(SALON_SPECS) and salon_idx < int(progress.ironman_stage_idx))
        or _is_forgiving_frontier_capped(progress, salon_idx)
    )
    frontier_idx = (
        min(len(SALON_SPECS) - 1, int(progress.ironman_stage_idx))
        if is_ironman
        else get_forgiving_frontier_idx(progress)
    )
    return SalonVisualState(
        index=salon_idx,
        discovered=discovered,
        selectable=selectable,
        is_selected=(salon_idx == sel_idx),
        is_current_frontier=(salon_idx == frontier_idx) and (
            (int(progress.ironman_stage_idx) < len(SALON_SPECS))
            if is_ironman
            else (int(progress.forgiving_salons_cleared) < len(SALON_SPECS))
        ),
        velvet_rope_promoted=velvet_rope,
        forgiving_cleared=(salon_idx < int(progress.forgiving_salons_cleared)),
        ironman_cleared=(salon_idx < int(progress.ironman_salons_cleared)),
    )


def evaluate_tour_settlement(
    progress: VenueTourProgress,
    active_salon_idx: int,
    new_bankroll: int,
    round_start_bankroll: Optional[int] = None,
) -> TourSettlementResult:
    """
    Updates `progress` after a Tour hand settles at `new_bankroll` inside `active_salon_idx`.
    Enforces:
    - Frontier residency: advancing salon unlocks/stamps requires playing inside the active frontier salon.
    - Net-profit promotion guard: when `round_start_bankroll` is supplied, advancing requires
      winning net profit on the promoting hand (`clean_br > round_start_bankroll`), preventing
      min-bet loss/push domino skips.
    - Ironman $0 bust: resets `ironman_bankroll = 500` and `ironman_stage_idx = 0` while preserving
      `ironman_salons_cleared` permanently.
    """
    clean_br = max(0, int(new_bankroll))
    salon = get_salon_spec(active_salon_idx)
    won_net_profit = (round_start_bankroll is None) or (clean_br > int(round_start_bankroll))

    if progress.active_mode == "ironman":
        progress.ironman_bankroll = clean_br
        if clean_br <= 0:
            progress.ironman_bankroll = TOUR_STARTING_BANKROLL
            progress.ironman_stage_idx = 0
            progress.ironman_runs_attempted = max(0, int(progress.ironman_runs_attempted)) + 1
            return TourSettlementResult(
                mode="ironman",
                salon_idx=salon.index,
                bankroll_after=progress.ironman_bankroll,
                ironman_busted=True,
            )

        if (
            salon.index == int(progress.ironman_stage_idx)
            and clean_br >= salon.exit_bankroll
            and won_net_profit
        ):
            next_stage = salon.index + 1
            progress.ironman_stage_idx = min(len(SALON_SPECS), next_stage)
            progress.ironman_salons_cleared = max(int(progress.ironman_salons_cleared), progress.ironman_stage_idx)
            completed = progress.ironman_stage_idx >= len(SALON_SPECS)
            if completed:
                progress.ironman_completed = True
            return TourSettlementResult(
                mode="ironman",
                salon_idx=salon.index,
                bankroll_after=clean_br,
                promoted=True,
                newly_unlocked_salon_idx=next_stage if next_stage < len(SALON_SPECS) else None,
                tour_completed=completed,
            )

        return TourSettlementResult(
            mode="ironman",
            salon_idx=salon.index,
            bankroll_after=clean_br,
        )

    # Standard (Forgiving) Mode
    progress.forgiving_bankroll = clean_br
    if clean_br <= 0:
        return TourSettlementResult(
            mode="forgiving",
            salon_idx=salon.index,
            bankroll_after=0,
            forgiving_busted=True,
        )

    if (
        int(progress.forgiving_salons_cleared) < len(SALON_SPECS)
        and salon.index == int(progress.forgiving_salons_cleared)
        and clean_br >= salon.exit_bankroll
        and won_net_profit
    ):
        next_cleared = salon.index + 1
        progress.forgiving_salons_cleared = min(len(SALON_SPECS), next_cleared)
        completed = progress.forgiving_salons_cleared >= len(SALON_SPECS)
        if completed:
            progress.forgiving_completed = True
            progress.forgiving_selected_idx = len(SALON_SPECS) - 1
        else:
            progress.forgiving_selected_idx = next_cleared
        return TourSettlementResult(
            mode="forgiving",
            salon_idx=salon.index,
            bankroll_after=clean_br,
            promoted=True,
            newly_unlocked_salon_idx=next_cleared if next_cleared < len(SALON_SPECS) else None,
            tour_completed=completed,
        )

    return TourSettlementResult(
        mode="forgiving",
        salon_idx=salon.index,
        bankroll_after=clean_br,
    )

