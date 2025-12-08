"""
إعدادات النظام الشاملة
Professional Configuration Settings
"""

import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data Directories
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
EXPORT_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"

# File Paths
CHANNELS_FILE = DATA_DIR / "channels.json"
PRICING_HISTORY_FILE = DATA_DIR / "pricing_history.csv"
RAW_MATERIALS_FILE = DATA_DIR / "raw_materials_template.csv"
PRODUCTS_FILE = DATA_DIR / "products_template.csv"
PACKAGES_FILE = DATA_DIR / "packages_template.csv"

# UI Settings
UI_CONFIG = {
    "theme": {
        "primaryColor": "#1E88E5",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#F5F5F5",
        "textColor": "#1A1A1A",
        "font": "sans serif"
    },
    "layout": "wide",
    "sidebar_state": "expanded"
}

# Business Rules
BUSINESS_RULES = {
    "default_vat_rate": 0.15,  # 15% VAT
    "default_payment_fee": 0.025,  # 2.5% Payment Gateway
    "min_profit_margin": 0.05,  # 5% Minimum
    "recommended_profit_margin": 0.15,  # 15% Recommended
    "max_discount_rate": 0.50,  # 50% Maximum Discount
}

# Data Validation Rules
VALIDATION_RULES = {
    "max_file_size_mb": 10,
    "required_columns": {
        "materials": ["material_sku", "material_name", "category", "unit", "cost_per_unit"],
        "products": ["product_sku", "product_name", "material_code", "quantity"],
        "packages": ["package_sku", "package_name", "product_sku", "quantity"]
    }
}

# Export Formats
EXPORT_FORMATS = {
    "csv": {"encoding": "utf-8-sig", "index": False},
    "excel": {"engine": "openpyxl", "index": False},
    "json": {"orient": "records", "force_ascii": False, "indent": 2}
}

# Analytics Settings
ANALYTICS_CONFIG = {
    "chart_height": 500,
    "chart_colors": {
        "primary": "#1E88E5",
        "secondary": "#43A047",
        "warning": "#FB8C00",
        "danger": "#E53935",
        "info": "#00ACC1"
    },
    "top_items_count": 10
}

# Cache Settings
CACHE_CONFIG = {
    "ttl": 3600,  # 1 hour
    "max_entries": 100
}

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "app.log",
            "formatter": "default"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}

# Create necessary directories
for directory in [DATA_DIR, BACKUP_DIR, EXPORT_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
