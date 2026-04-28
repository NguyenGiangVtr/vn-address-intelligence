#!/bin/bash
echo "Setting up database tables..."
export PYTHONPATH=$PYTHONPATH:.
python scripts/create_tables.py
