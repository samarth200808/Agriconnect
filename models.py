from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Farmer(db.Model):
    __tablename__ = 'farmers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    land_size = db.Column(db.String(50), nullable=False)
    land_place = db.Column(db.String(150), nullable=False)
    aadhaar_number = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ads = db.relationship('ProduceAd', backref='farmer', lazy=True)


class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    business_type = db.Column(db.String(100), nullable=False)
    gst_number = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    offers = db.relationship('Offer', backref='company', lazy=True)


class ProduceAd(db.Model):
    __tablename__ = 'produce_ads'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'), nullable=False)
    crop_name = db.Column(db.String(100), nullable=False)
    certificate_filename = db.Column(db.String(255), nullable=False)
    harvest_date = db.Column(db.String(20), nullable=False)
    total_quantity = db.Column(db.Float, nullable=False)
    price_per_kg = db.Column(db.Float, nullable=False)
    min_buying_quantity = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Available')  # 'Available' or 'Sold Out'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    offers = db.relationship('Offer', backref='ad', lazy=True, order_by='Offer.created_at.desc()')


class Offer(db.Model):
    __tablename__ = 'offers'
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('produce_ads.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    requested_quantity = db.Column(db.Float, nullable=False)
    quote_price = db.Column(db.Float, nullable=False)
    last_hike_amount = db.Column(db.Float, default=0.0)
    turn = db.Column(db.String(20), default='farmer')  # 'farmer', 'company', 'closed'
    status = db.Column(db.String(30), default='Pending')  # 'Pending', 'Countered', 'Accepted', 'No Negotiation', 'Paid'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total_amount(self):
        return round(self.requested_quantity * self.quote_price, 2)
