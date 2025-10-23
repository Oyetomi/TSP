"""
Tennis API router for fetching and analyzing tennis match data.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from ..models.tennis_models import TennisEventResponse, TennisEvent
from ..services.match_data_service import MatchDataProviderService, MatchDataProviderServiceError


# Response models
class MatchSummary(BaseModel):
    """Summary information about a tennis match."""
    id: int
    home_player: str
    away_player: str
    tournament: str
    status: str
    start_time: datetime
    ground_type: str


class TournamentSummary(BaseModel):
    """Summary of tournaments on a given date."""
    date: date
    total_events: int
    tournament_levels: Dict[str, int]
    surface_distribution: Dict[str, int]
    categories: Dict[str, int]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str


# Initialize router
tennis_router = APIRouter(prefix="/tennis", tags=["tennis"])

# Initialize service
match_data_service = MatchDataProviderService()


@tennis_router.get(
    "/events/{event_date}",
    response_model=TennisEventResponse,
    summary="Get tennis events for a specific date",
    description="Fetch all scheduled tennis events from MatchDataProvider for the given date."
)
async def get_tennis_events(
    event_date: date = Path(
        ...,
        description="Date to fetch events for (YYYY-MM-DD format)",
        example="2025-08-20"
    )
) -> TennisEventResponse:
    """Get all tennis events for a specific date."""
    try:
        events = await match_data_service.get_scheduled_events_async(event_date)
        return events
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@tennis_router.get(
    "/events/{event_date}/summary",
    response_model=List[MatchSummary],
    summary="Get match summaries for a date",
    description="Get simplified match information for easier consumption."
)
async def get_match_summaries(
    event_date: date = Path(..., description="Date to fetch events for"),
    category: Optional[str] = Query(None, description="Filter by category (atp, wta, etc.)"),
    tournament: Optional[str] = Query(None, description="Filter by tournament slug"),
    status: Optional[str] = Query(None, description="Filter by match status (inprogress, notstarted, finished)")
) -> List[MatchSummary]:
    """Get simplified match summaries with optional filtering."""
    try:
        events = await match_data_service.get_scheduled_events_async(event_date)
        matches = events.events
        
        # Apply filters
        if category:
            matches = [m for m in matches if m.tournament.category.slug.lower() == category.lower()]
        
        if tournament:
            matches = [m for m in matches if m.tournament.slug == tournament]
        
        if status:
            matches = [m for m in matches if m.status.type == status]
        
        # Convert to summary format
        summaries = [
            MatchSummary(
                id=match.id,
                home_player=match.home_team.name,
                away_player=match.away_team.name,
                tournament=match.tournament.name,
                status=match.status.description,
                start_time=match.start_time,
                ground_type=match.ground_type
            )
            for match in matches
        ]
        
        return summaries
        
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@tennis_router.get(
    "/events/{event_date}/ongoing",
    response_model=List[TennisEvent],
    summary="Get ongoing matches",
    description="Get all matches that are currently in progress."
)
async def get_ongoing_matches(
    event_date: date = Path(..., description="Date to check for ongoing matches")
) -> List[TennisEvent]:
    """Get all currently ongoing matches."""
    try:
        matches = match_data_service.get_ongoing_matches(event_date)
        return matches
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@tennis_router.get(
    "/events/{event_date}/upcoming", 
    response_model=List[TennisEvent],
    summary="Get upcoming matches",
    description="Get all matches that haven't started yet."
)
async def get_upcoming_matches(
    event_date: date = Path(..., description="Date to check for upcoming matches")
) -> List[TennisEvent]:
    """Get all upcoming matches."""
    try:
        matches = match_data_service.get_upcoming_matches(event_date)
        return matches
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@tennis_router.get(
    "/events/{event_date}/tournament/{tournament_slug}",
    response_model=List[TennisEvent],
    summary="Get events for a specific tournament",
    description="Get all events for a specific tournament on the given date."
)
async def get_tournament_events(
    event_date: date = Path(..., description="Date to fetch events for"),
    tournament_slug: str = Path(..., description="Tournament slug (e.g., 'winston-salem-usa')")
) -> List[TennisEvent]:
    """Get events for a specific tournament."""
    try:
        events = match_data_service.get_events_by_tournament(event_date, tournament_slug)
        if not events:
            raise HTTPException(
                status_code=404, 
                detail=f"No events found for tournament '{tournament_slug}' on {event_date}"
            )
        return events
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@tennis_router.get(
    "/events/{event_date}/category/{category}",
    response_model=List[TennisEvent], 
    summary="Get events by category",
    description="Get all events for a specific category (ATP, WTA, etc.)."
)
async def get_category_events(
    event_date: date = Path(..., description="Date to fetch events for"),
    category: str = Path(..., description="Category slug (e.g., 'atp', 'wta')")
) -> List[TennisEvent]:
    """Get events for a specific category."""
    try:
        events = match_data_service.get_events_by_category(event_date, category)
        if not events:
            raise HTTPException(
                status_code=404,
                detail=f"No events found for category '{category}' on {event_date}"
            )
        return events
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@tennis_router.get(
    "/match/{event_date}/{event_id}",
    response_model=TennisEvent,
    summary="Get specific match details",
    description="Get detailed information for a specific match by its ID."
)
async def get_match_details(
    event_date: date = Path(..., description="Date the event is scheduled for"),
    event_id: int = Path(..., description="MatchDataProvider event ID")
) -> TennisEvent:
    """Get details for a specific match."""
    try:
        match = match_data_service.get_match_by_id(event_date, event_id)
        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"Match with ID {event_id} not found on {event_date}"
            )
        return match
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@tennis_router.get(
    "/analytics/{event_date}",
    response_model=TournamentSummary,
    summary="Get analytics for a date",
    description="Get analytical summary of all tennis events for a given date."
)
async def get_date_analytics(
    event_date: date = Path(..., description="Date to analyze")
) -> TournamentSummary:
    """Get analytical summary for a specific date."""
    try:
        events = await match_data_service.get_scheduled_events_async(event_date)
        tournament_levels = match_data_service.get_tournament_levels(event_date)
        surface_distribution = match_data_service.get_surface_distribution(event_date)
        
        # Count categories
        categories = {}
        for event in events.events:
            category = event.tournament.category.name
            categories[category] = categories.get(category, 0) + 1
        
        return TournamentSummary(
            date=event_date,
            total_events=events.total_events,
            tournament_levels=tournament_levels,
            surface_distribution=surface_distribution,
            categories=categories
        )
        
    except MatchDataProviderServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
