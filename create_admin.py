#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to create an admin user in the database.
Usage: python3 create_admin.py
"""

import os
import sys
import getpass
from t2t_store import create_admin_user, init_db

# Import configuration
try:
    from config import DB_PATH
except ImportError:
    # Fallback to environment variable if config.py doesn't exist
    DB_PATH = os.environ.get("T2T_DB", "t2t_training.db")

def main():
    print("=== Create Admin User ===\n")
    
    # Ensure database exists
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} does not exist. Creating...")
        init_db(DB_PATH)
        print(f"✓ Created database: {DB_PATH}\n")
    else:
        print(f"Using existing database: {DB_PATH}\n")
    
    # Get admin email
    email = input("Admin email: ").strip()
    if not email:
        print("Error: Email cannot be empty")
        sys.exit(1)
    
    # Get password (hidden input)
    password = getpass.getpass("Admin password: ")
    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)
    
    # Confirm password
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Error: Passwords do not match")
        sys.exit(1)
    
    # Create admin user
    print("\nCreating admin user...")
    success = create_admin_user(DB_PATH, email, password)
    
    if success:
        print(f"✓ Admin user created successfully: {email}")
        print("\nYou can now login to the Admin panel with these credentials.")
    else:
        print("✗ Failed to create admin user")
        sys.exit(1)

if __name__ == "__main__":
    main()
