"""
services.export_service
=======================
Dataset export (Excel / CSV). Delegates to the existing
``core.exporter`` — wrapper exists for import-path consistency only.
"""

from __future__ import annotations

from core.exporter import export_csv, export_excel  # noqa: F401

__all__ = ["export_excel", "export_csv"]
