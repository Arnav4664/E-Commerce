import mysql.connector

# Establish connection to MySQL server
def create_database():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=""  
    )
    cursor = connection.cursor()

    # Create the database
    cursor.execute("CREATE DATABASE IF NOT EXISTS online_shopping_system")
    cursor.close()
    connection.close()

# Establish connection to the new database
def setup_tables():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="online_shopping_system"
    )
    cursor = connection.cursor()

    # Create tables in the correct order
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS User (
    user_email VARCHAR(255) PRIMARY KEY,
    user_name VARCHAR(100),
    user_phone VARCHAR(15),
    user_password VARCHAR(255),  
    user_address TEXT
)
""")


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Supplier (
        supplier_email VARCHAR(255) PRIMARY KEY,
        supplier_name VARCHAR(255),
        supplier_phone VARCHAR(15),
        supplier_password VARCHAR(255),
        supplier_address TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Product (
        product_name VARCHAR(255) PRIMARY KEY,
        supplier_email VARCHAR(255),
        price DECIMAL(10, 2),
        description TEXT,
        category VARCHAR(50),
        stock INT,
        image_filename VARCHAR(100),
        FOREIGN KEY (supplier_email) REFERENCES Supplier(supplier_email)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Inventory (
        product_name VARCHAR(100),
        restock_date DATE,
        price DECIMAL(10,2),
        description TEXT,
        category VARCHAR(50),
        stock INT,
        supplier_email VARCHAR(100),
        product_image VARCHAR(100),
        FOREIGN KEY (product_name) REFERENCES product(product_name)
);

                   """ 
    )
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Cart (
        user_email VARCHAR(255),
        total_price DECIMAL(10, 2),
        PRIMARY KEY (user_email),
        FOREIGN KEY (user_email) REFERENCES User(user_email)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Cart_Product (
        user_email VARCHAR(255),
        product_name VARCHAR(255),
        quantity INT,
        price DECIMAL(10, 2),
        PRIMARY KEY (user_email, product_name),
        FOREIGN KEY (user_email) REFERENCES User(user_email),
        FOREIGN KEY (product_name) REFERENCES Product(product_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `Order` (
        order_id INT AUTO_INCREMENT PRIMARY KEY,
        user_email VARCHAR(255),
        order_date DATETIME,
        total_amount DECIMAL(10, 2),
        shipping_address TEXT,
        FOREIGN KEY (user_email) REFERENCES User(user_email)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Order_Product (
        order_id INT,
        product_name VARCHAR(255),
        quantity INT,
        price_at_order_time DECIMAL(10, 2),
        PRIMARY KEY (order_id, product_name),
        FOREIGN KEY (order_id) REFERENCES `Order`(order_id),
        FOREIGN KEY (product_name) REFERENCES Product(product_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Payment (
        payment_id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT,
        payment_date DATETIME,
        payment_method VARCHAR(50),
        payment_status VARCHAR(50),
        FOREIGN KEY (order_id) REFERENCES `Order`(order_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Shipping_Method (
        shipping_method_name VARCHAR(100) PRIMARY KEY,
        shipping_cost DECIMAL(10, 2),
        delivery_time VARCHAR(100)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Order_Status (
        order_status_id INT AUTO_INCREMENT PRIMARY KEY,
        status_name VARCHAR(50),
        status_description TEXT,
        status_priority INT
    )
    """)

    connection.commit()
    cursor.close()
    connection.close()


# Run the setup functions
if __name__ == "__main__":
    create_database()
    setup_tables()
    print("Database and tables created successfully!")
