import requests
from rapidfuzz import process, fuzz

class TickerMapper:
    def __init__(self):
        self.mapping = {}
        self.names_list = []
        self._load_sec_data()

    def _load_sec_data(self):
        """
        Downloads the official list of all US Public Companies from the SEC.
        Source: https://www.sec.gov/files/company_tickers.json
        """
        print("📥 Loading SEC Ticker Master List...")
        
        # 🛡️ FIX: SEC requires 'AppName <Email>' format
        headers = {
            'User-Agent': 'CongressTradingBot contact@example.com',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            resp = requests.get(url, headers=headers)
            
            # Check for 403 Forbidden explicitly
            if resp.status_code != 200:
                print(f"❌ SEC blocked request. Status Code: {resp.status_code}")
                print("💡 Hint: Change 'contact@example.com' to your real email.")
                return

            data = resp.json()
            
            # The SEC JSON is a dictionary of dictionaries. Let's flatten it.
            for _, entry in data.items():
                ticker = entry['ticker']
                clean_name = self._clean_string(entry['title'])
                
                # Store mappings
                self.mapping[clean_name] = ticker
                self.names_list.append(clean_name)
                
            print(f"✅ Loaded {len(self.names_list)} public companies.")
            
        except Exception as e:
            print(f"⚠️ Failed to load SEC data: {e}. Ticker mapping will fail.")

    def _clean_string(self, text):
        """Standardizes company names for better matching."""
        if not isinstance(text, str): return ""
        text = text.upper()
        # Remove common legal suffixes to match "LOCKHEED MARTIN CORP" with "LOCKHEED MARTIN"
        replacements = [' INC', ' CORP', ' CORPORATION', ' COMPANY', ' PLC', ' LTD', ' GROUP', ',']
        for r in replacements:
            text = text.replace(r, '')
        return text.strip()

    def find_ticker(self, messy_name):
        """
        Uses Fuzzy Matching to find the closest public company name.
        Returns Ticker if confidence > 90, else None.
        """
        clean_input = self._clean_string(messy_name)
        
        # 1. Direct Hit (Fastest)
        if clean_input in self.mapping:
            return self.mapping[clean_input]

        # 2. Fuzzy Match (Slower but handles typos/variations)
        result = process.extractOne(
            clean_input, 
            self.names_list, 
            scorer=fuzz.token_sort_ratio
        )
        
        if result:
            match_name, score, _ = result
            # 88-90 is a safe threshold
            if score >= 88: 
                return self.mapping[match_name]
        
        return None