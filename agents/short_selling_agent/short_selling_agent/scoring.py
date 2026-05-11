# scoring.py
def calculate_short_conviction_score(data: dict) -> Dict[str, Any]:
    """
    Assign weights to high-conviction short signals.
    Returns { 'score': 0-100, 'breakdown': { signal: score }, 'verdict': 'strong/medium/weak' }
    """
    weights = {
        'below_sma200': 20,
        'rsi_20_to_40': 15,
        'adx_above_25': 15,
        'volume_spike': 10,
        'high_short_interest': 15,
        'negative_earnings_surprise': 10,
        'bearish_sma_cross': 10,
        'chop_downward': 5  # Choppiness decreasing → trend forming
    }

    score = 0
    breakdown = {}

    price_hist = data['price']
    indicators = data['indicators']
    fundamentals = data['fundamentals']
    
    if not price_hist:
        return {'score': 0, 'breakdown': {}, 'verdict': 'none'}

    latest_price = price_hist[-1]['adjClose']
    latest_date = price_hist[-1]['date']

    # --- 1. Below SMA200 ---
    sma200_vals = [i for i in indicators['sma200'] if i['date'] == latest_date]
    below_sma200 = sma200_vals[0]['value'] > latest_price if sma200_vals and sma200_vals[0]['value'] else False
    breakdown['below_sma200'] = weights['below_sma200'] if below_sma200 else 0
    score += breakdown['below_sma200']

    # --- 2. RSI between 20 and 40 ---
    rsi_vals = [i for i in indicators['rsi'] if i['date'] == latest_date]
    rsi_ok = 20 < rsi_vals[0]['value'] < 40 if rsi_vals and rsi_vals[0]['value'] else False
    breakdown['rsi_20_to_40'] = weights['rsi_20_to_40'] if rsi_ok else 0
    score += breakdown['rsi_20_to_40']

    # --- 3. ADX > 25 ---
    adx_vals = [i for i in indicators['adx'] if i['date'] == latest_date]
    adx_strong = adx_vals[0]['value'] > 25 if adx_vals and adx_vals[0]['value'] else False
    breakdown['adx_above_25'] = weights['adx_above_25'] if adx_strong else 0
    score += breakdown['adx_above_25']

    # --- 4. Volume > 1.5x avg ---
    recent_vol = [p['volume'] for p in price_hist[-20:]]
    avg_vol = sum(recent_vol) / len(recent_vol)
    volume_spiking = price_hist[-1]['volume'] > 1.5 * avg_vol
    breakdown['volume_spike'] = weights['volume_spike'] if volume_spiking else 0
    score += breakdown['volume_spike']

    # --- 5. Short interest > 10% ---
    short_pct = fundamentals['short_interest']['shortPercent']
    high_short = short_pct and short_pct > 0.10
    breakdown['high_short_interest'] = weights['high_short_interest'] if high_short else 0
    score += breakdown['high_short_interest']

    # --- 6. Negative earnings surprise ---
    earnings = fundamentals['recent_earnings']
    negative_surprise = any(e['surprise'] and e['surprise'] < -0.10 for e in earnings)
    breakdown['negative_earnings_surprise'] = weights['negative_earnings_surprise'] if negative_surprise else 0
    score += breakdown['negative_earnings_surprise']

    # --- 7. SMA50 < SMA200 (bearish alignment) ---
    sma50_vals = [i for i in indicators['sma50'] if i['date'] == latest_date]
    sma200_vals = [i for i in indicators['sma200'] if i['date'] == latest_date]
    bearish_sma = (
        sma50_vals and sma200_vals 
        and sma50_vals[0]['value'] 
        and sma200_vals[0]['value'] 
        and sma50_vals[0]['value'] < sma200_vals[0]['value']
    )
    breakdown['bearish_sma_cross'] = weights['bearish_sma_cross'] if bearish_sma else 0
    score += breakdown['bearish_sma_cross']

    # --- 8. Choppiness decreasing? (trend forming) ---
    chop_vals = indicators.get('chop', [])
    if len(chop_vals) >= 5:
        recent_chop = [v['value'] for v in chop_vals[-5:] if v['value']]
        chop_downward = len(recent_chop) > 1 and recent_chop[-1] < recent_chop[0]
        breakdown['chop_downward'] = weights['chop_downward'] if chop_downward else 0
        score += breakdown['chop_downward']

    # --- Final Verdict ---
    if score >= 70:
        verdict = 'strong'
    elif score >= 50:
        verdict = 'medium'
    else:
        verdict = 'weak'

    return {
        'score': round(score, 1),
        'breakdown': breakdown,
        'verdict': verdict,
        'as_of': data['as_of_date'],
        'symbol': data['symbol']
    }