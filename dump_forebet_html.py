#!/usr/bin/env python3
"""
Dump Forebet HTML to file for analysis
"""

from curl_cffi import requests

def dump_forebet_html():
    """Fetch and save Forebet predictions HTML"""
    
    url = "https://www.forebet.com/en/tennis/predictions-today"
    
    print(f"🌐 Fetching: {url}")
    
    try:
        response = requests.get(
            url,
            impersonate="chrome110",
            timeout=30
        )
        
        if response.status_code == 200:
            output_file = "forebet_predictions_today.html"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"✅ HTML saved to: {output_file}")
            print(f"📊 Size: {len(response.text):,} characters")
            
            # Quick preview
            lines = response.text.split('\n')
            print(f"📄 Lines: {len(lines):,}")
            
            # Look for prediction divs
            predict_y_count = response.text.count('predict_y')
            predict_no_count = response.text.count('predict_no')
            predict_plain_count = response.text.count('class="predict"') - predict_y_count - predict_no_count
            
            print(f"\n🎯 PREDICTION DIVS FOUND:")
            print(f"   ✅ predict_y (correct): {predict_y_count}")
            print(f"   ❌ predict_no (wrong): {predict_no_count}")
            print(f"   ⏳ predict (unfinished): {predict_plain_count}")
            
            if predict_y_count + predict_no_count > 0:
                accuracy = (predict_y_count / (predict_y_count + predict_no_count)) * 100
                print(f"\n📈 FOREBET ACCURACY: {accuracy:.1f}% ({predict_y_count}/{predict_y_count + predict_no_count})")
            
        else:
            print(f"❌ Failed: Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    dump_forebet_html()

