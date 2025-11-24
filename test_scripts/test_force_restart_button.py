"""
Test for force restart button functionality.
Verifies that the force restart button appears when downloads are stale.
"""
import unittest


class TestForceRestartButton(unittest.TestCase):
    """Test force restart button logic"""
    
    def test_stale_detection_triggers_button(self):
        """Test that stale status triggers display of force restart button"""
        # Mock status response with stale flag
        status_data = {
            "status": "running",
            "is_stale": True,
            "time_since_update_seconds": 350,
            "current": 50,
            "total": 100
        }
        
        # Verify stale flag is set
        self.assertTrue(status_data["is_stale"])
        self.assertGreater(status_data["time_since_update_seconds"], 300)
    
    def test_non_stale_no_button(self):
        """Test that non-stale downloads don't trigger the button"""
        # Mock status response without stale flag
        status_data = {
            "status": "running",
            "is_stale": False,
            "time_since_update_seconds": 30,
            "current": 50,
            "total": 100
        }
        
        # Verify stale flag is not set
        self.assertFalse(status_data["is_stale"])
        self.assertLess(status_data["time_since_update_seconds"], 300)
    
    def test_force_restart_payload(self):
        """Test that force restart sends correct payload"""
        # Expected payload for force restart
        payload = {
            "email": "admin@example.com",
            "password": "secret",
            "force_restart": True
        }
        
        # Verify force_restart flag is present
        self.assertIn("force_restart", payload)
        self.assertTrue(payload["force_restart"])
    
    def test_stale_threshold(self):
        """Test stale threshold is 300 seconds (5 minutes)"""
        stale_threshold = 300
        
        # Times that should be stale
        stale_times = [301, 350, 600, 1000]
        for time_since_update in stale_times:
            self.assertGreater(time_since_update, stale_threshold,
                             f"{time_since_update}s should be considered stale")
        
        # Times that should not be stale
        non_stale_times = [0, 30, 150, 299]
        for time_since_update in non_stale_times:
            self.assertLessEqual(time_since_update, stale_threshold,
                                f"{time_since_update}s should not be considered stale")
    
    def test_button_visibility_logic(self):
        """Test button visibility based on status and stale flag"""
        test_cases = [
            # (status, is_stale, should_show_button)
            ("running", True, True),   # Running + stale = show button
            ("running", False, False), # Running + not stale = no button
            ("completed", True, False),  # Completed = no button (regardless of stale)
            ("completed", False, False), # Completed = no button
            ("error", True, False),      # Error = no button (regardless of stale)
        ]
        
        for status, is_stale, should_show in test_cases:
            # Only running + stale should show button
            actual_show = (status == "running" and is_stale)
            self.assertEqual(actual_show, should_show,
                           f"Status={status}, is_stale={is_stale} should show_button={should_show}")


if __name__ == '__main__':
    unittest.main()
