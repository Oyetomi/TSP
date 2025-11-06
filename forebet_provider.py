#!/usr/bin/env python3
"""
Forebet Provider - Integration Module

Scrapes Forebet predictions and matches them with our system's predictions
for enhanced confidence scoring.
"""

from curl_cffi import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class ForebetProvider:
    """
    Provider for Forebet tennis predictions
    
    Scrapes Forebet's date-specific prediction pages (/predictions/YYYY-MM-DD)
    for multiple days and matches predictions with our system for confidence boosting.
    
    Now supports fetching 3+ days of predictions to match our system's date range!
    Uses the URL format: https://m.forebet.com/en/tennis/predictions/YYYY-MM-DD
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Forebet provider
        
        Args:
            logger: Optional logger instance (will create if not provided)
        """
        self.base_url = "https://m.forebet.com/en/tennis/predictions"
        self.session = requests.Session()
        self.predictions_cache = None
        self.cache_timestamp = None
        self.logger = logger or self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup default logger if none provided"""
        logger = logging.getLogger('ForebetProvider')
        logger.setLevel(logging.INFO)
        return logger
    
    def fetch_predictions(self, force_refresh: bool = False, days: int = 3) -> List[Dict]:
        """
        Fetch predictions from Forebet for the next N days
        
        Args:
            force_refresh: Force refresh even if cached
            days: Number of days to fetch (default: 3 to match our system)
            
        Returns:
            List of prediction dictionaries
        """
        # Use cache if available (within same run)
        if not force_refresh and self.predictions_cache is not None:
            self.logger.info(f"📦 Using cached Forebet predictions ({len(self.predictions_cache)} matches)")
            return self.predictions_cache
        
        self.logger.info(f"🌐 Fetching Forebet predictions for next {days} days...")
        
        all_predictions = []
        finished_count = 0
        unfinished_count = 0
        
        # Generate URLs for the next N days
        today = datetime.now()
        
        for day_offset in range(days):
            target_date = today + timedelta(days=day_offset)
            date_str = target_date.strftime('%Y-%m-%d')
            url = f"{self.base_url}/{date_str}"
            
            day_label = "TODAY" if day_offset == 0 else f"DAY+{day_offset} ({date_str})"
            
            try:
                self.logger.info(f"   📥 Fetching {day_label}...")
                
                response = self.session.get(
                    url,
                    impersonate="chrome110",
                    timeout=30
                )
                
                if response.status_code != 200:
                    self.logger.warning(f"⚠️ Forebet {day_label} fetch failed: Status {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                match_rows = soup.find_all('div', class_='rcnt')
                
                day_predictions = []
                
                for row in match_rows:
                    try:
                        prediction = self._parse_match_row(row)
                        if prediction:
                            prediction['day'] = day_label  # Tag with day for debugging
                            prediction['fetch_date'] = date_str  # Store the date
                            day_predictions.append(prediction)
                            if prediction['is_finished']:
                                finished_count += 1
                            else:
                                unfinished_count += 1
                    except Exception as e:
                        self.logger.debug(f"⚠️ Failed to parse row: {e}")
                        continue
                
                all_predictions.extend(day_predictions)
                self.logger.info(f"   ✅ {day_label}: {len(day_predictions)} matches")
                
            except Exception as e:
                self.logger.error(f"❌ Error fetching Forebet {day_label}: {e}")
                continue
        
        self.predictions_cache = all_predictions
        self.cache_timestamp = datetime.now()
        
        self.logger.info(f"✅ Fetched {len(all_predictions)} total Forebet predictions")
        self.logger.info(f"   📊 Finished: {finished_count} | Unfinished: {unfinished_count}")
        
        return all_predictions
    
    def _parse_match_row(self, row) -> Optional[Dict]:
        """
        Parse a single match row from Forebet
        
        Args:
            row: BeautifulSoup row element
            
        Returns:
            Dict with match prediction data or None
        """
        # Get player names
        tnms = row.find('div', class_='tnms')
        if not tnms:
            return None
            
        home_team = tnms.find('span', class_='homeTeam')
        away_team = tnms.find('span', class_='awayTeam')
        
        if not home_team or not away_team:
            return None
        
        player1 = home_team.get_text(strip=True)
        player2 = away_team.get_text(strip=True)
        
        # Get tournament
        tournament_link = tnms.find('a', class_='tnmscn')
        if tournament_link and 'href' in tournament_link.attrs:
            tournament = tournament_link['href'].split('/')[-2] if '/' in tournament_link['href'] else "Unknown"
        else:
            tournament = "Unknown"
        
        # Get Forebet's prediction and probabilities
        fprc = row.find('div', class_='fprc')
        if not fprc:
            return None
            
        probs = fprc.find_all('span')
        if len(probs) < 2:
            return None
        
        if 'fpr' in probs[0].get('class', []):
            predicted_player = player1
            predicted_probability = probs[0].get_text(strip=True)
            other_probability = probs[1].get_text(strip=True)
        else:
            predicted_player = player2
            predicted_probability = probs[1].get_text(strip=True)
            other_probability = probs[0].get_text(strip=True)
        
        # Check if match is finished (for validation/debugging)
        predict_div = row.find('div', class_=['predict_y', 'predict_no', 'predict'])
        is_finished = False
        
        if predict_div:
            if 'predict_y' in predict_div.get('class', []):
                is_finished = True
            elif 'predict_no' in predict_div.get('class', []):
                is_finished = True
        
        return {
            'player1': player1,
            'player2': player2,
            'tournament': tournament,
            'predicted_player': predicted_player,
            'predicted_probability': predicted_probability,
            'other_probability': other_probability,
            'is_finished': is_finished
        }
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize player name to "LastName FirstInitial" format
        
        Examples:
            "Ugo Blanchet" -> "blanchet u"
            "U.Blanchet" -> "blanchet u"
            "U. Blanchet" -> "blanchet u"
            "John Smith Jr" -> "smith jr j"
        
        Args:
            name: Player name in any format
            
        Returns:
            Normalized name as "lastname firstinitial" (lowercase)
        """
        name = name.strip().lower()
        
        # Remove dots and extra spaces
        name = name.replace('.', ' ').replace('  ', ' ')
        
        parts = name.split()
        if len(parts) < 2:
            # Single name, just return it
            return name
        
        # Last part is last name, first part is first name
        last_name = parts[-1]
        first_name = parts[0]
        first_initial = first_name[0] if first_name else ''
        
        # Format: "lastname firstinitial"
        return f"{last_name} {first_initial}"
    
    def find_match(self, our_player1: str, our_player2: str) -> Optional[Dict]:
        """
        Find a match in Forebet predictions using normalized name matching
        
        Handles abbreviated names from Forebet (e.g., "U.Blanchet" vs "Ugo Blanchet")
        by matching on "LastName FirstInitial" format to avoid false matches
        with players who have the same last name.
        
        Args:
            our_player1: First player name from our system
            our_player2: Second player name from our system
            
        Returns:
            Forebet prediction dict if found, None otherwise
        """
        if self.predictions_cache is None:
            self.fetch_predictions()
        
        if not self.predictions_cache:
            return None
        
        # Normalize our player names
        our_p1_norm = self._normalize_name(our_player1)
        our_p2_norm = self._normalize_name(our_player2)
        
        best_match = None
        best_score = 0
        
        for fb_pred in self.predictions_cache:
            # Normalize Forebet names
            fb_p1_norm = self._normalize_name(fb_pred['player1'])
            fb_p2_norm = self._normalize_name(fb_pred['player2'])
            
            # Try direct match (our_p1 vs fb_p1, our_p2 vs fb_p2)
            score1 = fuzz.ratio(our_p1_norm, fb_p1_norm)
            score2 = fuzz.ratio(our_p2_norm, fb_p2_norm)
            direct_score = min(score1, score2)  # Take minimum to ensure both match
            
            # Try reversed match (our_p1 vs fb_p2, our_p2 vs fb_p1)
            score1_rev = fuzz.ratio(our_p1_norm, fb_p2_norm)
            score2_rev = fuzz.ratio(our_p2_norm, fb_p1_norm)
            reversed_score = min(score1_rev, score2_rev)
            
            # Take best of both attempts
            match_score = max(direct_score, reversed_score)
            
            if match_score > best_score and match_score >= 75:  # Balanced threshold for normalized format
                best_score = match_score
                best_match = fb_pred
        
        if best_match:
            self.logger.debug(f"✅ Forebet match found: {our_player1} vs {our_player2}")
            self.logger.debug(f"   → {best_match['player1']} vs {best_match['player2']} (score: {best_score})")
            self.logger.debug(f"   Normalized: {our_p1_norm} vs {our_p2_norm}")
        else:
            # Show best attempt even if it failed
            if best_score > 0:
                # Find the prediction that had the best score
                best_attempt = None
                for fb_pred in self.predictions_cache:
                    fb_p1_norm = self._normalize_name(fb_pred['player1'])
                    fb_p2_norm = self._normalize_name(fb_pred['player2'])
                    
                    score1 = fuzz.ratio(our_p1_norm, fb_p1_norm)
                    score2 = fuzz.ratio(our_p2_norm, fb_p2_norm)
                    direct_score = min(score1, score2)
                    
                    score1_rev = fuzz.ratio(our_p1_norm, fb_p2_norm)
                    score2_rev = fuzz.ratio(our_p2_norm, fb_p1_norm)
                    reversed_score = min(score1_rev, score2_rev)
                    
                    match_score = max(direct_score, reversed_score)
                    if match_score == best_score:
                        best_attempt = fb_pred
                        break
                
                if best_attempt:
                    self.logger.debug(f"❌ No Forebet match: {our_player1} vs {our_player2}")
                    self.logger.debug(f"   Best attempt: {best_attempt['player1']} vs {best_attempt['player2']} (score: {best_score} < 75 threshold)")
                    self.logger.debug(f"   Our normalized: {our_p1_norm} vs {our_p2_norm}")
            else:
                self.logger.debug(f"❌ No Forebet match: {our_player1} vs {our_player2} (no similar matches found)")
        
        return best_match
    
    def check_agreement(self, our_predicted_winner: str, forebet_match: Dict) -> bool:
        """
        Check if our prediction agrees with Forebet's prediction
        
        Uses normalized name matching (LastName FirstInitial) to handle
        abbreviated names consistently with match finding logic.
        
        Args:
            our_predicted_winner: Winner predicted by our system
            forebet_match: Forebet prediction dict
            
        Returns:
            True if predictions agree, False otherwise
        """
        if not forebet_match:
            return False
        
        fb_predicted = forebet_match['predicted_player']
        
        # Normalize both names to handle abbreviations (e.g., "S. Korda" vs "Sebastian Korda")
        our_norm = self._normalize_name(our_predicted_winner)
        fb_norm = self._normalize_name(fb_predicted)
        
        # Use exact ratio on normalized names (higher confidence)
        agreement_score = fuzz.ratio(our_norm, fb_norm)
        
        # High threshold since names are normalized
        agrees = agreement_score >= 85
        
        if agrees:
            self.logger.debug(f"✅ Agreement: Both predict {our_predicted_winner}")
            self.logger.debug(f"   Normalized: {our_norm} ≈ {fb_norm} (score: {agreement_score})")
        else:
            self.logger.debug(f"❌ Disagreement: We={our_predicted_winner}, Forebet={fb_predicted}")
            self.logger.debug(f"   Normalized: {our_norm} vs {fb_norm} (score: {agreement_score})")
        
        return agrees
    
    def get_match_info(self, player1: str, player2: str, our_predicted_winner: str) -> Dict:
        """
        Get comprehensive Forebet info for a match
        
        Args:
            player1: First player name
            player2: Second player name
            our_predicted_winner: Our system's prediction
            
        Returns:
            Dict with Forebet data:
                - forebet_available: bool
                - forebet_predicted_winner: str or None
                - forebet_probability: str or None
                - forebet_agrees: bool
        """
        forebet_match = self.find_match(player1, player2)
        
        if not forebet_match:
            return {
                'forebet_available': False,
                'forebet_predicted_winner': None,
                'forebet_probability': None,
                'forebet_agrees': False
            }
        
        agrees = self.check_agreement(our_predicted_winner, forebet_match)
        
        return {
            'forebet_available': True,
            'forebet_predicted_winner': forebet_match['predicted_player'],
            'forebet_probability': forebet_match['predicted_probability'],
            'forebet_agrees': agrees
        }

