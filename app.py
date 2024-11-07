from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import pytz
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

app = Flask(__name__)
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'namma_kadai.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SECRET_KEY'] = 'bc9b2d89c5fbfd81232bac5cde78897f'
db = SQLAlchemy(app)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='Namma Kadai')
    cash_balance = db.Column(db.Float, default=1000.0)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    qty = db.Column(db.Integer, default=0)
    purchases = relationship('Purchase', backref='item', cascade='all, delete-orphan')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, ForeignKey('item.id', ondelete='SET NULL'), nullable=True)
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    item = db.relationship('Item', backref='sales')

# ***************************************************************************************************************************************
@app.before_first_request
def create_tables():
    db.create_all()
    if not Company.query.first():
        db.session.add(Company(cash_balance=1000))
        db.session.commit()

# ***************************************************************************************************************************************
@app.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    items_paginated = Item.query.paginate(page=page, per_page=10, error_out=False)
    return render_template(
        'home.html', 
        company=Company.query.first(), 
        items=items_paginated.items,  
        items_pagination=items_paginated
    )

# ***************************************************************************************************************************************
@app.route('/items', methods=['GET', 'POST'])
def manage_items():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')

        if not name or not price:
            flash("Both name and price are required!", "danger")
            return redirect(url_for('manage_items'))

        if Item.query.filter_by(name=name).first():
            flash("Item with this name already exists!", "danger")
            return redirect(url_for('manage_items'))

        try:
            new_item = Item(name=name, price=float(price))
            db.session.add(new_item)
            db.session.commit()
            flash('Item added successfully!', 'success')
        except ValueError:
            flash("Please enter a valid price!", "danger")

        return redirect(url_for('manage_items'))

    return render_template('items.html', items=Item.query.all())

# ***************************************************************************************************************************************
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        item.name = request.form['name']
        item.price = float(request.form['price'])
        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('manage_items'))

    return render_template('edit_item.html', item=item)

# ***************************************************************************************************************************************
@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    try:
        db.session.delete(item)
        db.session.commit()
        flash('Item and related purchases deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'danger')
    
    return redirect(url_for('manage_items'))

# ***************************************************************************************************************************************
@app.route('/purchase', methods=['GET', 'POST'])
def manage_purchase():
    items = Item.query.all()
    company = Company.query.first()

    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = int(request.form['qty'])
        rate = float(request.form['rate'])
        amount = rate * qty

        if company.cash_balance >= amount:
            item = Item.query.get(item_id)
            if item:
                company.cash_balance -= amount
                item.qty += qty
                db.session.add(Purchase(item_id=item_id, qty=qty, rate=rate, amount=amount))
                db.session.commit()
                flash('Purchase added successfully!', 'success')
            else:
                flash('Item not found!', 'danger')
        else:
            flash('Insufficient balance to make this purchase!', 'danger')

        return redirect(url_for('manage_purchase'))

    return render_template('purchase.html', items=items, company=company)

# ***************************************************************************************************************************************
@app.route('/sales', methods=['GET', 'POST'])
def manage_sales():
    items = Item.query.all()
    company = Company.query.first()

    items_data = [{'id': item.id, 'name': item.name, 'qty': item.qty} for item in items]

    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = int(request.form['qty'])
        rate = float(request.form['rate'])
        item = Item.query.get(item_id)
        if item and item.qty >= qty:
            amount = rate * qty
            company.cash_balance += amount
            item.qty -= qty
            db.session.add(Sale(item_id=item_id, qty=qty, rate=rate, amount=amount))
            db.session.commit()
            flash(f"Sale for {item.name} recorded successfully! Amount: ₹{amount:.2f}", 'success')
        else:
            flash(f"Not enough stock for {item.name}. Available stock: {item.qty}.", 'danger')

        return redirect(url_for('manage_sales'))

    return render_template('sales.html', items=items_data, company=company)

# ***************************************************************************************************************************************
@app.route('/balance')
def show_balance():
    return render_template('balance.html', cash_balance=Company.query.first().cash_balance)

# ***************************************************************************************************************************************
@app.route('/report')
def report():
    ist = pytz.timezone('Asia/Kolkata')
    per_page = 10

    purchases_page = request.args.get('purchases_page', 1, type=int)
    sales_page = request.args.get('sales_page', 1, type=int)

    purchases_paginated = Purchase.query.order_by(Purchase.timestamp.desc()).paginate(page=purchases_page, per_page=per_page, error_out=False)
    sales_paginated = Sale.query.order_by(Sale.timestamp.desc()).paginate(page=sales_page, per_page=per_page, error_out=False)

    purchases_with_details = [{
        'item_name': purchase.item.name,
        'qty': purchase.qty,
        'rate': purchase.rate,
        'amount': purchase.amount,
        'date': purchase.timestamp.astimezone(ist).strftime('%Y-%m-%d'),
        'time': purchase.timestamp.astimezone(ist).strftime('%I:%M %p')
    } for purchase in purchases_paginated.items]

    sales_with_details = [{
        'item_name': sale.item.name,
        'qty': sale.qty,
        'rate': sale.rate,
        'amount': sale.amount,
        'date': sale.timestamp.astimezone(ist).strftime('%Y-%m-%d'),
        'time': sale.timestamp.astimezone(ist).strftime('%I:%M %p')
    } for sale in sales_paginated.items]

    return render_template('report.html', 
                           purchases=purchases_with_details, 
                           sales=sales_with_details,
                           purchases_pagination=purchases_paginated, 
                           sales_pagination=sales_paginated)

# ***************************************************************************************************************************************
@app.template_filter('non_negative')
def non_negative(value):
    return max(0, value)

if __name__ == '__main__':
    app.run(debug=True)
