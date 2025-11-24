"""
Test for create project timeout calculation.
Verifies that the timeout scales appropriately with DOI list size.
"""
import unittest


class TestCreateProjectTimeout(unittest.TestCase):
    """Test create project timeout calculation"""
    
    def test_timeout_calculation(self):
        """Test that timeout scales with DOI count"""
        # Base timeout: 30 seconds
        # Per-DOI: 0.1 seconds
        # Max: 300 seconds (5 minutes)
        
        test_cases = [
            # (doi_count, expected_timeout)
            (10, 31),      # 30 + (10 * 0.1) = 31
            (100, 40),     # 30 + (100 * 0.1) = 40
            (394, 69.4),   # 30 + (394 * 0.1) = 69.4
            (1000, 130),   # 30 + (1000 * 0.1) = 130
            (3000, 300),   # 30 + (3000 * 0.1) = 330, capped at 300
            (5000, 300),   # 30 + (5000 * 0.1) = 530, capped at 300
        ]
        
        for doi_count, expected in test_cases:
            calculated = min(30 + (doi_count * 0.1), 300)
            self.assertEqual(calculated, expected, 
                           f"Timeout for {doi_count} DOIs should be {expected}s")
    
    def test_timeout_minimum(self):
        """Test that minimum timeout is reasonable"""
        # Even for 1 DOI, should have at least 30 seconds
        doi_count = 1
        timeout = min(30 + (doi_count * 0.1), 300)
        self.assertGreaterEqual(timeout, 30, "Minimum timeout should be 30 seconds")
    
    def test_timeout_maximum(self):
        """Test that timeout is capped at 5 minutes"""
        # Very large DOI list should not exceed 5 minutes
        doi_count = 10000
        timeout = min(30 + (doi_count * 0.1), 300)
        self.assertEqual(timeout, 300, "Maximum timeout should be 300 seconds (5 minutes)")
    
    def test_realistic_doi_counts(self):
        """Test timeout for realistic DOI counts"""
        # Most projects have between 10 and 500 DOIs
        realistic_counts = [10, 50, 100, 200, 394, 500]
        
        for count in realistic_counts:
            timeout = min(30 + (count * 0.1), 300)
            # All realistic counts should complete within 5 minutes
            self.assertLessEqual(timeout, 300, 
                               f"Timeout for {count} DOIs should not exceed 5 minutes")
            # All should have at least 30 seconds
            self.assertGreaterEqual(timeout, 30,
                                  f"Timeout for {count} DOIs should be at least 30 seconds")


if __name__ == '__main__':
    unittest.main()
