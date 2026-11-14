"""
Helper script to view all records in the AgriConnect SQLite database.
Run with: python3.11 view_db.py
"""
from app import app
from models import db, Farmer, Company, ProduceAd, Offer


def view_data():
    with app.app_context():
        print("=" * 60)
        print("FARMERS")
        print("=" * 60)
        farmers = Farmer.query.all()
        if not farmers:
            print("No farmers found.")
        for f in farmers:
            print(f"ID: {f.id} | Name: {f.name} | Email: {f.email} | Land: {f.land_size} ({f.land_place}) | Aadhaar: {f.aadhaar_number}")

        print("\n" + "=" * 60)
        print("COMPANIES")
        print("=" * 60)
        companies = Company.query.all()
        if not companies:
            print("No companies found.")
        for c in companies:
            print(f"ID: {c.id} | Company: {c.company_name} | Email: {c.email} | Business Type: {c.business_type} | GST: {c.gst_number}")

        print("\n" + "=" * 60)
        print("PRODUCE ADS")
        print("=" * 60)
        ads = ProduceAd.query.all()
        if not ads:
            print("No produce ads found.")
        for a in ads:
            print(f"ID: {a.id} | Farmer ID: {a.farmer_id} | Crop: {a.crop_name} | Qty: {a.total_quantity} kg | Price/kg: ₹{a.price_per_kg} | Status: {a.status}")

        print("\n" + "=" * 60)
        print("OFFERS & NEGOTIATIONS")
        print("=" * 60)
        offers = Offer.query.all()
        if not offers:
            print("No offers found.")
        for o in offers:
            print(f"ID: {o.id} | Ad ID: {o.ad_id} | Company ID: {o.company_id} | Requested: {o.requested_quantity} kg | Quote: ₹{o.quote_price}/kg | Status: {o.status} | Turn: {o.turn}")
        print("=" * 60)


if __name__ == '__main__':
    view_data()
