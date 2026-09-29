#!/usr/bin/env python
"""Inspecte le mode explorer (curated vs swipe) sur le VPS."""
import os
import sys

ROOT = os.environ.get("TIMALOVE_ROOT", "/home/jomas/timalove/timalove")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from core.controllers import app_config_controller as c

cfg = c.get_app_config()
print("explorer_curated_mode", cfg.get("explorer_curated_mode"))
print("guided_messages_enabled", cfg.get("guided_messages_enabled"))
print("explorer_search_enabled", cfg.get("explorer_search_enabled"))
print("native_ua", c.explorer_curated_mode_active(user_agent="Mozilla TimaLoveApp/1.0"))
print("chrome_ua", c.explorer_curated_mode_active(user_agent="Mozilla Chrome"))
