from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import pytz


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

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    item = db.relationship('Item', backref='purchases')

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    item = db.relationship('Item', backref='sales')


@app.before_first_request
def create_tables():
    db.create_all()
    if not Company.query.first():
        company = Company(cash_balance=1000)
        db.session.add(company)
        db.session.commit()



@app.route('/')
def home():
    company = Company.query.first() 
    return render_template('home.html', company=company)



# Routes for Items
@app.route('/items', methods=['GET', 'POST'])
def manage_items():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        new_item = Item(name=name, price=float(price))
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!')
        return redirect(url_for('manage_items'))

    items = Item.query.all()
    return render_template('items.html', items=items)

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get(item_id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.price = request.form['price']
        db.session.commit()
        flash('Item updated successfully!')
        return redirect(url_for('manage_items'))
    
    return render_template('edit_item.html', item=item)

# Routes for Purchases
@app.route('/purchase', methods=['GET', 'POST'])
def manage_purchase():
    items = Item.query.all()
    purchases = Purchase.query.all()
    company = Company.query.first()

    
    ist = pytz.timezone('Asia/Kolkata')

    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = request.form['qty']
        rate = request.form['rate']
        amount = float(rate) * int(qty)

        company.cash_balance -= amount  
        item = Item.query.get(item_id)
        item.qty += int(qty)  
        db.session.commit()

        new_purchase = Purchase(item_id=item_id, qty=qty, rate=rate, amount=amount)
        db.session.add(new_purchase)
        db.session.commit()
        flash('Purchase added successfully!')
        return redirect(url_for('manage_purchase'))
    
    
    purchases_with_details = []
    for purchase in purchases:
        item = Item.query.get(purchase.item_id)
        
        ist_time = purchase.timestamp.astimezone(ist)
        purchases_with_details.append({
            'item_name': item.name,  
            'qty': purchase.qty,
            'rate': purchase.rate,
            'amount': purchase.amount,
            'date': ist_time.strftime('%Y-%m-%d'),
            'time': ist_time.strftime('%I:%M %p'),  
        })

    return render_template('purchase.html', items=items, purchases=purchases_with_details)

# Routes for Sales
@app.route('/sales', methods=['GET', 'POST'])
def manage_sales():
    items = Item.query.all()
    company = Company.query.first()

    
    ist = pytz.timezone('Asia/Kolkata')

    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = int(request.form['qty'])
        rate = float(request.form['rate'])
        amount = rate * qty

        
        company.cash_balance += amount
        item = Item.query.get(item_id)
        item.qty -= qty

        
        sale = Sale(
            item_id=item_id,
            qty=qty,
            rate=rate,
            amount=amount,
            timestamp=datetime.now(ist)  
        )
        db.session.add(sale)
        db.session.commit()
        flash('Sale recorded successfully!')
        return redirect(url_for('manage_sales'))

    
    sales = Sale.query.all()
    sales_with_details = []
    for sale in sales:
        item = Item.query.get(sale.item_id)
        ist_time = sale.timestamp.astimezone(ist)
        sales_with_details.append({
            'item_name': item.name,
            'item_id': sale.item_id,
            'qty': sale.qty,
            'rate': sale.rate,
            'amount': sale.amount,
            'date': ist_time.strftime('%Y-%m-%d'),
            'time': ist_time.strftime('%I:%M:%S %p'),
        })

    return render_template('sales.html', items=items, sales=sales_with_details)



# Route to view current cash balance
@app.route('/balance')
def show_balance():
    company = Company.query.first()
    return render_template('balance.html', cash_balance=company.cash_balance)

# Route to show item quantities
@app.route('/report')
def report():
    items = Item.query.all()
    company = Company.query.first()
    return render_template('report.html', items=items, cash_balance=company.cash_balance)

if __name__ == '__main__':
    app.run(debug=True)


























# from flask import Flask, render_template, request, redirect, url_for, flash
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime
# import os

# app = Flask(__name__)
# db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'namma_kadai.db')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
# app.config['SECRET_KEY'] = 'bc9b2d89c5fbfd81232bac5cde78897f'
# db = SQLAlchemy(app)


# class Company(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False, default='Namma Kadai')
#     cash_balance = db.Column(db.Float, default=1000.0)

# class Item(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     price = db.Column(db.Float, nullable=False)
#     qty = db.Column(db.Integer, default=0)

# class Purchase(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow)
#     item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
#     qty = db.Column(db.Integer, nullable=False)
#     rate = db.Column(db.Float, nullable=False)
#     amount = db.Column(db.Float, nullable=False)

# class Sale(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow)
#     item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
#     qty = db.Column(db.Integer, nullable=False)
#     rate = db.Column(db.Float, nullable=False)
#     amount = db.Column(db.Float, nullable=False)

# @app.before_first_request
# def create_tables():
#     print("creating tables...............")
#     db.create_all()
#     if not Company.query.first():
#         company = Company(cash_balance=1000)
#         db.session.add(company)
#         db.session.commit()
#         print("company entry created..........")
#     else:
#         print("company entry already exists....")

# # Routes go here

# if __name__ == '__main__':
#     app.run(debug=True)
