"""
Match Analysis API router for tennis set prediction.

This router provides endpoints for analyzing individual matches,
comparing players, and predicting set outcomes.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from ..models.player_models import (
    PlayerRankings, PlayerYearStatistics, FormAnalysis, 
    PlayerComparison, VotingData
)
from ..services.player_analysis_service import PlayerAnalysisService, MatchDataProviderServiceError


# Response models
class MatchAnalysisResponse(BaseModel):
    """Complete match analysis for set prediction."""
    event_id: int
    player1_id: int
    player2_id: int
    player1_name: str
    player2_name: str
    analysis_date: datetime
    player1_analysis: Dict[str, Any]
    player2_analysis: Dict[str, Any]
    head_to_head: Optional[Dict[str, Any]]
    prediction: Dict[str, Any]
    confidence: str
    voting_data: Optional[Dict[str, Any]]


class PlayerSummary(BaseModel):
    """Summary of player information for quick analysis."""
    id: int
    name: str
    ranking: Optional[int]
    country: str
    recent_form: Dict[str, Any]
    surface_preference: Optional[str]


class SetPredictionResponse(BaseModel):
    """Set prediction response."""
    match_id: int
    predicted_winner: str
    predicted_score: str
    confidence_level: str
    key_factors: List[str]
    player_advantages: Dict[str, List[str]]
    recommended_bet: Optional[str] = None


class SurfaceAnalysis(BaseModel):
    """Surface-specific analysis for players."""
    surface: str
    player1_stats: Optional[Dict[str, Any]]
    player2_stats: Optional[Dict[str, Any]]
    surface_advantage: Optional[str]


# Initialize router
match_analysis_router = APIRouter(prefix="/match-analysis", tags=["match-analysis"])

# Initialize service
analysis_service = PlayerAnalysisService()


@match_analysis_router.get(
    "/player/{player_id}/rankings",
    response_model=Dict[str, Any],
    summary="Get player rankings",
    description="Get ATP/WTA/UTR rankings for a specific player."
)
async def get_player_rankings(
    player_id: int = Path(..., description="MatchDataProvider player ID")
) -> Dict[str, Any]:
    """Get player rankings information."""
    try:
        rankings = analysis_service.get_player_rankings(player_id)
        return rankings
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/player/{player_id}/recent-form",
    response_model=Dict[str, Any],
    summary="Get player recent form analysis",
    description="Analyze player's recent form based on last N matches (singles only) with optional opponent ranking context."
)
async def get_player_form(
    player_id: int = Path(..., description="MatchDataProvider player ID"),
    num_matches: int = Query(10, description="Number of recent matches to analyze", ge=1, le=50),
    opponent_ranking: Optional[int] = Query(None, description="Opponent's ATP ranking for contextual analysis")
) -> Dict[str, Any]:
    """Get player's recent form analysis with enhanced set performance evaluation."""
    try:
        form_analysis = analysis_service.analyze_recent_form(player_id, num_matches, opponent_ranking)
        return form_analysis
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/player/{player_id}/statistics/{year}",
    response_model=Dict[str, Any],
    summary="Get player yearly statistics",
    description="Get player statistics broken down by surface for a specific year."
)
async def get_player_statistics(
    player_id: int = Path(..., description="MatchDataProvider player ID"),
    year: int = Path(..., description="Year for statistics")
) -> Dict[str, Any]:
    """Get player yearly statistics."""
    try:
        statistics = analysis_service.get_player_year_statistics(player_id, year)
        return statistics
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/player/{player_id}/details",
    response_model=Dict[str, Any],
    summary="Get player detailed information",
    description="Get comprehensive player information including ranking, country, etc."
)
async def get_player_details(
    player_id: int = Path(..., description="MatchDataProvider player ID")
) -> Dict[str, Any]:
    """Get detailed player information."""
    try:
        details = analysis_service.get_player_details(player_id)
        return details
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/match/{event_id}/votes",
    response_model=Dict[str, Any],
    summary="Get match voting predictions",
    description="Get community votes and predictions for who will win the match."
)
async def get_match_votes(
    event_id: int = Path(..., description="MatchDataProvider event ID")
) -> Dict[str, Any]:
    """Get match voting data."""
    try:
        votes = analysis_service.get_match_votes(event_id)
        return votes
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/compare/{player1_id}/{player2_id}",
    response_model=Dict[str, Any],
    summary="Compare two players for match prediction",
    description="Get comprehensive comparison between two players for set prediction analysis."
)
async def compare_players(
    player1_id: int = Path(..., description="First player's MatchDataProvider ID"),
    player2_id: int = Path(..., description="Second player's MatchDataProvider ID")
) -> Dict[str, Any]:
    """Compare two players for match prediction."""
    try:
        comparison = analysis_service.compare_players_for_set_prediction(player1_id, player2_id)
        return comparison
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/predict-set/{player1_id}/{player2_id}",
    response_model=SetPredictionResponse,
    summary="Predict set outcome between two players",
    description="Get set prediction with confidence level and key factors."
)
async def predict_set_outcome(
    player1_id: int = Path(..., description="First player's MatchDataProvider ID"),
    player2_id: int = Path(..., description="Second player's MatchDataProvider ID"),
    surface: Optional[str] = Query(None, description="Court surface (hardcourt, clay, grass)"),
    include_voting: bool = Query(False, description="Include community voting data if available"),
    event_id: Optional[int] = Query(None, description="Event ID for voting data")
) -> SetPredictionResponse:
    """Predict set outcome between two players."""
    try:
        # Get comprehensive comparison
        comparison = analysis_service.compare_players_for_set_prediction(player1_id, player2_id)
        
        # Extract player names
        player1_name = comparison['player1']['details']['team']['name']
        player2_name = comparison['player2']['details']['team']['name']
        
        # Get prediction from comparison
        if hasattr(comparison, 'set_prediction'):
            prediction = comparison.set_prediction
        else:
            # Manual prediction logic
            factors = comparison.get('prediction_factors', {})
            rec = factors.get('recommendation', 'uncertain')
            
            if rec == 'player1':
                predicted_winner = player1_name
                predicted_score = "2-1"
            elif rec == 'player2':
                predicted_winner = player2_name
                predicted_score = "2-1"
            else:
                predicted_winner = "Uncertain"
                predicted_score = "2-1"
            
            prediction = {
                'predicted_winner': predicted_winner,
                'predicted_score': predicted_score,
                'confidence': 'Medium'
            }
        
        # Generate key factors
        key_factors = []
        if factors.get('ranking_advantage'):
            if factors['ranking_advantage'] == 'player1':
                key_factors.append(f"{player1_name} has higher ranking")
            else:
                key_factors.append(f"{player2_name} has higher ranking")
        
        if factors.get('form_advantage'):
            if factors['form_advantage'] == 'player1':
                key_factors.append(f"{player1_name} has better recent form")
            elif factors['form_advantage'] == 'player2':
                key_factors.append(f"{player2_name} has better recent form")
        
        if surface:
            key_factors.append(f"Surface: {surface}")
        
        # Player advantages
        player_advantages = {
            player1_name: [],
            player2_name: []
        }
        
        if factors.get('ranking_advantage') == 'player1':
            player_advantages[player1_name].append("Higher ranking")
        elif factors.get('ranking_advantage') == 'player2':
            player_advantages[player2_name].append("Higher ranking")
        
        if factors.get('form_advantage') == 'player1':
            player_advantages[player1_name].append("Better recent form")
        elif factors.get('form_advantage') == 'player2':
            player_advantages[player2_name].append("Better recent form")
        
        return SetPredictionResponse(
            match_id=event_id or 0,
            predicted_winner=prediction['predicted_winner'],
            predicted_score=prediction['predicted_score'],
            confidence_level=prediction.get('confidence', 'Medium'),
            key_factors=key_factors,
            player_advantages=player_advantages
        )
        
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/surface-analysis/{player1_id}/{player2_id}/{surface}",
    response_model=SurfaceAnalysis,
    summary="Analyze players on specific surface",
    description="Compare player performance on a specific surface (hardcourt, clay, grass)."
)
async def analyze_surface_performance(
    player1_id: int = Path(..., description="First player's MatchDataProvider ID"),
    player2_id: int = Path(..., description="Second player's MatchDataProvider ID"),
    surface: str = Path(..., description="Court surface (hardcourt, clay, grass)")
) -> SurfaceAnalysis:
    """Analyze player performance on specific surface."""
    try:
        # Get statistics for both players
        current_year = datetime.now().year
        p1_stats = analysis_service.get_player_year_statistics(player1_id, current_year)
        p2_stats = analysis_service.get_player_year_statistics(player2_id, current_year)
        
        # Extract surface-specific stats
        p1_surface_stats = None
        p2_surface_stats = None
        
        surface_mapping = {
            'hardcourt': ['Hardcourt', 'Hard'],
            'clay': ['Clay', 'Red clay'],
            'grass': ['Grass']
        }
        
        surface_keywords = surface_mapping.get(surface.lower(), [surface])
        
        # Find matching surface statistics
        for stat in p1_stats.get('statistics', []):
            for keyword in surface_keywords:
                if keyword.lower() in stat.get('groundType', '').lower():
                    p1_surface_stats = stat
                    break
            if p1_surface_stats:
                break
        
        for stat in p2_stats.get('statistics', []):
            for keyword in surface_keywords:
                if keyword.lower() in stat.get('groundType', '').lower():
                    p2_surface_stats = stat
                    break
            if p2_surface_stats:
                break
        
        # Determine surface advantage
        surface_advantage = None
        if p1_surface_stats and p2_surface_stats:
            p1_win_rate = (p1_surface_stats['wins'] / p1_surface_stats['matches']) * 100
            p2_win_rate = (p2_surface_stats['wins'] / p2_surface_stats['matches']) * 100
            
            if p1_win_rate > p2_win_rate:
                surface_advantage = "player1"
            elif p2_win_rate > p1_win_rate:
                surface_advantage = "player2"
        
        return SurfaceAnalysis(
            surface=surface,
            player1_stats=p1_surface_stats,
            player2_stats=p2_surface_stats,
            surface_advantage=surface_advantage
        )
        
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/quick-analysis/{event_id}",
    response_model=Dict[str, Any],
    summary="Quick match analysis from event ID",
    description="Get quick analysis for a match using the event ID to extract player information."
)
async def quick_match_analysis(
    event_id: int = Path(..., description="MatchDataProvider event ID"),
    include_votes: bool = Query(True, description="Include community voting data")
) -> Dict[str, Any]:
    """Get quick match analysis from event ID."""
    try:
        analysis_data = {
            'event_id': event_id,
            'analysis_date': datetime.now(),
            'error': None,
            'voting_data': None,
            'recommendation': 'Unable to determine - need player IDs'
        }
        
        # Get voting data if requested
        if include_votes:
            try:
                votes = analysis_service.get_match_votes(event_id)
                analysis_data['voting_data'] = votes
                
                # Basic recommendation based on votes
                vote_data = votes.get('vote', {})
                if vote_data:
                    vote1 = vote_data.get('vote1', 0)
                    vote2 = vote_data.get('vote2', 0)
                    total_votes = vote1 + vote2
                    
                    if total_votes > 0:
                        p1_percentage = (vote1 / total_votes) * 100
                        p2_percentage = (vote2 / total_votes) * 100
                        
                        if p1_percentage > p2_percentage:
                            analysis_data['recommendation'] = f"Community favors Player 1 ({p1_percentage:.1f}% vs {p2_percentage:.1f}%)"
                        else:
                            analysis_data['recommendation'] = f"Community favors Player 2 ({p2_percentage:.1f}% vs {p1_percentage:.1f}%)"
                        
                        analysis_data['confidence'] = 'High' if abs(p1_percentage - p2_percentage) > 20 else 'Medium'
                
            except Exception as e:
                analysis_data['voting_error'] = str(e)
        
        return analysis_data
        
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/player/{player_id}/comprehensive-form",
    response_model=Dict[str, Any],
    summary="Get comprehensive form analysis with pagination",
    description="Get comprehensive singles form analysis using pagination for better coverage."
)
async def get_comprehensive_form(
    player_id: int = Path(..., description="MatchDataProvider player ID"),
    max_matches: int = Query(30, description="Maximum matches to analyze", ge=10, le=100),
    opponent_ranking: Optional[int] = Query(None, description="Opponent's ATP ranking for context"),
    include_previous_year: bool = Query(False, description="Include previous year matches")
) -> Dict[str, Any]:
    """Get comprehensive form analysis with extensive match coverage."""
    try:
        if include_previous_year:
            # Use year-based comprehensive analysis
            comprehensive_form = analysis_service.get_recent_comprehensive_form(
                player_id, 
                current_year=True,
                previous_year=True,
                max_matches_per_year=max_matches // 2
            )
            
            if comprehensive_form.get('matches_data'):
                # Run enhanced analysis on the comprehensive data
                form_analysis = analysis_service.analyze_recent_form(
                    player_id, 
                    min(len(comprehensive_form['matches_data']), max_matches),
                    opponent_ranking
                )
                
                # Combine the results
                form_analysis['comprehensive_info'] = {
                    'years_covered': comprehensive_form['years_covered'],
                    'total_available': comprehensive_form['total_available'],
                    'pages_fetched': comprehensive_form['pages_fetched']
                }
                
                return form_analysis
            else:
                return comprehensive_form
        else:
            # Standard comprehensive analysis (current year only)
            return analysis_service.analyze_recent_form(player_id, max_matches, opponent_ranking)
            
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/player/{player_id}/singles-matches",
    response_model=Dict[str, Any], 
    summary="Get comprehensive singles matches with pagination",
    description="Get singles matches with pagination support for extensive analysis."
)
async def get_player_singles_comprehensive(
    player_id: int = Path(..., description="MatchDataProvider player ID"),
    max_matches: int = Query(30, description="Maximum matches to retrieve", ge=10, le=100),
    max_pages: int = Query(3, description="Maximum pages to fetch", ge=1, le=10)
) -> Dict[str, Any]:
    """Get comprehensive singles matches data with pagination."""
    try:
        singles_data = analysis_service.get_comprehensive_singles_matches(
            player_id, max_matches=max_matches, max_pages=max_pages
        )
        return singles_data
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@match_analysis_router.get(
    "/batch-analysis",
    response_model=Dict[str, Any],
    summary="Analyze multiple players at once",
    description="Get analysis for multiple players in a single request."
)
async def batch_player_analysis(
    player_ids: str = Query(..., description="Comma-separated list of player IDs"),
    include_form: bool = Query(True, description="Include recent form analysis"),
    include_rankings: bool = Query(True, description="Include ranking information")
) -> Dict[str, Any]:
    """Analyze multiple players in batch."""
    try:
        # Parse player IDs
        ids = [int(pid.strip()) for pid in player_ids.split(',')]
        
        if len(ids) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 players allowed per batch")
        
        batch_results = {
            'analyzed_players': len(ids),
            'analysis_date': datetime.now(),
            'players': {}
        }
        
        for player_id in ids:
            player_data = {'id': player_id}
            
            try:
                # Get basic details
                details = analysis_service.get_player_details(player_id)
                player_data['name'] = details.get('team', {}).get('name', f'Player {player_id}')
                player_data['country'] = details.get('team', {}).get('country', {}).get('name', 'Unknown')
                
                # Get rankings if requested
                if include_rankings:
                    rankings = analysis_service.get_player_rankings(player_id)
                    player_data['rankings'] = rankings
                
                # Get form analysis if requested
                if include_form:
                    form = analysis_service.analyze_recent_form(player_id, 5)
                    player_data['recent_form'] = form
                
                player_data['status'] = 'success'
                
            except Exception as e:
                player_data['status'] = 'error'
                player_data['error'] = str(e)
            
            batch_results['players'][str(player_id)] = player_data
        
        return batch_results
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid player IDs format")
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
