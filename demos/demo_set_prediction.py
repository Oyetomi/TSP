"""
Demo script showcasing the complete tennis set prediction workflow.

This demonstrates how to analyze a match between two players and predict
who will win the most sets, with detailed reasoning.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def demo_complete_set_prediction():
    """Complete demonstration of set prediction workflow."""
    
    print("🎾 TENNIS SET PREDICTION SYSTEM DEMO")
    print("=" * 60)
    print("📊 Analyzing: Stefanos Tsitsipas vs Yunchaokete Bu")
    print("🎯 Goal: Predict who wins the most sets\n")
    
    # Player IDs
    tsitsipas_id = 122366
    yunchaokete_id = 254227
    event_id = 14428710
    
    print("STEP 1: Gathering Player Intelligence...")
    print("-" * 40)
    
    # Get player details
    print("🔍 Fetching player information...")
    try:
        p1_response = requests.get(f"{BASE_URL}/match-analysis/player/{tsitsipas_id}/details")
        p2_response = requests.get(f"{BASE_URL}/match-analysis/player/{yunchaokete_id}/details")
        
        p1_details = p1_response.json()['team']
        p2_details = p2_response.json()['team']
        
        print(f"   Player 1: {p1_details['name']} ({p1_details['country']['name']})")
        print(f"   Player 2: {p2_details['name']} ({p2_details['country']['name']})")
        
    except Exception as e:
        print(f"   ❌ Error getting player details: {e}")
        return
    
    # Get rankings
    print("\n🏆 Analyzing rankings...")
    try:
        p1_rankings = requests.get(f"{BASE_URL}/match-analysis/player/{tsitsipas_id}/rankings").json()
        p2_rankings = requests.get(f"{BASE_URL}/match-analysis/player/{yunchaokete_id}/rankings").json()
        
        p1_atp = p1_rankings['rankings'][0]['ranking']
        p1_points = p1_rankings['rankings'][0]['points']
        
        # Yunchaokete might not have ATP ranking
        p2_ranking = "Unranked"
        p2_points = 0
        for ranking in p2_rankings.get('rankings', []):
            if ranking.get('type') == 5:  # ATP ranking
                p2_ranking = f"#{ranking['ranking']}"
                p2_points = ranking['points']
                break
        
        print(f"   {p1_details['name']}: ATP #{p1_atp} ({p1_points} points)")
        print(f"   {p2_details['name']}: {p2_ranking} ({p2_points} points)")
        
        ranking_advantage = "Tsitsipas" if p1_points > p2_points else "Yunchaokete" if p2_points > p1_points else "Equal"
        print(f"   🎯 Ranking Advantage: {ranking_advantage}")
        
    except Exception as e:
        print(f"   ❌ Error getting rankings: {e}")
    
    # Get recent form
    print("\n📈 Recent form analysis...")
    try:
        p1_form = requests.get(f"{BASE_URL}/match-analysis/player/{tsitsipas_id}/recent-form?num_matches=5").json()
        p2_form = requests.get(f"{BASE_URL}/match-analysis/player/{yunchaokete_id}/recent-form?num_matches=5").json()
        
        p1_win_rate = p1_form['form_data']['win_rate']
        p1_set_rate = p1_form['form_data']['set_win_rate']
        
        p2_win_rate = p2_form['form_data']['win_rate'] 
        p2_set_rate = p2_form['form_data']['set_win_rate']
        
        print(f"   {p1_details['name']}: {p1_win_rate:.0%} match wins, {p1_set_rate:.0%} set wins")
        print(f"   {p2_details['name']}: {p2_win_rate:.0%} match wins, {p2_set_rate:.0%} set wins")
        
        form_advantage = "Tsitsipas" if p1_win_rate > p2_win_rate else "Yunchaokete" if p2_win_rate > p1_win_rate else "Equal"
        print(f"   🎯 Form Advantage: {form_advantage}")
        
    except Exception as e:
        print(f"   ❌ Error getting form: {e}")
    
    # Get community sentiment
    print("\n👥 Community sentiment...")
    try:
        votes = requests.get(f"{BASE_URL}/match-analysis/match/{event_id}/votes").json()
        vote_data = votes['vote']
        
        total_votes = vote_data['vote1'] + vote_data['vote2'] 
        p1_percentage = (vote_data['vote1'] / total_votes) * 100
        p2_percentage = (vote_data['vote2'] / total_votes) * 100
        
        print(f"   Total votes: {total_votes:,}")
        print(f"   Player 1: {vote_data['vote1']:,} votes ({p1_percentage:.1f}%)")
        print(f"   Player 2: {vote_data['vote2']:,} votes ({p2_percentage:.1f}%)")
        
        crowd_favorite = "Player 1" if p1_percentage > p2_percentage else "Player 2"
        print(f"   🎯 Crowd Favorite: {crowd_favorite}")
        
    except Exception as e:
        print(f"   ❌ Error getting votes: {e}")
    
    # Surface analysis
    print("\n🏟️  Surface analysis (Hardcourt)...")
    try:
        surface = requests.get(f"{BASE_URL}/match-analysis/surface-analysis/{tsitsipas_id}/{yunchaokete_id}/hardcourt").json()
        
        p1_surface = surface.get('player1_stats')
        p2_surface = surface.get('player2_stats')
        
        if p1_surface:
            p1_surface_rate = (p1_surface['wins'] / p1_surface['matches']) * 100
            print(f"   {p1_details['name']}: {p1_surface['wins']}/{p1_surface['matches']} ({p1_surface_rate:.1f}%)")
        
        if p2_surface:
            p2_surface_rate = (p2_surface['wins'] / p2_surface['matches']) * 100  
            print(f"   {p2_details['name']}: {p2_surface['wins']}/{p2_surface['matches']} ({p2_surface_rate:.1f}%)")
        
        surface_adv = surface.get('surface_advantage', 'Unknown')
        advantage_name = "Tsitsipas" if surface_adv == "player1" else "Yunchaokete" if surface_adv == "player2" else "Equal"
        print(f"   🎯 Surface Advantage: {advantage_name}")
        
    except Exception as e:
        print(f"   ❌ Error getting surface data: {e}")
    
    print("\n" + "=" * 60)
    print("STEP 2: SET PREDICTION ANALYSIS")
    print("=" * 60)
    
    # Get final prediction
    try:
        prediction = requests.get(f"{BASE_URL}/match-analysis/predict-set/{tsitsipas_id}/{yunchaokete_id}?event_id={event_id}").json()
        
        print("🎯 FINAL SET PREDICTION:")
        print(f"   Winner: {prediction['predicted_winner']}")
        print(f"   Score: {prediction['predicted_score']}")  
        print(f"   Confidence: {prediction['confidence_level']}")
        print(f"\n📊 Key Factors:")
        for factor in prediction['key_factors']:
            print(f"   • {factor}")
        
        print(f"\n⚖️  Player Advantages:")
        for player, advantages in prediction['player_advantages'].items():
            if advantages:
                print(f"   {player}:")
                for advantage in advantages:
                    print(f"     • {advantage}")
        
        # Detailed comparison
        comparison = requests.get(f"{BASE_URL}/match-analysis/compare/{tsitsipas_id}/{yunchaokete_id}").json()
        factors = comparison['prediction_factors']
        
        print(f"\n🧮 Prediction Algorithm:")
        score_p1 = 0
        score_p2 = 0
        
        if factors.get('ranking_advantage') == 'player1':
            score_p1 += 2
            print("   • Ranking advantage (Player 1): +2 points")
        elif factors.get('ranking_advantage') == 'player2':
            score_p2 += 2  
            print("   • Ranking advantage (Player 2): +2 points")
        
        if factors.get('form_advantage') == 'player1':
            score_p1 += 1
            print("   • Form advantage (Player 1): +1 point")
        elif factors.get('form_advantage') == 'player2':
            score_p2 += 1
            print("   • Form advantage (Player 2): +1 point")
        
        print(f"\n📈 Final Scores:")
        print(f"   {p1_details['name']}: {score_p1} points")
        print(f"   {p2_details['name']}: {score_p2} points")
        
        # Win probability estimate
        total_score = score_p1 + score_p2
        if total_score > 0:
            p1_prob = (score_p1 / total_score) * 100
            p2_prob = (score_p2 / total_score) * 100
            print(f"\n🎲 Estimated Probabilities:")
            print(f"   {p1_details['name']}: {p1_prob:.0f}%") 
            print(f"   {p2_details['name']}: {p2_prob:.0f}%")
        
    except Exception as e:
        print(f"❌ Error getting prediction: {e}")
    
    print("\n" + "=" * 60)
    print("✅ SET PREDICTION COMPLETE!")
    print("=" * 60)
    print("🎾 RECOMMENDATION: Based on analysis of rankings, recent form,")
    print("   surface performance, and community sentiment, the system")
    print("   predicts the higher-ranked player with better recent form")
    print("   will win the majority of sets.")
    print(f"\n📚 Full API Documentation: {BASE_URL}/docs")
    print("🔄 This analysis updates in real-time with fresh match data!")

if __name__ == "__main__":
    try:
        demo_complete_set_prediction()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Ensure FastAPI server is running: python run_server.py")
