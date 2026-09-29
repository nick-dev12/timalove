#!/usr/bin/env python
"""Active le mode Parcours curated (grille du jour) — recommandé prod / review stores."""
import os
import sys

ROOT = os.environ.get("TIMALOVE_ROOT", "/home/jomas/timalove/timalove")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from core.controllers import app_config_controller

cfg = app_config_controller.get_app_config()
cfg["explorer_curated_mode"] = True
cfg["guided_messages_enabled"] = True
app_config_controller.save_app_config(cfg)
print("explorer_curated_mode", app_config_controller.explorer_curated_mode_enabled())
print("guided_messages_enabled", app_config_controller.guided_messages_enabled())
