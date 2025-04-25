"""
Impact scoring for sentiment events
"""
from typing import Dict, Any

def calculate_impact(event: Dict[str, Any]) -> float:
    """
    Calculate the impact factor of a sentiment event.
    
    Args:
        event: Sentiment event dictionary with metadata
        
    Returns:
        Impact factor between 0.1 and 10.0
    """
    # Base impact starts at 1.0
    impact = 1.0
    
    # Source weighting
    source_weights = {
        'news': 1.5,     # News articles are most trusted
        'reddit': 0.8,   # Reddit posts are somewhat trusted
        'twitter': 0.5,  # Tweets are less trusted
    }
    
    # Apply source weight if available
    if 'source' in event:
        source = event.get('source', '').lower()
        impact *= source_weights.get(source, 1.0)
    
    # Apply multiplier based on popularity/engagement
    if 'engagement' in event:
        engagement = event.get('engagement', 0)
        
        # Logarithmic scaling for engagement
        if engagement > 0:
            # log(1) = 0, log(10) = 1, log(100) = 2, etc.
            log_scale = min(3.0, max(0, 0.5 * (engagement / 10)))
            impact *= (1.0 + log_scale)
    
    # Apply multiplier based on author reputation if available
    if 'author_reputation' in event:
        reputation = event.get('author_reputation', 0.5)  # Default to mid-range
        impact *= max(0.5, min(2.0, reputation))
    
    # Apply multiplier based on content length if available
    if 'content_length' in event:
        length = event.get('content_length', 0)
        
        # Longer content gets slightly higher impact, up to 1.5x
        # Content length ranges are approximate characters:
        # 0-50: 0.8x (short tweet/title)
        # 50-200: 1.0x (long tweet, short comment)
        # 200-500: 1.2x (medium comment/post)
        # 500+: 1.5x (longer article/analysis)
        if length < 50:
            impact *= 0.8
        elif length > 500:
            impact *= 1.5
        elif length > 200:
            impact *= 1.2
    
    # Apply confidence multiplier if available
    if 'confidence' in event:
        confidence = event.get('confidence', 0.5)  # Default to mid-range
        impact *= max(0.5, min(1.5, confidence))
    
    # Ensure impact is within reasonable bounds
    return max(0.1, min(10.0, impact))