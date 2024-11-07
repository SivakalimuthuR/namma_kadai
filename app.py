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

    # Relationship with Purchase, backref creates 'item' in the Purchase model
    purchases = relationship('Purchase', backref='item', cascade='all, delete-orphan')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, ForeignKey('item.id', ondelete='SET NULL'), nullable=True)
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    # No need to define the relationship to Item again, as 'item' will be created automatically by the backref
    # Remove the redundant `item` relationship

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
    # Get the current page number from the request arguments, defaulting to 1 if not provided
    page = request.args.get('page', 1, type=int)
    
    # Define the number of items per page
    items_per_page = 10
    
    # Query the items with pagination
    items_paginated = Item.query.paginate(page=page, per_page=items_per_page, error_out=False)
    
    # Pass the pagination object and the company info to the template
    return render_template(
        'home.html', 
        company=Company.query.first(), 
        items=items_paginated.items,  # Only the items for the current page
        items_pagination=items_paginated  # The full pagination object
    )

# ***************************************************************************************************************************************

@app.route('/items', methods=['GET', 'POST'])
def manage_items():
    if request.method == 'POST':
        # Get the data from the form
        name = request.form.get('name')
        price = request.form.get('price')

        # Validation to make sure both fields are filled out
        if not name or not price:
            flash("Both name and price are required!", "danger")
            return redirect(url_for('manage_items'))  # Redirect back to the items page

        # Check if the item already exists in the database by name
        existing_item = Item.query.filter_by(name=name).first()
        
        if existing_item:
            flash("Item with this name already exists!", "danger")  # Flash error message if the item exists
            return redirect(url_for('manage_items'))  # Redirect back to the items page

        try:
            # Add the new item to the database (since no duplicate exists)
            new_item = Item(name=name, price=float(price))
            db.session.add(new_item)
            db.session.commit()  # Commit the transaction to save the item
            flash('Item added successfully!', 'success')  # Flash a success message
        except ValueError:
            flash("Please enter a valid price!", "danger")  # If price is not a valid number
            return redirect(url_for('manage_items'))

        return redirect(url_for('manage_items'))  # After success, refresh the page

    # GET request, render the template with the existing items
    return render_template('items.html', items=Item.query.all())



# ***************************************************************************************************************************************

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    # Get the item by ID, or 404 if it doesn't exist
    item = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        # Get the updated values from the form
        item.name = request.form['name']
        item.price = float(request.form['price'])  # Update price as a float

        # Commit the changes to the database
        db.session.commit()

        # Flash a success message
        flash('Item updated successfully!', 'success')
        return redirect(url_for('manage_items'))  # Redirect to the items list

    # GET request, render the edit form with the current item data
    return render_template('edit_item.html', item=item)

# ***************************************************************************************************************************************
@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    try:
        # Delete the item and its related purchases will be automatically deleted due to cascade
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
    # Get all items and the company data (assuming only one company exists)
    items = Item.query.all()
    company = Company.query.first()

    if request.method == 'POST':
        # Get the data from the form
        item_id = request.form['item_id']
        qty = int(request.form['qty'])
        rate = float(request.form['rate'])
        amount = rate * qty

        # Check if the company has enough cash balance for the purchase
        if company.cash_balance >= amount:
            # Find the item by its ID
            item = Item.query.get(item_id)

            if item:
                # Update the company cash balance and item stock
                company.cash_balance -= amount
                item.qty += qty

                # Create a new Purchase record and commit it to the database
                db.session.add(Purchase(item_id=item_id, qty=qty, rate=rate, amount=amount))
                db.session.commit()

                # Flash success message with a 'success' category
                flash('Purchase added successfully!', 'success')
            else:
                # Flash error message with a 'danger' category if the item is not found
                flash('Item not found!', 'danger')
        else:
            # Flash error message with a 'danger' category if there is insufficient balance
            flash('Insufficient balance to make this purchase!', 'danger')

        return redirect(url_for('manage_purchase'))  # Redirect back to the purchase page

    # Render the template with the list of items and company data (including balance)
    return render_template('purchase.html', items=items, company=company)


# ***************************************************************************************************************************************



@app.route('/sales', methods=['GET', 'POST'])
def manage_sales():
    items = Item.query.all()  # Fetching all items
    company = Company.query.first()  # Fetch the company to show the balance
    ist = pytz.timezone('Asia/Kolkata')

    # Serialize the items into dictionaries that can be passed to the template
    items_data = [{
        'id': item.id,
        'name': item.name,
        'qty': item.qty
    } for item in items]

    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = int(request.form['qty'])
        rate = float(request.form['rate'])
        item = Item.query.get(item_id)
        if item and item.qty >= qty:
            amount = rate * qty
            company.cash_balance += amount
            item.qty -= qty
            sale = Sale(item_id=item_id, qty=qty, rate=rate, amount=amount, timestamp=datetime.now(ist))
            db.session.add(sale)
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
    # Set timezone for India
    ist = pytz.timezone('Asia/Kolkata')
    
    # Pagination settings
    per_page = 10  # Records per page (can be adjusted)
    
    # Get the current page for purchases and sales from query parameters
    purchases_page = request.args.get('purchases_page', 1, type=int)
    sales_page = request.args.get('sales_page', 1, type=int)
    
    # Paginate purchases and sales with separate page numbers
    purchases_paginated = Purchase.query.order_by(Purchase.timestamp.desc()).paginate(page=purchases_page, per_page=per_page, error_out=False)
    sales_paginated = Sale.query.order_by(Sale.timestamp.desc()).paginate(page=sales_page, per_page=per_page, error_out=False)
    
    # Format the purchases with details for the template
    purchases_with_details = [{
        'item_name': purchase.item.name,
        'qty': purchase.qty,
        'rate': purchase.rate,
        'amount': purchase.amount,
        'date': purchase.timestamp.astimezone(ist).strftime('%Y-%m-%d'),
        'time': purchase.timestamp.astimezone(ist).strftime('%I:%M %p')
    } for purchase in purchases_paginated.items]
    
    # Format the sales with details for the template
    sales_with_details = [{
        'item_name': sale.item.name,
        'qty': sale.qty,
        'rate': sale.rate,
        'amount': sale.amount,
        'date': sale.timestamp.astimezone(ist).strftime('%Y-%m-%d'),
        'time': sale.timestamp.astimezone(ist).strftime('%I:%M %p')
    } for sale in sales_paginated.items]
    
    # Return the template with paginated data
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
