#!/usr/bin/env python3
"""
Update Tennis Abstract Elo data from live website
Fetches latest ATP and WTA Elo ratings and exports to CSV
"""

import logging
from tennis_abstract_integration import TennisAbstractScraper
import pandas as pd
from datetime import datetime

def update_elo_data():
    """Fetch latest Elo data from Tennis Abstract and update CSV"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("🎾 UPDATING TENNIS ABSTRACT ELO DATA")
    print("=" * 80)
    print()
    
    # Initialize scraper
    scraper = TennisAbstractScraper(rate_limit_seconds=2)
    
    # Fetch ATP data
    print("📊 Fetching ATP Elo rankings from Tennis Abstract...")
    atp_players = scraper.fetch_atp_elo_rankings(force_refresh=True)
    
    if not atp_players:
        logger.error("❌ Failed to fetch ATP data")
        return False
    
    print(f"✅ Fetched {len(atp_players)} ATP players")
    print()
    
    # Fetch WTA data
    print("📊 Fetching WTA Elo rankings from Tennis Abstract...")
    wta_players = scraper.fetch_wta_elo_rankings(force_refresh=True)
    
    if not wta_players:
        logger.error("❌ Failed to fetch WTA data")
        print("   Proceeding with ATP data only...")
        all_players = atp_players
    else:
        print(f"✅ Fetched {len(wta_players)} WTA players")
        print()
        all_players = atp_players + wta_players
    
    # Convert to DataFrame
    df = pd.DataFrame(all_players)
    
    # Export to CSV
    output_file = 'tennis_abstract_elo.csv'
    df.to_csv(output_file, index=False)
    
    print("=" * 80)
    print("✅ ELO DATA UPDATE COMPLETE")
    print("=" * 80)
    print(f"📄 File: {output_file}")
    print(f"📊 Total Players: {len(all_players)}")
    print(f"   - ATP: {len(atp_players)}")
    print(f"   - WTA: {len(wta_players) if wta_players else 0}")
    print(f"🕒 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Show top 10 ATP players
    print("🏆 TOP 10 ATP PLAYERS (by Elo):")
    print("-" * 80)
    for i, player in enumerate(atp_players[:10], 1):
        print(f"   {i:2d}. {player['name']:25s} | Elo: {player['elo_rating']:.1f} | ATP: #{player.get('atp_rank', 'N/A')}")
    print()
    
    # Show top 10 WTA players if available
    if wta_players:
        print("🏆 TOP 10 WTA PLAYERS (by Elo):")
        print("-" * 80)
        for i, player in enumerate(wta_players[:10], 1):
            print(f"   {i:2d}. {player['name']:25s} | Elo: {player['elo_rating']:.1f} | WTA: #{player.get('wta_rank', 'N/A')}")
        print()
    
    print("✅ CSV updated successfully!")
    print("💡 TIP: System will automatically use this fresh data for predictions")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        success = update_elo_data()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Update cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

