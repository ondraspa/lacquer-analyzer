#!/usr/bin/env python3
"""Lacquer Chemical Analyzer - Main Entry Point

Desktop application for analyzing lacquer formulations
for Burkle curtain coaters with plating compatibility
(silvering + nickel sulfamate).
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lacquer Chemical Analyzer")
    app.setOrganizationName("LacquerTech")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()