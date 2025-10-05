#!/usr/bin/env python3
"""Test script to discover LSL streams"""

from pylsl import resolve_streams
import time

print("Searching for LSL streams (waiting 2 seconds)...")
streams = resolve_streams(wait_time=2.0)

print(f"\nFound {len(streams)} stream(s):")
for s in streams:
    print(f"  - Name: {s.name()}")
    print(f"    Type: {s.type()}")
    print(f"    Channels: {s.channel_count()}")
    print(f"    Source ID: {s.source_id()}")
    print(f"    Hostname: {s.hostname()}")
    print()
