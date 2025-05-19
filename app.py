from flask import Flask, render_template, request, redirect, url_for, session,flash,jsonify
import mysql.connector
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sujata@16", 
        database="online_shopping_system"
    )


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/logout')
def logout():
    if 'user_email' in session:
        session.pop('user_email', None)
        return redirect(url_for('login_user'))  
    elif 'supplier_email' in session:
        session.pop('supplier_email', None)
        return redirect(url_for('login_supplier'))  
    else:
        return redirect(url_for('home')) 


# User Login
@app.route('/login/user', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # user exists
            cursor.execute("SELECT * FROM User WHERE user_email = %s", (email,))
            user = cursor.fetchone()

            if not user:
                return render_template('login_user.html', error="Username does not exist.", show_signup=True)

            # Verify password
            if user['user_password'] != password:
                return render_template('login_user.html', error="Invalid password.", show_signup=False)

            # If credentials are correct, log the user in
            session['user_email'] = user['user_email']
            return redirect(url_for('products'))

        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return render_template('login_user.html', error="An error occurred. Please try again.", show_signup=False)

        finally:
            if connection:
                connection.close()

    return render_template('login_user.html', show_signup=False)


# Supplier Login  
@app.route('/login/supplier', methods=['GET', 'POST'])
def login_supplier():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # supplier exists
            cursor.execute("SELECT * FROM Supplier WHERE supplier_email = %s", (email,))
            supplier = cursor.fetchone()

            if not supplier:
                return render_template('login_supplier.html', error="Username does not exist.", show_signup=True)

            # Verify password
            if supplier['supplier_password'] != password:
                return render_template('login_supplier.html', error="Invalid password.", show_signup=False)

            # If credentials are correct, log the supplier in
            session['supplier_email'] = supplier['supplier_email']
            return redirect(url_for('inventory'))

        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return render_template('login_supplier.html', error="An error occurred. Please try again.", show_signup=False)

        finally:
            if connection:
                connection.close()

    return render_template('login_supplier.html', show_signup=False)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Inventory Route
@app.route('/inventory')
def inventory():
    if 'supplier_email' not in session:
        return redirect(url_for('login_supplier'))

    supplier_email = session['supplier_email']
    connection = None
    inventory_items = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch inventory details including image filename
        cursor.execute("""
            SELECT i.product_name, i.restock_date, 
                   p.price, p.stock, p.image_filename
            FROM Inventory i
            JOIN Product p ON i.product_name = p.product_name
            WHERE i.supplier_email = %s
        """, (supplier_email,))
        inventory_items = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        flash("An error occurred while fetching inventory.", "danger")
    finally:
        if connection:
            connection.close()

    return render_template('inventory.html', inventory_items=inventory_items)

@app.route('/restock-product', methods=['POST'])
def restock_product():
    if 'supplier_email' not in session:
        flash("Please log in to continue.", "warning")
        return redirect(url_for('login_supplier'))

    try:
        supplier_email = session['supplier_email']
        action = request.form.get('action')
        
        # Use get() with default to prevent KeyError
        original_name = request.form.get('original_product_name', '')
        product_name = request.form.get('product_name', original_name).strip()

        if not original_name:
            flash("Missing product identification", "danger")
            return redirect(url_for('inventory'))

        connection = get_db_connection()
        cursor = connection.cursor()

        if action == 'update':
            # Validate required fields
            try:
                stock = int(request.form.get('stock', 0))
                price = float(request.form.get('price', 0))
            except ValueError:
                flash("Invalid stock or price value", "danger")
                return redirect(url_for('inventory'))

            # Update queries
            cursor.execute("""
                UPDATE Inventory
                SET product_name = %s, stock = %s, restock_date = NOW(), price = %s
                WHERE product_name = %s AND supplier_email = %s
            """, (product_name, stock,price, original_name, supplier_email))
            
            cursor.execute("""
                UPDATE Product
                SET product_name = %s, stock = %s, price = %s
                WHERE product_name = %s AND supplier_email = %s
            """, (product_name, stock, price, original_name, supplier_email))

            # Handle image upload
            if 'image' in request.files:
                image = request.files['image']
                if image.filename != '':
                    if allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        cursor.execute("""
                            UPDATE Product
                            SET image_filename = %s
                            WHERE product_name = %s AND supplier_email = %s
                        """, (filename, product_name, supplier_email))

            connection.commit()
            flash("Product updated successfully!", "success")

        elif action == 'delete_full':
            # 1. First delete from order_product to avoid foreign key constraints
            cursor.execute("""
                DELETE FROM order_product 
                WHERE product_name = %s
            """, (original_name,))
            
            # 2. Delete from Inventory table
            cursor.execute("""
                DELETE FROM Inventory
                WHERE product_name = %s AND supplier_email = %s
            """, (original_name, supplier_email))
            
            # 3. Delete from Product table
            cursor.execute("""
                DELETE FROM Product
                WHERE product_name = %s AND supplier_email = %s
            """, (original_name, supplier_email))
            
            connection.commit()
            flash(f"Product '{original_name}' has been completely deleted", "success")

    except mysql.connector.Error as err:
        if 'connection' in locals():
            connection.rollback()
        flash(f"Database error: {err}", "danger")
        print(f"Database error: {err}")
    except Exception as e:
        if 'connection' in locals():
            connection.rollback()
        flash(f"Error: {str(e)}", "danger")
        print(f"Error: {str(e)}")
    finally:
        if 'connection' in locals():
            connection.close()

    return redirect(url_for('inventory'))

# Add Product from Supplier
@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if 'supplier_email' not in session:
        return redirect(url_for('login_supplier'))

    supplier_email = session['supplier_email']

    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        price = request.form.get('price', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        stock = request.form.get('stock', '').strip()
        restock_date = request.form.get('restock_date', '').strip()
        image = request.files.get('product_image')

        # Debugging: Print received values
        print(f"Received: {product_name}, {price}, {stock}, {image.filename if image else 'No Image'}")

        # Validate inputs
        if not product_name or not price or not stock :
            print("⚠️ Missing required fields.")
            flash("Please fill all required fields correctly.")
            return redirect(url_for('add_product'))

        if not price.isdigit() or not stock.isdigit() :
            flash("Price, stock, and restock quantity must be numeric.")
            return redirect(url_for('add_product'))

        price = float(price)
        stock = int(stock)

        # Handle image upload (Make optional)
        image_filename = "default.jpg"  # Default image if none provided
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)

        connection = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            print("🔹 Connected to database successfully.")
            # Insert into Product table
            cursor.execute("""
                INSERT INTO Product (product_name, supplier_email, price, description, category, stock, image_filename)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (product_name, supplier_email, price, description, category, stock, image_filename))

            # Insert into Inventory table
            cursor.execute("""
                INSERT INTO Inventory (product_name, restock_date, price, description, category, stock, supplier_email, product_image)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (product_name, restock_date, price, description, category, stock, supplier_email, image_filename))

            # Commit to database
            connection.commit()
            print(" Product successfully added to database.")

        except mysql.connector.Error as err:
            connection.rollback()  # Rollback if error occurs
            print(f" Database error: {err}")
            return f"Error adding product: {err}"

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return redirect(url_for('inventory'))

    return render_template('add_product.html')

# Signup as User
@app.route('/signup/user', methods=['GET', 'POST'])
def signup_user():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        if not email or not password or not name or not phone or not address:
            return render_template('signup_user.html', error="All fields are required.")

        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = """
            INSERT INTO User (user_email, user_password, user_name, user_phone, user_address)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (email, password, name, phone, address))
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            if err.errno == 1062:  # Duplicate entry
                return render_template('signup_user.html', error="Email already exists.")
            else:
                return render_template('signup_user.html', error="An error occurred. Please try again.")
        finally:
            if connection:
                connection.close()

        return render_template('signup_success.html', role="User")
    return render_template('signup_user.html')


# Signup as Supplier
@app.route('/signup/supplier', methods=['GET', 'POST'])
def signup_supplier():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        if not email or not password or not name or not phone or not address:
            return render_template('signup_supplier.html', error="All fields are required.")

        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = """
            INSERT INTO Supplier (supplier_email, supplier_password, supplier_name, supplier_phone, supplier_address)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (email, password, name, phone, address))
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            if err.errno == 1062:  # Duplicate entry
                return render_template('signup_supplier.html', error="Email already exists.")
            else:
                return render_template('signup_supplier.html', error="An error occurred. Please try again.")
        finally:
            if connection:
                connection.close()

        return render_template('signup_success.html', role="Supplier")
    return render_template('signup_supplier.html')

# Products page
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'user_email' not in session:
        return redirect(url_for('login_user'))

    # Get filters from query parameters
    selected_category = request.args.get('category')
    search_query = request.args.get('search', '').strip()
    sort_order = request.args.get('sort', '')  # New: Sorting

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch available categories
        cursor.execute("SELECT DISTINCT category FROM Inventory")
        categories = [row['category'] for row in cursor.fetchall()]

        # Base query
        query = """
            SELECT p.product_name, p.price, p.category, p.description, p.product_image, p.stock, s.supplier_name,
                   IFNULL(cp.quantity, 0) AS quantity
            FROM Inventory p
            LEFT JOIN Cart_Product cp ON p.product_name = cp.product_name AND cp.user_email = %s
            JOIN Supplier s ON p.supplier_email = s.supplier_email
            WHERE 1=1
        """
        params = [session['user_email']]

        # Filter by category
        if selected_category and selected_category != "":
            query += " AND p.category = %s"
            params.append(selected_category)

        # Filter by search
        if search_query:
            query += " AND (p.product_name LIKE %s OR p.description LIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        # Sorting
        if sort_order == 'price_asc':
            query += " ORDER BY p.price ASC"
        elif sort_order == 'price_desc':
            query += " ORDER BY p.price DESC"

        # Execute query
        cursor.execute(query, params)
        products = cursor.fetchall()

        # Update image paths
        for product in products:
            product['product_image'] = f"/static/uploads/{product['product_image']}" if product['product_image'] else "/static/default.jpg"

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return render_template('products.html', error="An error occurred while fetching products.")
    finally:
        if connection:
            connection.close()

    return render_template(
        'products.html',
        products=products,
        categories=categories,
        selected_category=selected_category,
        search_query=search_query,
        sort_order=sort_order  # Pass sort to template for selected value
    )

# Cart functionality
@app.route('/cart', methods=['POST'])
def cart():
    if 'user_email' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Please login first'}), 401
        return redirect(url_for('login_user'))  

    # Get form data
    user_email = session['user_email']
    product_name = request.form['product_name']
    action = request.form['action']
    restock_quantity = int(request.form.get('restock_quantity', 0))
    
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Fetch product price and stock
        cursor.execute("SELECT price, stock FROM Inventory WHERE product_name = %s", (product_name,))
        product = cursor.fetchone()
        if not product:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Product not found'}), 404
            return "Error: Product not found"
        
        unit_price, stock = product

        # Check if the product is in the cart
        cursor.execute("SELECT quantity FROM Cart_Product WHERE product_name = %s AND user_email = %s", 
                      (product_name, user_email))
        cart_item = cursor.fetchone()

        # Check if the user has a cart
        cursor.execute("SELECT * FROM Cart WHERE user_email = %s", (user_email,))
        user_cart = cursor.fetchone()

        if not user_cart:
            # Create a cart if it doesn't exist
            cursor.execute("INSERT INTO Cart (user_email, total_price) VALUES (%s, %s)", (user_email, 0))

        if action == 'add':
            if cart_item:
                # Check stock before adding
                if cart_item[0] >= stock:
                    if is_ajax:
                        return jsonify({
                            'success': False,
                            'message': 'Maximum quantity reached',
                            'cart_count': get_cart_count(user_email)
                        })
                    return "Maximum quantity reached"
                
                new_quantity = cart_item[0] + 1
                cursor.execute(
                    "UPDATE Cart_Product SET quantity = %s, price = %s WHERE product_name = %s AND user_email = %s",
                    (new_quantity, new_quantity * unit_price, product_name, user_email)
                )
            else:
                # Add product to Cart_Product
                cursor.execute(
                    "INSERT INTO Cart_Product (user_email, product_name, quantity, price) VALUES (%s, %s, %s, %s)",
                    (user_email, product_name, 1, unit_price)
                )

            # Update total price in Cart
            cursor.execute("UPDATE Cart SET total_price = total_price + %s WHERE user_email = %s", 
                          (unit_price, user_email))
            message = f"{product_name} added to cart"

        elif action == 'increase':
            # Check stock before increasing
            if cart_item[0] >= stock:
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'message': 'Maximum quantity reached',
                        'cart_count': get_cart_count(user_email)
                    })
                return "Maximum quantity reached"
            
            # Increment quantity
            new_quantity = cart_item[0] + 1
            cursor.execute(
                "UPDATE Cart_Product SET quantity = %s, price = %s WHERE product_name = %s AND user_email = %s",
                (new_quantity, new_quantity * unit_price, product_name, user_email)
            )
            # Update total price in Cart
            cursor.execute("UPDATE Cart SET total_price = total_price + %s WHERE user_email = %s", 
                          (unit_price, user_email))
            message = f"{product_name} quantity increased"

        elif action == 'decrease':
            # Decrement quantity
            new_quantity = cart_item[0] - 1
            if new_quantity > 0:
                cursor.execute(
                    "UPDATE Cart_Product SET quantity = %s, price = %s WHERE product_name = %s AND user_email = %s",
                    (new_quantity, new_quantity * unit_price, product_name, user_email)
                )
                # Update total price in Cart
                cursor.execute("UPDATE Cart SET total_price = total_price - %s WHERE user_email = %s", 
                              (unit_price, user_email))
            else:
                # Remove product if quantity is 0
                cursor.execute("DELETE FROM Cart_Product WHERE product_name = %s AND user_email = %s", 
                              (product_name, user_email))
                # Update total price in Cart
                cursor.execute("UPDATE Cart SET total_price = total_price - %s WHERE user_email = %s", 
                              (unit_price, user_email))
            message = f"{product_name} quantity decreased"

        connection.commit()

        # Get updated cart count
        cart_count = get_cart_count(user_email)

        if is_ajax:
            return jsonify({
                'success': True,
                'message': message,
                'cart_count': cart_count
            })

        # For non-AJAX requests (fallback)
        current_category = request.form.get('current_category', '')
        current_search = request.form.get('current_search', '')
        current_sort = request.form.get('current_sort', '')
        
        return redirect(url_for('products',
            category=current_category,
            search=current_search,
            sort=current_sort
        ))

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        if is_ajax:
            return jsonify({
                'success': False,
                'message': 'Database error occurred',
                'cart_count': get_cart_count(user_email) if 'user_email' in session else 0
            }), 500
        return "Error"
    finally:
        if connection:
            connection.close()

def get_cart_count(user_email):
    """Helper function to get cart count for a user"""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT SUM(quantity) FROM Cart_Product WHERE user_email = %s", (user_email,))
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0
    except mysql.connector.Error as err:
        print(f"Error getting cart count: {err}")
        return 0
    finally:
        if connection:
            connection.close()



@app.context_processor
def inject_cart_count():
    if 'user_email' in session:
        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT SUM(quantity) FROM Cart_Product WHERE user_email = %s", (session['user_email'],))
            cart_count = cursor.fetchone()[0] or 0
        finally:
            if connection:
                connection.close()
        return {'cart_count': cart_count}
    return {'cart_count': 0}



@app.route('/view-cart', methods=['GET', 'POST'])
def view_cart():
    if 'user_email' not in session:
        return redirect(url_for('login_user'))  

    user_email = session['user_email']
    connection = None
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Handle POST requests for cart updates
        if request.method == 'POST':
            # Process quantity updates
            for key, value in request.form.items():
                if key.startswith('quantity_'):
                    product_name = key.split('_')[1]
                    new_quantity = int(value)
                    
                    # Update quantity in database
                    cursor.execute("""
                        UPDATE Cart_Product 
                        SET quantity = %s 
                        WHERE user_email = %s AND product_name = %s
                    """, (new_quantity, user_email, product_name))
            
            # Process item removals
            remove_items = request.form.getlist('remove_item')
            for product_name in remove_items:
                cursor.execute("""
                    DELETE FROM Cart_Product 
                    WHERE user_email = %s AND product_name = %s
                """, (user_email, product_name))
            
            connection.commit()

        # Fetch current cart contents
        cursor.execute("""
            SELECT product_name, quantity, price, (quantity * price) as item_total
            FROM Cart_Product
            WHERE user_email = %s
        """, (user_email,))
        cart_items = cursor.fetchall()

        # Calculate total amount
        total_amount = sum(item['item_total'] for item in cart_items) if cart_items else 0
        

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return "Error processing cart", 500
    finally:
        if connection:
            connection.close()

    return render_template('cart.html', 
                         cart_items=cart_items, 
                         total_amount=total_amount,
                        )


@app.route('/place-order', methods=['POST'])
def place_order():
    if 'user_email' not in session:
        return redirect(url_for('login_user'))  

    user_email = session['user_email']
    shipping_method = request.form.get('shipping_method')  

    if not shipping_method:
        return "Error: Please select a shipping method!"

    shipping_details = {
        "Regular Shipping": {"cost": 0, "delivery_time": "6 to 7 working days"},
        "Express Shipping": {"cost": 1000, "delivery_time": "1 to 2 working days"}
    }

    if shipping_method not in shipping_details:
        return "Error: Invalid shipping method selected!"

    shipping_cost = shipping_details[shipping_method]["cost"]
    delivery_time = shipping_details[shipping_method]["delivery_time"]

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Fetch user address
        cursor.execute("SELECT user_address FROM User WHERE user_email = %s", (user_email,))
        user_address = cursor.fetchone()

        if not user_address:
            return "Error: User address not found!"

        # Fetch cart products
        cursor.execute("SELECT product_name, quantity, price FROM Cart_Product WHERE user_email = %s", (user_email,))
        cart_products = cursor.fetchall()

        if not cart_products:
            return "Error: Cart is empty!"

        # Calculate total amount
        total_amount = sum([item[2] for item in cart_products]) + shipping_cost

        # Create order
        cursor.execute(
            "INSERT INTO `order` (user_email, total_amount, shipping_address, order_date) VALUES (%s, %s, %s, NOW())",
            (user_email, total_amount, user_address[0])
        )
        order_id = cursor.lastrowid

        # Add products to Order_Product and update inventory
        for product_name, quantity, price in cart_products:
            cursor.execute(
                "INSERT INTO Order_Product (order_id, product_name, quantity, price_at_order_time) VALUES (%s, %s, %s, %s)",
                (order_id, product_name, quantity, price)
            )

        # Clear user's cart
        # cursor.execute("DELETE FROM Cart_Product WHERE user_email = %s", (user_email,))
        # cursor.execute("DELETE FROM Cart WHERE user_email = %s", (user_email,))

        connection.commit()

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return f"Error placing order: {err}"
    finally:
        if connection:
            connection.close()

    return redirect(url_for('payment', order_id=order_id))




# Payment page
@app.route('/payment/<int:order_id>', methods=['GET'])
def payment(order_id):
    return render_template('payment.html', order_id=order_id)


# Process payment
@app.route('/process-payment', methods=['POST'])
def process_payment():
    order_id = request.form['order_id']
    payment_method = request.form['payment_method']
    user_email = session['user_email']
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Step 1: Insert payment details into the payment table
        cursor.execute("""
            INSERT INTO payment (order_id, payment_date, payment_method, payment_status)
            VALUES (%s, NOW(), %s, %s)
        """, (order_id, payment_method, "Completed"))

        # Step 2: Get ordered products and quantities from the order table
        cursor.execute("""
            SELECT product_name, quantity FROM order_product WHERE order_id = %s
        """, (order_id,))
        ordered_items = cursor.fetchall()

        if not ordered_items:
            connection.rollback()
            return "Error: No items found for this order."

        # Step 3: Update Inventory and Product stock
        for product_name, quantity in ordered_items:
            print(f"🔹 Updating inventory for {product_name}, reducing by {quantity}")

            # Update Inventory Table
            cursor.execute("""
                UPDATE Inventory SET stock = stock - %s
                WHERE product_name = %s AND stock >= %s
            """, (quantity, product_name, quantity))

            if cursor.rowcount == 0:
                connection.rollback()
                return f"Error: Not enough stock for {product_name}."

            # Optional: If you track stock in Product Table, update it too
            cursor.execute("""
                UPDATE Product SET stock = stock - %s
                WHERE product_name = %s AND stock >= %s
            """, (quantity, product_name, quantity))
             # Clear user's cart
            cursor.execute("DELETE FROM Cart_Product WHERE user_email = %s", (user_email,))
            cursor.execute("DELETE FROM Cart WHERE user_email = %s", (user_email,))
            connection.commit()
        print("✅ Payment processed and inventory updated.")

    except mysql.connector.Error as err:
        connection.rollback()
        print(f"❌ Database error: {err}")
        return f"Error processing payment: {err}"

    finally:
        if connection:
            connection.close()

    return render_template('order_success.html', order_id=order_id)

@app.route('/past_orders')
def past_orders():
    if 'user_email' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    user_email = session['user_email']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch past orders of the logged-in user
    cursor.execute("""
            SELECT o.order_id, o.order_date, o.total_amount, o.shipping_address
            FROM `order` o
            JOIN payment p ON o.order_id = p.order_id
            WHERE o.user_email = %s 
            ORDER BY o.order_date DESC
        """, (user_email,))

    orders = cursor.fetchall()
    connection.close()

    return render_template('orders.html', orders=orders)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

