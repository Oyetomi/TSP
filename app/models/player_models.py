"""
Pydantic models for tennis player analysis data.

These models handle player rankings, recent matches, statistics,
and match prediction data from MatchDataProvider API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, computed_field


class PlayerRankingInfo(BaseModel):
    """Player ranking information for ATP/WTA/UTR rankings."""
    ranking: int
    points: Union[int, float]
    previous_ranking: Optional[int] = Field(None, alias="previousRanking")
    previous_points: Optional[Union[int, float]] = Field(None, alias="previousPoints")
    best_ranking: Optional[int] = Field(None, alias="bestRanking")
    tournaments_played: Optional[int] = Field(None, alias="tournamentsPlayed")
    type: int  # 5 for ATP, 6 for WTA, etc.
    row_name: str = Field(alias="rowName")
    ranking_class: Optional[str] = Field(None, alias="rankingClass")

    class Config:
        populate_by_name = True


class PlayerRankings(BaseModel):
    """Player rankings response containing multiple ranking systems."""
    rankings: List[PlayerRankingInfo]

    @computed_field
    @property
    def atp_ranking(self) -> Optional[int]:
        """Get ATP ranking if available."""
        for ranking in self.rankings:
            if ranking.type == 5:  # ATP ranking type
                return ranking.ranking
        return None

    @computed_field
    @property
    def wta_ranking(self) -> Optional[int]:
        """Get WTA ranking if available."""
        for ranking in self.rankings:
            if ranking.type == 6:  # WTA ranking type
                return ranking.ranking
        return None

    @computed_field
    @property
    def utr_rating(self) -> Optional[float]:
        """Get UTR rating if available."""
        for ranking in self.rankings:
            if ranking.type == 32:  # UTR rating type
                return ranking.points
        return None


class MatchVotes(BaseModel):
    """Community votes for match prediction."""
    vote1: int  # Votes for player 1
    vote2: int  # Votes for player 2
    vote_x: Optional[int] = Field(None, alias="voteX")  # Draw votes (usually null for tennis)

    class Config:
        populate_by_name = True

    @computed_field
    @property
    def total_votes(self) -> int:
        """Total number of votes."""
        return self.vote1 + self.vote2

    @computed_field
    @property
    def player1_percentage(self) -> float:
        """Percentage of votes for player 1."""
        if self.total_votes == 0:
            return 0.0
        return (self.vote1 / self.total_votes) * 100

    @computed_field
    @property
    def player2_percentage(self) -> float:
        """Percentage of votes for player 2."""
        if self.total_votes == 0:
            return 0.0
        return (self.vote2 / self.total_votes) * 100

    @computed_field
    @property
    def favorite(self) -> int:
        """Which player is favored (1 or 2)."""
        if self.vote1 > self.vote2:
            return 1
        elif self.vote2 > self.vote1:
            return 2
        else:
            return 0  # Tie


class VotingData(BaseModel):
    """Complete voting data for a match."""
    vote: MatchVotes
    both_teams_to_score_vote: Optional[Dict[str, int]] = Field(None, alias="bothTeamsToScoreVote")
    first_team_to_score_vote: Optional[Dict[str, int]] = Field(None, alias="firstTeamToScoreVote")
    who_should_have_won_vote: Optional[Dict[str, int]] = Field(None, alias="whoShouldHaveWonVote")

    class Config:
        populate_by_name = True


class PlayerStatistics(BaseModel):
    """Player statistics for a specific surface/condition."""
    matches: int
    ground_type: str = Field(alias="groundType")
    wins: int
    total_serve_attempts: Optional[int] = Field(None, alias="totalServeAttempts")
    aces: Optional[int] = None
    double_faults: Optional[int] = Field(None, alias="doubleFaults")
    first_serve_points_scored: Optional[int] = Field(None, alias="firstServePointsScored")
    first_serve_points_total: Optional[int] = Field(None, alias="firstServePointsTotal")
    first_serve_total: Optional[int] = Field(None, alias="firstServeTotal")
    second_serve_points_scored: Optional[int] = Field(None, alias="secondServePointsScored")
    second_serve_points_total: Optional[int] = Field(None, alias="secondServePointsTotal")
    second_serve_total: Optional[int] = Field(None, alias="secondServeTotal")
    break_points_scored: Optional[int] = Field(None, alias="breakPointsScored")
    break_points_total: Optional[int] = Field(None, alias="breakPointsTotal")
    opponent_break_points_total: Optional[int] = Field(None, alias="opponentBreakPointsTotal")
    opponent_break_points_scored: Optional[int] = Field(None, alias="opponentBreakPointsScored")
    winners_total: Optional[int] = Field(None, alias="winnersTotal")
    unforced_errors_total: Optional[int] = Field(None, alias="unforcedErrorsTotal")
    tiebreaks_won: Optional[int] = Field(None, alias="tiebreaksWon")
    tiebreak_losses: Optional[int] = Field(None, alias="tiebreakLosses")
    tournaments_played: Optional[int] = Field(None, alias="tournamentsPlayed")
    tournaments_won: Optional[int] = Field(None, alias="tournamentsWon")

    class Config:
        populate_by_name = True

    @computed_field
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.matches == 0:
            return 0.0
        return (self.wins / self.matches) * 100

    @computed_field
    @property
    def first_serve_percentage(self) -> Optional[float]:
        """Calculate first serve percentage."""
        if not self.first_serve_total or not self.total_serve_attempts:
            return None
        return (self.first_serve_total / self.total_serve_attempts) * 100

    @computed_field
    @property
    def first_serve_win_percentage(self) -> Optional[float]:
        """Calculate first serve points won percentage."""
        if not self.first_serve_points_total or not self.first_serve_points_scored:
            return None
        return (self.first_serve_points_scored / self.first_serve_points_total) * 100

    @computed_field
    @property
    def break_point_conversion(self) -> Optional[float]:
        """Calculate break point conversion percentage."""
        if not self.break_points_total or not self.break_points_scored:
            return None
        return (self.break_points_scored / self.break_points_total) * 100

    @computed_field
    @property
    def break_point_saved(self) -> Optional[float]:
        """Calculate break points saved percentage."""
        if not self.opponent_break_points_total:
            return None
        saved = self.opponent_break_points_total - (self.opponent_break_points_scored or 0)
        return (saved / self.opponent_break_points_total) * 100


class PlayerYearStatistics(BaseModel):
    """Player statistics for a year broken down by surface."""
    statistics: List[PlayerStatistics]

    @computed_field
    @property
    def total_matches(self) -> int:
        """Total matches across all surfaces."""
        return sum(stat.matches for stat in self.statistics)

    @computed_field
    @property
    def total_wins(self) -> int:
        """Total wins across all surfaces."""
        return sum(stat.wins for stat in self.statistics)

    @computed_field
    @property
    def overall_win_rate(self) -> float:
        """Overall win rate across all surfaces."""
        if self.total_matches == 0:
            return 0.0
        return (self.total_wins / self.total_matches) * 100

    @computed_field
    @property
    def surface_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Breakdown of performance by surface."""
        breakdown = {}
        for stat in self.statistics:
            breakdown[stat.ground_type] = {
                'matches': stat.matches,
                'wins': stat.wins,
                'win_rate': stat.win_rate,
                'tournaments_played': stat.tournaments_played,
                'tournaments_won': stat.tournaments_won
            }
        return breakdown

    def get_surface_stats(self, surface: str) -> Optional[PlayerStatistics]:
        """Get statistics for a specific surface."""
        for stat in self.statistics:
            if surface.lower() in stat.ground_type.lower():
                return stat
        return None


class RecentTournament(BaseModel):
    """Recent tournament information."""
    name: str
    slug: str
    id: int
    category: Optional[Dict[str, Any]] = None
    ground_type: Optional[str] = Field(None, alias="groundType")
    tennis_points: Optional[int] = Field(None, alias="tennisPoints")

    class Config:
        populate_by_name = True


class PlayerRecentTournaments(BaseModel):
    """Player's recent unique tournaments."""
    unique_tournaments: List[RecentTournament] = Field(alias="uniqueTournaments")

    class Config:
        populate_by_name = True


class FormAnalysis(BaseModel):
    """Analysis of player's recent form."""
    player_id: int
    matches_analyzed: int
    wins: int
    losses: int
    win_rate: float
    sets_won: int
    sets_lost: int
    set_win_rate: float
    recent_matches: List[Dict[str, Any]]

    @computed_field
    @property
    def form_rating(self) -> str:
        """Descriptive form rating."""
        if self.win_rate >= 0.8:
            return "Excellent"
        elif self.win_rate >= 0.6:
            return "Good"
        elif self.win_rate >= 0.4:
            return "Average"
        else:
            return "Poor"

    @computed_field
    @property
    def momentum(self) -> str:
        """Recent momentum based on last 3 matches."""
        if len(self.recent_matches) < 3:
            return "Insufficient data"
        
        # Check results of last 3 matches
        recent_results = []
        for match in self.recent_matches[:3]:
            home_team_id = match.get('homeTeam', {}).get('id')
            away_team_id = match.get('awayTeam', {}).get('id')
            winner_code = match.get('winnerCode')
            
            is_home_player = home_team_id == self.player_id
            
            if winner_code == 1 and is_home_player:
                recent_results.append('W')
            elif winner_code == 2 and not is_home_player:
                recent_results.append('W')
            else:
                recent_results.append('L')
        
        wins_in_last_3 = recent_results.count('W')
        
        if wins_in_last_3 == 3:
            return "Hot streak"
        elif wins_in_last_3 == 2:
            return "Strong momentum"
        elif wins_in_last_3 == 1:
            return "Mixed form"
        else:
            return "Cold streak"


class PlayerComparison(BaseModel):
    """Complete comparison between two players for set prediction."""
    comparison_date: datetime
    player1: Dict[str, Any]
    player2: Dict[str, Any]
    prediction_factors: Dict[str, Any]

    @computed_field
    @property
    def recommendation(self) -> Dict[str, Any]:
        """Get match recommendation based on analysis."""
        factors = self.prediction_factors
        
        # Count advantages
        p1_advantages = 0
        p2_advantages = 0
        
        if factors.get('ranking_advantage') == 'player1':
            p1_advantages += 2
        elif factors.get('ranking_advantage') == 'player2':
            p2_advantages += 2
            
        if factors.get('form_advantage') == 'player1':
            p1_advantages += 1
        elif factors.get('form_advantage') == 'player2':
            p2_advantages += 1
        
        # Determine confidence level
        advantage_diff = abs(p1_advantages - p2_advantages)
        if advantage_diff >= 3:
            confidence = "High"
        elif advantage_diff >= 2:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        # Determine favorite
        if p1_advantages > p2_advantages:
            favorite = "player1"
        elif p2_advantages > p1_advantages:
            favorite = "player2"
        else:
            favorite = "uncertain"
        
        return {
            'favorite': favorite,
            'confidence': confidence,
            'player1_score': p1_advantages,
            'player2_score': p2_advantages,
            'factors_analyzed': len([k for k, v in factors.items() if v is not None])
        }

    @computed_field
    @property
    def set_prediction(self) -> Dict[str, Any]:
        """Specific prediction for who wins the most sets."""
        rec = self.recommendation
        
        # Base prediction on overall recommendation
        if rec['favorite'] == 'player1':
            predicted_winner = self.player1['details']['team']['name']
            predicted_sets = "2-1" if rec['confidence'] == 'Low' else "2-0"
        elif rec['favorite'] == 'player2':
            predicted_winner = self.player2['details']['team']['name']
            predicted_sets = "2-1" if rec['confidence'] == 'Low' else "2-0"
        else:
            predicted_winner = "Uncertain"
            predicted_sets = "2-1"
        
        return {
            'predicted_winner': predicted_winner,
            'predicted_score': predicted_sets,
            'confidence': rec['confidence'],
            'reasoning': self._generate_reasoning()
        }
    
    def _generate_reasoning(self) -> List[str]:
        """Generate reasoning for the prediction."""
        reasoning = []
        factors = self.prediction_factors
        
        if factors.get('ranking_advantage'):
            if factors['ranking_advantage'] == 'player1':
                reasoning.append("Player 1 has higher ranking")
            else:
                reasoning.append("Player 2 has higher ranking")
        
        if factors.get('form_advantage'):
            if factors['form_advantage'] == 'player1':
                reasoning.append("Player 1 has better recent form")
            elif factors['form_advantage'] == 'player2':
                reasoning.append("Player 2 has better recent form")
        
        if not reasoning:
            reasoning.append("Close match based on available data")
        
        return reasoning
