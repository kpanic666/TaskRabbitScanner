#!/usr/bin/env python3
"""
Test script to verify name validation function works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from taskrabbit_parser import TaskRabbitParser

def test_name_validation():
    """Test the name validation function with various inputs"""
    parser = TaskRabbitParser()
    
    test_cases = [
        # Valid names (should return True)
        ("Laurette O.", True),
        ("eva c.", True),
        ("Larisa Y.", True),
        ("Moriah T.", True),
        ("Arabella C.", True),
        ("John Smith", True),
        ("Maria", True),
        ("David L.", True),
        
        # Invalid names (should return False)
        ("How I can help:", False),
        ("About me:", False),
        ("My experience", False),
        ("What I do", False),
        ("Services offered", False),
        ("Contact me", False),
        ("Book now", False),
        ("View profile", False),
        ("$25/hr", False),
        ("5 stars", False),
        ("", False),
        ("a", False),
        ("123456", False),
        ("!!!", False),
    ]
    
    print("Testing name validation function...")
    print("=" * 50)
    
    all_passed = True
    for test_name, expected in test_cases:
        result = parser.is_valid_person_name(test_name)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} | '{test_name}' -> {result} (expected {expected})")
        
        if result != expected:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! Name validation is working correctly.")
    else:
        print("⚠️  Some tests failed. Name validation needs adjustment.")
    
    return all_passed

if __name__ == "__main__":
    test_name_validation()
