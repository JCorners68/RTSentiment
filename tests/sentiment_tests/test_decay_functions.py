import unittest
import math
from sentiment_analyzer.models.decay_functions import apply_decay


class TestDecayFunctions(unittest.TestCase):
    
    def test_linear_decay(self):
        """Test linear decay function."""
        # At age 0, decay should be 1.0
        self.assertEqual(apply_decay(0, "linear", 24), 1.0)
        
        # At half-life (24 hours), decay should be 0.0
        self.assertEqual(apply_decay(24, "linear", 24), 0.0)
        
        # At 12 hours (half of half-life), decay should be 0.5
        self.assertAlmostEqual(apply_decay(12, "linear", 24), 0.5)
        
        # Beyond half-life, decay should be 0.0
        self.assertEqual(apply_decay(30, "linear", 24), 0.0)
        
    def test_exponential_decay(self):
        """Test exponential decay function."""
        # At age 0, decay should be 1.0
        self.assertAlmostEqual(apply_decay(0, "exponential", 24), 1.0)
        
        # At half-life (24 hours), decay should be 0.5
        self.assertAlmostEqual(apply_decay(24, "exponential", 24), 0.5, places=5)
        
        # At 2x half-life (48 hours), decay should be 0.25
        self.assertAlmostEqual(apply_decay(48, "exponential", 24), 0.25, places=5)
        
        # Custom calculation to verify
        decay_constant = math.log(2) / 24
        expected = math.exp(-decay_constant * 36)
        self.assertAlmostEqual(apply_decay(36, "exponential", 24), expected)
        
    def test_half_life_decay(self):
        """Test half-life decay function."""
        # At age 0, decay should be 1.0
        self.assertEqual(apply_decay(0, "half_life", 24), 1.0)
        
        # At half-life (24 hours), decay should be 0.5
        self.assertEqual(apply_decay(24, "half_life", 24), 0.5)
        
        # At 2x half-life (48 hours), decay should be 0.25
        self.assertEqual(apply_decay(48, "half_life", 24), 0.25)
        
        # At 3x half-life (72 hours), decay should be 0.125
        self.assertEqual(apply_decay(72, "half_life", 24), 0.125)
        
    def test_default_decay(self):
        """Test default decay behavior."""
        # Unknown decay type should default to no decay (return 1.0)
        self.assertEqual(apply_decay(10, "unknown_type", 24), 1.0)


if __name__ == '__main__':
    unittest.main()