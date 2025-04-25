import unittest
from sentiment_analyzer.models.impact_scoring import calculate_impact


class TestImpactScoring(unittest.TestCase):
    
    def test_source_weighting(self):
        """Test impact calculation based on source weighting."""
        # Test news source (highest weight)
        news_event = {
            'source': 'news',
            'sentiment': 0.5
        }
        
        # Test reddit source (medium weight)
        reddit_event = {
            'source': 'reddit',
            'sentiment': 0.5
        }
        
        # Test twitter source (lowest weight)
        twitter_event = {
            'source': 'twitter',
            'sentiment': 0.5
        }
        
        # Test unknown source (default weight)
        unknown_event = {
            'source': 'unknown',
            'sentiment': 0.5
        }
        
        news_impact = calculate_impact(news_event)
        reddit_impact = calculate_impact(reddit_event)
        twitter_impact = calculate_impact(twitter_event)
        unknown_impact = calculate_impact(unknown_event)
        
        # Higher credibility source should have higher impact
        self.assertGreater(news_impact, reddit_impact)
        self.assertGreater(reddit_impact, twitter_impact)
        self.assertGreaterEqual(unknown_impact, twitter_impact)  # Unknown defaults to 1.0
        
    def test_engagement_metrics(self):
        """Test impact calculation based on engagement metrics."""
        # Event with high engagement
        high_engage = {
            'source': 'news',
            'engagement': 1000,
            'sentiment': 0.5
        }
        
        # Event with low engagement
        low_engage = {
            'source': 'news',
            'engagement': 10,
            'sentiment': 0.5
        }
        
        # Event with no engagement field
        no_engage = {
            'source': 'news',
            'sentiment': 0.5
        }
        
        high_impact = calculate_impact(high_engage)
        low_impact = calculate_impact(low_engage)
        no_engage_impact = calculate_impact(no_engage)
        
        # Higher engagement should result in higher impact
        self.assertGreater(high_impact, low_impact)
        self.assertGreater(low_impact, no_engage_impact)
        
    def test_author_reputation(self):
        """Test impact calculation based on author reputation."""
        # High reputation author
        high_rep = {
            'author_reputation': 1.8,
            'sentiment': 0.5
        }
        
        # Low reputation author
        low_rep = {
            'author_reputation': 0.5,
            'sentiment': 0.5
        }
        
        high_rep_impact = calculate_impact(high_rep)
        low_rep_impact = calculate_impact(low_rep)
        
        # Higher reputation should result in higher impact
        self.assertGreater(high_rep_impact, low_rep_impact)
        
    def test_content_length(self):
        """Test impact calculation based on content length."""
        # Short content
        short_content = {
            'content_length': 30,
            'sentiment': 0.5
        }
        
        # Medium content
        medium_content = {
            'content_length': 150,
            'sentiment': 0.5
        }
        
        # Long content
        long_content = {
            'content_length': 600,
            'sentiment': 0.5
        }
        
        short_impact = calculate_impact(short_content)
        medium_impact = calculate_impact(medium_content)
        long_impact = calculate_impact(long_content)
        
        # Longer content should have higher impact
        self.assertLess(short_impact, medium_impact)
        self.assertLess(medium_impact, long_impact)
        
    def test_confidence(self):
        """Test impact calculation based on confidence."""
        # High confidence
        high_conf = {
            'confidence': 1.0,
            'sentiment': 0.5
        }
        
        # Low confidence
        low_conf = {
            'confidence': 0.5,
            'sentiment': 0.5
        }
        
        high_conf_impact = calculate_impact(high_conf)
        low_conf_impact = calculate_impact(low_conf)
        
        # Higher confidence should result in higher impact
        self.assertGreater(high_conf_impact, low_conf_impact)
        
    def test_impact_bounds(self):
        """Test that impact is always within bounds."""
        # Empty event should get default impact
        empty_event = {}
        self.assertEqual(calculate_impact(empty_event), 1.0)
        
        # Create some extreme events to test bounds
        min_event = {
            'source': 'twitter',
            'author_reputation': 0.1,
            'content_length': 10,
            'confidence': 0.1
        }
        
        max_event = {
            'source': 'news',
            'engagement': 10000,
            'author_reputation': 5.0,
            'content_length': 10000,
            'confidence': 5.0
        }
        
        min_impact = calculate_impact(min_event)
        max_impact = calculate_impact(max_event)
        
        # Impact should be bounded between 0.1 and 10.0
        self.assertGreaterEqual(min_impact, 0.1)
        self.assertLessEqual(max_impact, 10.0)


if __name__ == '__main__':
    unittest.main()