"""
Functions for time-based decay of sentiment impact
"""
import math
from typing import Union

def apply_decay(age_hours: float, decay_type: str = "exponential", 
               half_life: float = 24.0) -> float:
    """
    Apply time decay to a sentiment value based on its age.
    
    Args:
        age_hours: Age of the event in hours
        decay_type: Type of decay function ('linear', 'exponential', 'half_life')
        half_life: Half-life parameter for exponential decay (in hours)
        
    Returns:
        Decay factor between 0 and 1
    """
    # No decay for age zero
    if age_hours <= 0:
        return 1.0
        
    if decay_type == "linear":
        # Linear decay: 1.0 at age 0, 0.0 at half_life
        if age_hours >= half_life:
            return 0.0
        return 1.0 - (age_hours / half_life)
        
    elif decay_type == "exponential":
        # Exponential decay: e^(-λt) where λ = ln(2)/half_life
        decay_constant = math.log(2) / half_life
        return math.exp(-decay_constant * age_hours)
        
    elif decay_type == "half_life":
        # Half-life decay: 0.5^(age/half_life)
        return math.pow(0.5, age_hours / half_life)
        
    else:
        # Default: no decay
        return 1.0