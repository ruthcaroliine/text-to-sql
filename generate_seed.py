from faker import Faker
import random

fake = Faker()

customers = []
for i in range(1, 51):
    name = fake.name().replace("'", "''")
    email = fake.unique.email()
    date = fake.date_between(start_date='-2y', end_date='today')
    customers.append(f"('{name}', '{email}', '{date}')")

products = []
names = ["Widget Pro", "Widget Lite", "Gadget Max", "Gadget Mini", "Doohickey",
         "Thingamajig", "Whatchamacallit", "Gizmo X", "Gizmo Y", "Super Widget"]
for i, name in enumerate(names, 1):
    price = round(random.uniform(4.99, 199.99), 2)
    stock = random.randint(0, 200)
    products.append(f"('{name}', {price}, {stock})")

print("INSERT INTO customers (name, email, created_at) VALUES")
print(",\n".join(customers) + ";\n")

print("INSERT INTO products (name, price, stock) VALUES")
print(",\n".join(products) + ";\n")

# Orders
print("INSERT INTO orders (customer_id, status, created_at) VALUES")
orders = []
statuses = ['pending', 'completed', 'cancelled', 'shipped']
for i in range(1, 101):
    cid = random.randint(1, 50)
    status = random.choice(statuses)
    date = fake.date_between(start_date='-1y', end_date='today')
    orders.append(f"({cid}, '{status}', '{date}')")
print(",\n".join(orders) + ";\n")

# Order items
print("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES")
items = []
for order_id in range(1, 101):
    for _ in range(random.randint(1, 4)):
        pid = random.randint(1, 10)
        qty = random.randint(1, 5)
        price = round(random.uniform(4.99, 199.99), 2)
        items.append(f"({order_id}, {pid}, {qty}, {price})")
print(",\n".join(items) + ";")