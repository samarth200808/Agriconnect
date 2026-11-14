import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, Farmer, Company, ProduceAd, Offer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'agriconnect-college-project-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agriconnect.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'certificates')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

db.init_app(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_role') != role or not session.get('user_id'):
                flash(f'Please log in as a {role.capitalize()} to access this page.', 'warning')
                return redirect(url_for(f'{role}_auth'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def lock_deal_and_reduce_inventory(offer):
    """Locks an accepted deal, deducts sold quantity from the ad, and marks Sold Out if 0."""
    ad = offer.ad
    if ad.status == 'Sold Out' or ad.total_quantity < offer.requested_quantity:
        return False, f"Insufficient quantity left on '{ad.crop_name}' (Available: {ad.total_quantity} kg)."

    offer.status = 'Accepted'
    offer.turn = 'closed'
    ad.total_quantity = round(ad.total_quantity - offer.requested_quantity, 2)

    if ad.total_quantity <= 0:
        ad.total_quantity = 0
        ad.status = 'Sold Out'
    elif ad.total_quantity < ad.min_buying_quantity:
        ad.min_buying_quantity = ad.total_quantity

    db.session.commit()
    return True, f"Deal locked for {offer.requested_quantity} kg at ₹{offer.quote_price}/kg!"


@app.route('/')
def index():
    return render_template('index.html')


# -------------------- FARMER AUTH --------------------
@app.route('/farmer/auth', methods=['GET', 'POST'])
def farmer_auth():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'register':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            land_size = request.form.get('land_size', '').strip()
            land_place = request.form.get('land_place', '').strip()
            aadhaar_number = request.form.get('aadhaar_number', '').strip()

            if Farmer.query.filter_by(email=email).first():
                flash('A farmer account with this email already exists.', 'danger')
                return redirect(url_for('farmer_auth'))

            farmer = Farmer(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                land_size=land_size,
                land_place=land_place,
                aadhaar_number=aadhaar_number
            )
            db.session.add(farmer)
            db.session.commit()

            session['user_id'] = farmer.id
            session['user_role'] = 'farmer'
            session['user_name'] = farmer.name
            flash('Farmer registration complete! Welcome to your portal.', 'success')
            return redirect(url_for('farmer_dashboard'))

        elif action == 'login':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            farmer = Farmer.query.filter_by(email=email).first()

            if farmer and check_password_hash(farmer.password_hash, password):
                session['user_id'] = farmer.id
                session['user_role'] = 'farmer'
                session['user_name'] = farmer.name
                flash(f'Welcome back, {farmer.name}!', 'success')
                return redirect(url_for('farmer_dashboard'))
            else:
                flash('Invalid email or password for Farmer login.', 'danger')

    return render_template('farmer_auth.html')


# -------------------- COMPANY AUTH --------------------
@app.route('/company/auth', methods=['GET', 'POST'])
def company_auth():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'register':
            company_name = request.form.get('company_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            business_type = request.form.get('business_type', '').strip()
            gst_number = request.form.get('gst_number', '').strip()

            if Company.query.filter_by(email=email).first():
                flash('A company account with this email already exists.', 'danger')
                return redirect(url_for('company_auth'))

            company = Company(
                company_name=company_name,
                email=email,
                password_hash=generate_password_hash(password),
                business_type=business_type,
                gst_number=gst_number
            )
            db.session.add(company)
            db.session.commit()

            session['user_id'] = company.id
            session['user_role'] = 'company'
            session['user_name'] = company.company_name
            flash('Company account registered! You can now browse produce and place offers.', 'success')
            return redirect(url_for('company_dashboard'))

        elif action == 'login':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            company = Company.query.filter_by(email=email).first()

            if company and check_password_hash(company.password_hash, password):
                session['user_id'] = company.id
                session['user_role'] = 'company'
                session['user_name'] = company.company_name
                flash(f'Welcome back, {company.company_name}!', 'success')
                return redirect(url_for('company_dashboard'))
            else:
                flash('Invalid email or password for Company login.', 'danger')

    return render_template('company_auth.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# -------------------- FARMER PORTAL --------------------
@app.route('/farmer/dashboard')
@login_required('farmer')
def farmer_dashboard():
    farmer = Farmer.query.get_or_404(session['user_id'])
    my_ads = ProduceAd.query.filter_by(farmer_id=farmer.id).order_by(ProduceAd.created_at.desc()).all()
    incoming_offers = (
        Offer.query.join(ProduceAd)
        .filter(ProduceAd.farmer_id == farmer.id)
        .order_by(Offer.created_at.desc())
        .all()
    )
    return render_template(
        'farmer_dashboard.html',
        farmer=farmer,
        my_ads=my_ads,
        incoming_offers=incoming_offers
    )


@app.route('/farmer/post-ad', methods=['POST'])
@login_required('farmer')
def post_ad():
    crop_name = request.form.get('crop_name', '').strip()
    harvest_date = request.form.get('harvest_date', '').strip()
    try:
        total_quantity = float(request.form.get('total_quantity', 0))
        price_per_kg = float(request.form.get('price_per_kg', 0))
        min_buying_quantity = float(request.form.get('min_buying_quantity', 0))
    except ValueError:
        flash('Please enter valid numeric values for quantity and price.', 'danger')
        return redirect(url_for('farmer_dashboard'))

    if total_quantity <= 0 or price_per_kg <= 0 or min_buying_quantity <= 0:
        flash('Quantities and price must be greater than zero.', 'danger')
        return redirect(url_for('farmer_dashboard'))

    if min_buying_quantity > total_quantity:
        flash('Minimum buying quantity cannot exceed total produce quantity.', 'danger')
        return redirect(url_for('farmer_dashboard'))

    cert_file = request.files.get('certificate')
    if not cert_file or cert_file.filename == '':
        flash('Please upload a quality check certificate file.', 'danger')
        return redirect(url_for('farmer_dashboard'))

    if not allowed_file(cert_file.filename):
        flash('Allowed certificate formats: PDF, PNG, JPG, JPEG.', 'danger')
        return redirect(url_for('farmer_dashboard'))

    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    safe_name = f"farmer_{session['user_id']}_{timestamp}_{secure_filename(cert_file.filename)}"
    cert_file.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))

    new_ad = ProduceAd(
        farmer_id=session['user_id'],
        crop_name=crop_name,
        certificate_filename=safe_name,
        harvest_date=harvest_date,
        total_quantity=total_quantity,
        price_per_kg=price_per_kg,
        min_buying_quantity=min_buying_quantity,
        status='Available'
    )
    db.session.add(new_ad)
    db.session.commit()

    flash(f'Ad for "{crop_name}" ({total_quantity} kg) posted!', 'success')
    return redirect(url_for('farmer_dashboard'))


@app.route('/farmer/offer/<int:offer_id>/respond', methods=['POST'])
@login_required('farmer')
def farmer_respond_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    if offer.ad.farmer_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('farmer_dashboard'))

    if offer.turn != 'farmer' or offer.status not in ('Pending', 'Countered'):
        flash('This offer is not awaiting your response.', 'warning')
        return redirect(url_for('farmer_dashboard'))

    decision = request.form.get('decision')

    if decision == 'accept':
        ok, msg = lock_deal_and_reduce_inventory(offer)
        flash(msg, 'success' if ok else 'danger')

    elif decision == 'hike':
        try:
            hike_amount = float(request.form.get('hike_amount', 0))
        except ValueError:
            flash('Please enter a valid numeric hike amount.', 'danger')
            return redirect(url_for('farmer_dashboard'))

        if hike_amount <= 0:
            flash('Hike amount must be greater than ₹0.', 'danger')
            return redirect(url_for('farmer_dashboard'))

        offer.quote_price = round(offer.quote_price + hike_amount, 2)
        offer.last_hike_amount = round(hike_amount, 2)
        offer.status = 'Countered'
        offer.turn = 'company'
        db.session.commit()
        flash(
            f'Added hike of +₹{hike_amount}/kg. Counter-offer of ₹{offer.quote_price}/kg sent to {offer.company.company_name}.',
            'info'
        )

    elif decision == 'no_negotiation':
        offer.status = 'No Negotiation'
        offer.turn = 'closed'
        db.session.commit()
        flash(f'Offer from {offer.company.company_name} marked as No Negotiation.', 'secondary')

    return redirect(url_for('farmer_dashboard'))


# -------------------- COMPANY PORTAL --------------------
@app.route('/company/dashboard')
@login_required('company')
def company_dashboard():
    company = Company.query.get_or_404(session['user_id'])
    ads = ProduceAd.query.order_by(ProduceAd.status.asc(), ProduceAd.created_at.desc()).all()
    my_offers = (
        Offer.query.filter_by(company_id=company.id)
        .order_by(Offer.created_at.desc())
        .all()
    )
    return render_template(
        'company_dashboard.html',
        company=company,
        ads=ads,
        my_offers=my_offers
    )


@app.route('/company/ad/<int:ad_id>/offer', methods=['POST'])
@login_required('company')
def create_offer(ad_id):
    ad = ProduceAd.query.get_or_404(ad_id)
    if ad.status == 'Sold Out' or ad.total_quantity <= 0:
        flash('This produce listing is already Sold Out.', 'danger')
        return redirect(url_for('company_dashboard'))

    try:
        requested_quantity = float(request.form.get('requested_quantity', 0))
        quote_price = float(request.form.get('quote_price', 0))
    except ValueError:
        flash('Please provide valid numbers for quantity and quote price.', 'danger')
        return redirect(url_for('company_dashboard'))

    if requested_quantity < ad.min_buying_quantity:
        flash(f'Minimum buying quantity for {ad.crop_name} is {ad.min_buying_quantity} kg.', 'warning')
        return redirect(url_for('company_dashboard'))

    if requested_quantity > ad.total_quantity:
        flash(f'Requested quantity exceeds available stock ({ad.total_quantity} kg).', 'warning')
        return redirect(url_for('company_dashboard'))

    if quote_price <= 0:
        flash('Quote price must be greater than ₹0.', 'warning')
        return redirect(url_for('company_dashboard'))

    offer = Offer(
        ad_id=ad.id,
        company_id=session['user_id'],
        requested_quantity=requested_quantity,
        quote_price=round(quote_price, 2),
        turn='farmer',
        status='Pending'
    )
    db.session.add(offer)
    db.session.commit()

    flash(
        f'Offer sent to Farmer {ad.farmer.name} for {requested_quantity} kg of {ad.crop_name} at ₹{quote_price}/kg!',
        'success'
    )
    return redirect(url_for('company_dashboard'))


@app.route('/company/offer/<int:offer_id>/respond', methods=['POST'])
@login_required('company')
def company_respond_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    if offer.company_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('company_dashboard'))

    if offer.turn != 'company' or offer.status != 'Countered':
        flash('This offer is not awaiting a company counter-response.', 'warning')
        return redirect(url_for('company_dashboard'))

    decision = request.form.get('decision')

    if decision == 'counter':
        try:
            new_quote_price = float(request.form.get('new_quote_price', 0))
        except ValueError:
            flash('Please enter a valid counter quote price.', 'danger')
            return redirect(url_for('company_dashboard'))

        if new_quote_price <= 0:
            flash('Counter quote price must be greater than ₹0.', 'danger')
            return redirect(url_for('company_dashboard'))

        offer.quote_price = round(new_quote_price, 2)
        offer.status = 'Pending'
        offer.turn = 'farmer'
        db.session.commit()
        flash(
            f'Revised quote of ₹{offer.quote_price}/kg sent back to Farmer {offer.ad.farmer.name} for approval.',
            'info'
        )

    elif decision == 'accept_hike':
        # Company agrees to farmer's hiked price; send back to farmer to lock OR lock directly
        ok, msg = lock_deal_and_reduce_inventory(offer)
        if ok:
            flash(msg + ' Redirecting to payment gateway.', 'success')
            return redirect(url_for('payment_gateway', offer_id=offer.id))
        else:
            flash(msg, 'danger')

    elif decision == 'decline':
        offer.status = 'No Negotiation'
        offer.turn = 'closed'
        db.session.commit()
        flash('Negotiation closed.', 'secondary')

    return redirect(url_for('company_dashboard'))


# -------------------- DUMMY HTML PAYMENT GATEWAY --------------------
@app.route('/company/payment/<int:offer_id>', methods=['GET', 'POST'])
@login_required('company')
def payment_gateway(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    if offer.company_id != session['user_id']:
        flash('Unauthorized access to payment page.', 'danger')
        return redirect(url_for('company_dashboard'))

    if offer.status not in ('Accepted', 'Paid'):
        flash('Payment gateway only opens once a deal is accepted.', 'warning')
        return redirect(url_for('company_dashboard'))

    if request.method == 'POST':
        offer.status = 'Paid'
        db.session.commit()
        flash('Demo payment completed!', 'success')
        return redirect(url_for('payment_gateway', offer_id=offer.id))

    return render_template('payment_gateway.html', offer=offer)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
