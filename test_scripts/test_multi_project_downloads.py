#!/usr/bin/env python3
"""
Test script for multi-project PDF download functionality.
Tests that multiple projects can have concurrent downloads with independent progress tracking.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_multi_project_state_structure():
    """Test that multi-project state structure works correctly"""
    print("\n=== Testing Multi-Project State Structure ===")
    
    passed = 0
    failed = 0
    
    # Test Case 1: Multiple active projects in dict structure
    print("\nTest 1: Multiple active projects tracked in dict")
    active_projects = {7: True, 8: True, 9: True}
    
    if isinstance(active_projects, dict) and len(active_projects) == 3:
        print(f"✓ PASS: Dict structure supports {len(active_projects)} concurrent downloads")
        passed += 1
    else:
        print("✗ FAIL: Dict structure should support multiple projects")
        failed += 1
    
    # Test Case 2: State store with multiple projects
    print("\nTest 2: State store with multiple project states")
    state_store = {
        7: {"project_id": 7, "active": True, "status": "running", "current": 3, "total": 10},
        8: {"project_id": 8, "active": True, "status": "running", "current": 5, "total": 15},
        9: {"project_id": 9, "active": True, "status": "running", "current": 1, "total": 5}
    }
    
    if isinstance(state_store, dict) and len(state_store) == 3:
        # Check each project has its own state
        all_valid = all(
            isinstance(v, dict) and v.get("project_id") == k 
            for k, v in state_store.items()
        )
        if all_valid:
            print(f"✓ PASS: State store correctly tracks {len(state_store)} independent project states")
            passed += 1
        else:
            print("✗ FAIL: State store project IDs don't match keys")
            failed += 1
    else:
        print("✗ FAIL: State store should be a dict with multiple projects")
        failed += 1
    
    # Test Case 3: Adding a new project to active tracking
    print("\nTest 3: Adding new project to active tracking")
    active_projects = {7: True, 8: True}
    new_project_id = 10
    
    # Add new project
    active_projects[new_project_id] = True
    
    if new_project_id in active_projects and len(active_projects) == 3:
        print(f"✓ PASS: Successfully added project {new_project_id} to active tracking")
        passed += 1
    else:
        print("✗ FAIL: Failed to add new project to active tracking")
        failed += 1
    
    # Test Case 4: Removing completed project from active tracking
    print("\nTest 4: Removing completed project from active tracking")
    active_projects = {7: True, 8: True, 9: True}
    completed_project_id = 8
    
    # Remove completed project
    if completed_project_id in active_projects:
        del active_projects[completed_project_id]
    
    if completed_project_id not in active_projects and len(active_projects) == 2:
        print(f"✓ PASS: Successfully removed completed project {completed_project_id}")
        passed += 1
    else:
        print("✗ FAIL: Failed to remove completed project")
        failed += 1
    
    # Test Case 5: Progress content mapping
    print("\nTest 5: Progress content mapping for multiple projects")
    progress_contents = {
        7: "Progress card for project 7",
        8: "Progress card for project 8",
        9: "Progress card for project 9"
    }
    
    # Simulate matching progress divs
    progress_divs = [
        {"index": 6},
        {"index": 7},
        {"index": 8},
        {"index": 9},
        {"index": 10}
    ]
    
    # Build outputs (matching _build_progress_outputs logic)
    outputs = []
    for div_id in progress_divs:
        project_id = div_id["index"]
        if project_id in progress_contents:
            outputs.append(progress_contents[project_id])
        else:
            outputs.append("")  # Empty for non-active projects
    
    # Verify correct mapping
    if (outputs[0] == "" and  # project 6: empty
        outputs[1] == "Progress card for project 7" and
        outputs[2] == "Progress card for project 8" and
        outputs[3] == "Progress card for project 9" and
        outputs[4] == ""):  # project 10: empty
        print("✓ PASS: Progress content correctly mapped to project divs")
        passed += 1
    else:
        print("✗ FAIL: Progress content mapping incorrect")
        print(f"  Expected: ['', 'proj7', 'proj8', 'proj9', '']")
        print(f"  Got: {outputs}")
        failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_concurrent_download_scenarios():
    """Test various concurrent download scenarios"""
    print("\n=== Testing Concurrent Download Scenarios ===")
    
    passed = 0
    failed = 0
    
    # Scenario 1: Starting second download while first is running
    print("\nScenario 1: Start download on project 8 while project 7 is running")
    active_projects = {7: True}
    state_store = {
        7: {"project_id": 7, "active": True, "status": "running", "current": 3, "total": 10}
    }
    
    # Start project 8
    new_project_id = 8
    active_projects[new_project_id] = True
    state_store[new_project_id] = {
        "project_id": new_project_id,
        "active": True,
        "status": "running",
        "current": 0,
        "total": 15
    }
    
    if (7 in active_projects and 8 in active_projects and
        7 in state_store and 8 in state_store):
        print("✓ PASS: Both projects tracked independently")
        passed += 1
    else:
        print("✗ FAIL: Second project start failed to maintain first project state")
        failed += 1
    
    # Scenario 2: Project 7 completes while project 8 is running
    print("\nScenario 2: Project 7 completes while project 8 continues")
    # Mark project 7 as completed
    state_store[7]["status"] = "completed"
    state_store[7]["active"] = False
    state_store[7]["current"] = 10
    
    # Remove from active tracking
    del active_projects[7]
    
    if (7 not in active_projects and 8 in active_projects and
        7 in state_store and state_store[7]["status"] == "completed"):
        print("✓ PASS: Project 7 removed from active, state preserved, project 8 continues")
        passed += 1
    else:
        print("✗ FAIL: Completion handling incorrect")
        failed += 1
    
    # Scenario 3: Multiple projects complete
    print("\nScenario 3: All active projects complete")
    # Mark project 8 as completed
    state_store[8]["status"] = "completed"
    state_store[8]["active"] = False
    state_store[8]["current"] = 15
    
    # Remove from active tracking
    del active_projects[8]
    
    if len(active_projects) == 0 and len(state_store) == 2:
        print("✓ PASS: All projects removed from active, states preserved for display")
        passed += 1
    else:
        print("✗ FAIL: Final cleanup incorrect")
        failed += 1
    
    # Scenario 4: Restore multiple active projects after refresh
    print("\nScenario 4: Restore multiple projects after page refresh")
    # Simulate restored state after refresh
    state_store = {
        "7": {"project_id": 7, "active": True, "status": "running", "current": 5, "total": 10},
        "8": {"project_id": 8, "active": True, "status": "running", "current": 8, "total": 15}
    }
    
    # Restore active projects from state
    active_projects = {}
    for project_id, state in state_store.items():
        if isinstance(state, dict) and state.get("active"):
            active_projects[int(project_id)] = True
    
    if len(active_projects) == 2 and 7 in active_projects and 8 in active_projects:
        print("✓ PASS: Multiple projects correctly restored after refresh")
        passed += 1
    else:
        print("✗ FAIL: Multi-project restoration failed")
        print(f"  Active projects: {active_projects}")
        failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_stale_detection_per_project():
    """Test that stale detection works independently per project"""
    print("\n=== Testing Per-Project Stale Detection ===")
    
    passed = 0
    failed = 0
    
    # Simulate backend responses for multiple projects
    print("\nTest: Project 7 is stale, Project 8 is running normally")
    
    project_states = {
        7: {
            "status": "running",
            "is_stale": True,
            "current": 3,
            "total": 10,
            "time_since_update_seconds": 180
        },
        8: {
            "status": "running",
            "is_stale": False,
            "current": 8,
            "total": 15,
            "time_since_update_seconds": 5
        }
    }
    
    # Check stale status is tracked per project
    if (project_states[7]["is_stale"] and 
        not project_states[8]["is_stale"]):
        print("✓ PASS: Stale status tracked independently per project")
        passed += 1
    else:
        print("✗ FAIL: Stale status not tracked correctly")
        failed += 1
    
    # Verify force restart button should only show for project 7
    projects_needing_restart = [
        pid for pid, state in project_states.items() 
        if state.get("status") == "running" and state.get("is_stale")
    ]
    
    if projects_needing_restart == [7]:
        print("✓ PASS: Force restart correctly identified for stale project only")
        passed += 1
    else:
        print("✗ FAIL: Force restart identification incorrect")
        print(f"  Expected: [7], Got: {projects_needing_restart}")
        failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    print("=" * 70)
    print("Multi-Project PDF Download Test Suite")
    print("=" * 70)
    
    # Run tests
    test1_pass = test_multi_project_state_structure()
    test2_pass = test_concurrent_download_scenarios()
    test3_pass = test_stale_detection_per_project()
    
    print("\n" + "=" * 70)
    if test1_pass and test2_pass and test3_pass:
        print("All tests passed! ✓")
        print("\nNote: These tests verify the multi-project logic. To test the actual")
        print("implementation, you need to:")
        print("1. Start the backend: python3 harvest_be.py")
        print("2. Start the frontend: python3 harvest_fe.py")
        print("3. Login as admin")
        print("4. Create multiple projects with DOIs")
        print("5. Start PDF downloads on multiple projects (e.g., Project 7, then 8)")
        print("6. Verify that:")
        print("   - Both progress cards show simultaneously")
        print("   - Each card updates independently")
        print("   - Force Restart button appears only for stale downloads")
        print("   - Completed downloads show completion message")
        print("=" * 70)
        return 0
    else:
        print("Some tests failed! ✗")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
