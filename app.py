from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

class Database:
    def __init__(self, config):
        self.config = config

    def execute_query(self, query, params=None):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def insert_reservation(self, customer_name, contact_number, num_people):
        query = "INSERT INTO reservations (customer_name, contact_number, num_people) VALUES (%s, %s, %s)"
        params = (customer_name, contact_number, num_people)
        self.execute_query(query, params)

    def delete_reservation(self, reservation_id):
        query = "DELETE FROM reservations WHERE id = %s"
        params = (reservation_id,)
        self.execute_query(query, params)

    def insert_feedback(self, customer_name, feedback_text):
        query = "INSERT INTO feedback (customer_name, feedback_text) VALUES (%s, %s)"
        params = (customer_name, feedback_text)
        self.execute_query(query, params)

class RestaurantApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'your_secret_key'
        self.db = Database({
            'user': 'root',
            'password': 'cutie123',
            'host': 'localhost',
            'database': 'restaurant'
        })
        self.menu_items = [
            {"id": 1, "name": "Pizza", "description": "Delicious pizza with assorted toppings", "price": 10},
            {"id": 2, "name": "Pasta", "description": "Authentic Italian pasta", "price": 12},
            {"id": 3, "name": "Salad", "description": "Fresh garden salad", "price": 8}
        ]
        self.setup_routes()

    def setup_routes(self):
        self.app.add_url_rule('/', 'home', self.home)
        self.app.add_url_rule('/dinein', 'dinein', self.dinein)
        self.app.add_url_rule('/order', 'order', self.order, methods=['POST'])
        self.app.add_url_rule('/payment', 'payment', self.payment)
        self.app.add_url_rule('/process_payment', 'process_payment', self.process_payment, methods=['POST'])
        self.app.add_url_rule('/payment_confirmation', 'payment_confirmation', self.payment_confirmation)
        self.app.add_url_rule('/delivery', 'delivery', self.delivery)
        self.app.add_url_rule('/process_delivery', 'process_delivery', self.process_delivery, methods=['POST'])
        self.app.add_url_rule('/cancel_order', 'cancel_order', self.cancel_order)
        self.app.add_url_rule('/reservation', 'reservation', self.reservation, methods=['GET', 'POST'])
        self.app.add_url_rule('/reservation_confirmation', 'reservation_confirmation', self.reservation_confirmation)
        self.app.add_url_rule('/feedback', 'feedback', self.feedback, methods=['GET', 'POST'])
        self.app.add_url_rule('/feedback_confirmation', 'feedback_confirmation', self.feedback_confirmation)
        self.app.add_url_rule('/order_status', 'order_status', self.order_status)
        self.app.add_url_rule('/cancel_reservation', 'cancel_reservation', self.cancel_reservation, methods=['GET', 'POST'])


    def home(self):
        import random
        customer_id = str(random.randint(1000, 9999))
        return render_template('home.html', customer_id=customer_id)

    def dinein(self):
        return render_template('dinein.html', menu_items=self.menu_items)
    
    def cancel_reservation(self):
        if request.method == 'POST':
            reservation_id = request.form.get('reservation_id')
            self.db.delete_reservation(reservation_id)
            return redirect(url_for('cancel_order'))
        else:
            return render_template('cancel_reservation.html')

    def order(self):
        total_amount = self.calculate_total_amount(request.form)
        session['order'] = {
            'customer_id': request.form.get('customer_id'),
            'items': request.form,
            'total_amount': total_amount
        }
        self.insert_order(session['order'])
        return redirect(url_for('payment'))

    def calculate_total_amount(self, form_data):
        total_amount = 0
        for item in self.menu_items:
            quantity = int(form_data.get(f'quantity_{item["id"]}', 0))
            total_amount += quantity * item['price']
        return total_amount

    def insert_order(self, order_details):
        for item in self.menu_items:
            quantity = int(order_details['items'].get(f'quantity_{item["id"]}', 0))
            if quantity > 0:
                self.db.execute_query(
                    "INSERT INTO orders (customer_id, item_name, quantity, total_amount, payment_method, address, phone) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        order_details['customer_id'],
                        item['name'],
                        quantity,
                        order_details['total_amount'],
                        '', '', ''
                    )
                )

    def payment(self):
        total_amount = session.get('order', {}).get('total_amount', 0)
        return render_template('payment.html', total_amount=total_amount)

    def process_payment(self):
        payment_method = request.form.get('payment_method')
        if payment_method in ['card', 'cash']:
            self.update_payment_method(payment_method)
            return redirect(url_for('payment_confirmation'))

    def update_payment_method(self, payment_method):
        self.db.execute_query(
            "UPDATE orders SET payment_method = %s WHERE customer_id = %s",
            (payment_method, session['order']['customer_id'])
        )

    def feedback(self):
        if request.method == 'POST':
            customer_name = request.form.get('customer_name')
            feedback_text = request.form.get('feedback_text')
            self.db.insert_feedback(customer_name, feedback_text)
            return redirect(url_for('feedback_confirmation'))
        return render_template('feedback.html')

    def feedback_confirmation(self):
        return render_template('feedback_confirmation.html')
    
    def payment_confirmation(self):
        session.pop('order', None)
        return render_template('payment_confirmation.html')

    def delivery(self):
        return render_template('delivery.html')

    def process_delivery(self):
        address = request.form.get('address')
        phone = request.form.get('phone')
        self.update_delivery_details(address, phone)
        return render_template('delivery_confirmation.html', address=address, phone=phone)

    def update_delivery_details(self, address, phone):
        self.db.execute_query(
            "UPDATE orders SET address = %s, phone = %s WHERE customer_id = %s",
            (address, phone, session['order']['customer_id'])
        )

    def cancel_order(self):
        session.pop('order', None)
        return render_template('cancel_order.html')

    def reservation(self):
        if request.method == 'POST':
            customer_name = request.form.get('customer_name')
            contact_number = request.form.get('contact_number')
            num_people = request.form.get('num_people')
            reservation_id = self.db.insert_reservation(customer_name, contact_number, num_people)
            return redirect(url_for('reservation_confirmation', reservation_id=reservation_id))
        return render_template('reservation.html')

    def reservation_confirmation(self):
        return render_template('reservation_confirmation.html')

    def cancel_reservation(self):
        if request.method == 'POST':
            reservation_id = request.form.get('reservation_id')
            self.db.delete_reservation(reservation_id)
            return redirect(url_for('cancel_order'))
        else:
            return render_template('cancel_reservation.html')
    
    def order_status(self):
        return render_template('order_status.html')

    def run(self, port=5000):
        self.app.run(debug=True, port=port)

if __name__ == '__main__':
    app = RestaurantApp()
    app.run(port=8080)
