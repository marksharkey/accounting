#!/usr/bin/env python3
"""
Fix invoice line items by linking them to service_catalog entries based on description matching
"""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
from config import get_settings
from difflib import SequenceMatcher

settings = get_settings()


def similarity_ratio(a, b):
    """Calculate string similarity between 0 and 1"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fix_line_item_services():
    """Link line items to services based on description matching"""

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all line items without service_id
        line_items = session.query(models.InvoiceLineItem).filter(
            models.InvoiceLineItem.service_id == None
        ).all()

        print(f"Found {len(line_items)} line items without service_id")

        # Get all services
        services = session.query(models.ServiceCatalog).all()
        service_names = {s.id: s.name for s in services}

        matched = 0
        unmatched = []

        for li in line_items:
            description = li.description or ""

            # Find best matching service by description
            best_match = None
            best_score = 0.4  # Minimum threshold

            for service in services:
                score = similarity_ratio(description, service.name)
                if score > best_score:
                    best_score = score
                    best_match = service

            if best_match:
                li.service_id = best_match.id
                matched += 1
                if matched <= 10 or matched % 500 == 0:
                    print(
                        f"✓ '{description[:40]:40}' → {best_match.name} ({best_score:.2f})"
                    )
            else:
                unmatched.append(description)

        session.commit()

        print(f"\n{'='*70}")
        print(f"Matched:   {matched} line items")
        print(f"Unmatched: {len(unmatched)} line items")

        if unmatched:
            print(f"\nUnmatched descriptions (first 10):")
            for desc in unmatched[:10]:
                print(f"  - {desc[:60]}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    fix_line_item_services()
