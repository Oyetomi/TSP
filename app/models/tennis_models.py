"""
Pydantic models for tennis data from MatchDataProvider API.

Based on the analyzed structure from MatchDataProvider scheduled events endpoint.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, computed_field


class Country(BaseModel):
    """Player country information."""
    alpha2: Optional[str] = None
    alpha3: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None


class PlayerTeamInfo(BaseModel):
    """Player team information."""
    id: Optional[int] = None


class TeamColors(BaseModel):
    """Team color scheme."""
    primary: str
    secondary: str
    text: str


class Player(BaseModel):
    """Tennis player model."""
    id: int
    name: str
    slug: str
    short_name: Optional[str] = Field(None, alias="shortName")
    gender: Optional[str] = None
    name_code: str = Field(alias="nameCode")
    user_count: Optional[int] = Field(None, alias="userCount")
    country: Optional[Country] = None
    player_team_info: Optional[PlayerTeamInfo] = Field(None, alias="playerTeamInfo")
    team_colors: TeamColors = Field(alias="teamColors")
    disabled: bool = False
    national: bool = False
    type: int = 1

    class Config:
        populate_by_name = True


class Sport(BaseModel):
    """Sport information."""
    id: int
    name: str
    slug: str


class Category(BaseModel):
    """Tournament category (ATP, WTA, etc)."""
    id: int
    name: str
    slug: str
    flag: str
    sport: Sport


class UniqueTournament(BaseModel):
    """Unique tournament details."""
    id: int
    name: str
    slug: str
    category: Category
    user_count: int = Field(alias="userCount")
    ground_type: Optional[str] = Field(None, alias="groundType")
    tennis_points: Optional[int] = Field(None, alias="tennisPoints")
    has_performance_graph_feature: bool = Field(alias="hasPerformanceGraphFeature")
    has_event_player_statistics: bool = Field(alias="hasEventPlayerStatistics")
    display_inverse_home_away_teams: bool = Field(alias="displayInverseHomeAwayTeams")

    class Config:
        populate_by_name = True


class Tournament(BaseModel):
    """Tournament information."""
    id: int
    name: str
    slug: str
    category: Category
    unique_tournament: UniqueTournament = Field(alias="uniqueTournament")
    priority: int = 0

    class Config:
        populate_by_name = True


class Season(BaseModel):
    """Tournament season."""
    id: int
    name: str
    year: str
    editor: bool = False


class RoundInfo(BaseModel):
    """Match round information."""
    round: int
    name: Optional[str] = None
    cup_round_type: Optional[int] = Field(None, alias="cupRoundType")

    class Config:
        populate_by_name = True


class MatchStatus(BaseModel):
    """Match status information."""
    code: int
    description: str
    type: str

    @computed_field
    @property
    def is_finished(self) -> bool:
        """Check if match is finished."""
        return self.type == "finished"

    @computed_field
    @property
    def is_in_progress(self) -> bool:
        """Check if match is in progress."""
        return self.type == "inprogress"

    @computed_field
    @property
    def is_not_started(self) -> bool:
        """Check if match hasn't started yet."""
        return self.type == "notstarted"


class Score(BaseModel):
    """Tennis match score."""
    current: int = 0
    display: int = 0
    period1: Optional[int] = None
    period2: Optional[int] = None
    period3: Optional[int] = None
    period4: Optional[int] = None
    period5: Optional[int] = None
    period1_tie_break: Optional[int] = Field(None, alias="period1TieBreak")
    period2_tie_break: Optional[int] = Field(None, alias="period2TieBreak")
    period3_tie_break: Optional[int] = Field(None, alias="period3TieBreak")
    period4_tie_break: Optional[int] = Field(None, alias="period4TieBreak")
    period5_tie_break: Optional[int] = Field(None, alias="period5TieBreak")
    point: Optional[str] = None

    class Config:
        populate_by_name = True

    @computed_field
    @property
    def sets_won(self) -> int:
        """Calculate number of sets won."""
        sets = [self.period1, self.period2, self.period3, self.period4, self.period5]
        return sum(1 for set_score in sets if set_score is not None and set_score > 0)

    @computed_field
    @property
    def games_in_sets(self) -> List[int]:
        """Get games won in each set."""
        return [
            score for score in [
                self.period1, self.period2, self.period3, 
                self.period4, self.period5
            ] if score is not None
        ]


class TimeInfo(BaseModel):
    """Match timing information."""
    current_period_start_timestamp: Optional[int] = Field(None, alias="currentPeriodStartTimestamp")

    class Config:
        populate_by_name = True

    @computed_field
    @property
    def current_period_start_time(self) -> Optional[datetime]:
        """Convert timestamp to datetime."""
        if self.current_period_start_timestamp:
            return datetime.fromtimestamp(self.current_period_start_timestamp)
        return None


class Changes(BaseModel):
    """Match changes information."""
    changes: List[str] = []
    change_timestamp: int = Field(alias="changeTimestamp")

    class Config:
        populate_by_name = True


class Periods(BaseModel):
    """Match periods definition."""
    point: str = "Game"
    current: str = "Match"
    period1: str = "1st set"
    period2: str = "2nd set"
    period3: str = "3rd set"
    period4: str = "4th set"
    period5: str = "5th set"


class TennisEvent(BaseModel):
    """Complete tennis event/match model."""
    id: int
    slug: str
    custom_id: str = Field(alias="customId")
    start_timestamp: int = Field(alias="startTimestamp")
    
    # Tournament and match info
    tournament: Tournament
    season: Season
    round_info: Optional[RoundInfo] = Field(None, alias="roundInfo")
    
    # Players
    home_team: Player = Field(alias="homeTeam")
    away_team: Player = Field(alias="awayTeam")
    first_to_serve: Optional[int] = Field(None, alias="firstToServe")
    
    # Match status and scores
    status: MatchStatus
    home_score: Optional[Score] = Field(None, alias="homeScore")
    away_score: Optional[Score] = Field(None, alias="awayScore")
    
    # Match details
    ground_type: Optional[str] = Field(None, alias="groundType")
    time: Optional[TimeInfo] = None
    changes: Optional[Changes] = None
    periods: Optional[Periods] = None
    last_period: Optional[str] = Field(None, alias="lastPeriod")
    
    # Metadata
    has_global_highlights: bool = Field(False, alias="hasGlobalHighlights")
    crowdsourcing_data_display_enabled: bool = Field(False, alias="crowdsourcingDataDisplayEnabled")
    final_result_only: bool = Field(False, alias="finalResultOnly")
    feed_locked: bool = Field(False, alias="feedLocked")
    is_editor: bool = Field(False, alias="isEditor")

    class Config:
        populate_by_name = True

    @computed_field
    @property
    def start_time(self) -> datetime:
        """Convert start timestamp to datetime."""
        return datetime.fromtimestamp(self.start_timestamp)

    @computed_field
    @property
    def match_summary(self) -> str:
        """Get a summary string of the match."""
        return f"{self.home_team.name} vs {self.away_team.name} - {self.status.description}"

    @computed_field
    @property
    def is_atp(self) -> bool:
        """Check if this is an ATP tournament."""
        return self.tournament.category.slug == "atp"

    @computed_field
    @property
    def is_wta(self) -> bool:
        """Check if this is a WTA tournament."""
        return self.tournament.category.slug == "wta"

    @computed_field
    @property
    def tournament_level(self) -> str:
        """Get tournament level based on points."""
        points = self.tournament.unique_tournament.tennis_points
        if not points:
            return "Other"
        if points >= 2000:
            return "Grand Slam"
        elif points >= 1000:
            return "Masters 1000"
        elif points >= 500:
            return "ATP 500"
        elif points >= 250:
            return "ATP 250"
        else:
            return "Other"


class TennisEventResponse(BaseModel):
    """Response model for MatchDataProvider tennis events API."""
    events: List[TennisEvent]

    @computed_field
    @property
    def total_events(self) -> int:
        """Total number of events."""
        return len(self.events)

    @computed_field
    @property
    def ongoing_matches(self) -> List[TennisEvent]:
        """Get matches that are currently in progress."""
        return [event for event in self.events if event.status.is_in_progress]

    @computed_field
    @property
    def upcoming_matches(self) -> List[TennisEvent]:
        """Get matches that haven't started yet."""
        return [event for event in self.events if event.status.is_not_started]

    @computed_field
    @property
    def finished_matches(self) -> List[TennisEvent]:
        """Get finished matches."""
        return [event for event in self.events if event.status.is_finished]
