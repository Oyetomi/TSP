#!/usr/bin/env python3
"""
Simple script to dump UTR API responses using curl_cffi
"""

import json
from curl_cffi import requests

def dump_utr_api():
    """Dump the actual UTR API responses"""
    
    # Men's UTR rankings
    print("🔄 Fetching Men's UTR rankings...")
    url_men = 'https://www.matchdata-api.example.com/api/v1/rankings/type/34'
    headers_men = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'baggage': 'sentry-environment=production,sentry-release=MNFQzn9e7qD7gxk2_7lio,sentry-public_key=d693747a6bb242d9bb9cf7069fb57988,sentry-trace_id=f9d453f2549d86f124db2b13b6c3d38d',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.matchdata-api.example.com/tennis/rankings/utr-men',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'sentry-trace': 'f9d453f2549d86f124db2b13b6c3d38d-bf001fe4f3975dad',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'x-requested-with': '50734b'
    }
    
    try:
        response = requests.get(
            url_men,
            headers=headers_men,
            cookies={'perf_dv6Tr4n': '1'},
            impersonate="chrome120",
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            
            # Save full response
            with open('men_utr_full.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            # Print structure info
            print(f"📊 Response keys: {list(data.keys())}")
            
            if 'rankings' in data:
                rankings = data['rankings']
                print(f"📊 Number of rankings: {len(rankings)}")
                
                if rankings:
                    print(f"📄 First entry structure:")
                    print(json.dumps(rankings[0], indent=2))
                    
                    print(f"\n📄 Sample entries (first 3):")
                    for i, entry in enumerate(rankings[:3]):
                        print(f"Entry {i+1}: {json.dumps(entry, indent=2)}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error fetching men's UTR: {e}")
    
    print("\n" + "="*50)
    
    # Women's UTR rankings
    print("🔄 Fetching Women's UTR rankings...")
    url_women = 'https://www.matchdata-api.example.com/api/v1/rankings/type/35'
    headers_women = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'baggage': 'sentry-environment=production,sentry-release=MNFQzn9e7qD7gxk2_7lio,sentry-public_key=d693747a6bb242d9bb9cf7069fb57988,sentry-trace_id=40f91cdee92ef0e009b988ad2b983b96',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.matchdata-api.example.com/tennis/rankings/utr-women',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'sentry-trace': '40f91cdee92ef0e009b988ad2b983b96-9e1c1add92bd83cf',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'x-requested-with': 'fa07e5'
    }
    
    try:
        response = requests.get(
            url_women,
            headers=headers_women,
            cookies={'perf_dv6Tr4n': '1'},
            impersonate="chrome120",
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            
            # Save full response
            with open('women_utr_full.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            # Print structure info
            print(f"📊 Response keys: {list(data.keys())}")
            
            if 'rankings' in data:
                rankings = data['rankings']
                print(f"📊 Number of rankings: {len(rankings)}")
                
                if rankings:
                    print(f"📄 First entry structure:")
                    print(json.dumps(rankings[0], indent=2))
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error fetching women's UTR: {e}")

if __name__ == "__main__":
    dump_utr_api()
