from flask import Flask
from flask_restful import Api, Resource, reqparse
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import generate_password_hash, check_password_hash
import locale, datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'uas-dpa'  # Ganti dengan secret key yang lebih aman

# Setel locale ke format Indonesia
locale.setlocale(locale.LC_ALL, 'id_ID')

api = Api(app)
jwt = JWTManager(app)
db = SQLAlchemy(app)

# Model transaksi
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

# Model kategori transaksi
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

# Model pengguna
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Parsing argumen untuk input transaksi
transaction_parser = reqparse.RequestParser()
transaction_parser.add_argument('description', type=str, required=True, help='Description is required')
transaction_parser.add_argument('amount', type=float, required=True, help='Amount is required')
transaction_parser.add_argument('category_id', type=int, required=True, help='Category ID is required')
transaction_parser.add_argument('date', type=str, required=True, help='Date is required (format: YYYY-MM-DD)')

# Parsing argumen untuk registrasi pengguna
register_parser = reqparse.RequestParser()
register_parser.add_argument('username', type=str, required=True, help='Username is required')
register_parser.add_argument('password', type=str, required=True, help='Password is required')

# Parsing argumen untuk login pengguna
login_parser = reqparse.RequestParser()
login_parser.add_argument('username', type=str, required=True, help='Username is required')
login_parser.add_argument('password', type=str, required=True, help='Password is required')

# Resource untuk transaksi
class TransactionResource(Resource):
    @jwt_required()
    def get(self, transaction_id=None):
        if transaction_id:
            transaction = Transaction.query.get(transaction_id)
            if transaction:
                return {
                    'id': transaction.id,
                    'description': transaction.description,
                    'amount': transaction.amount,
                    'category_id': transaction.category_id,
                    'date': transaction.date.strftime('%Y-%m-%d')
                }
            return {'message': 'Transaction not found'}, 404

        transactions = Transaction.query.all()
        return [{
            'id': t.id,
            'description': t.description,
            'amount': locale.currency(t.amount, grouping=True),
            'category_id': t.category_id,
            'date': t.date.strftime('%Y-%m-%d')
        } for t in transactions]

    @jwt_required()
    def post(self):
        args = transaction_parser.parse_args()
        description = args['description']
        amount = args['amount']
        category_id = args['category_id']
        date_str = args['date']

        # Validasi format tanggal
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return {'message': 'Invalid date format. Please use YYYY-MM-DD format.'}, 400

        transaction = Transaction(description=description, amount=amount, category_id=category_id, date=date)
        db.session.add(transaction)
        db.session.commit()
        return {'message': 'Transaction created successfully'}, 201

    @jwt_required()
    def put(self, transaction_id):
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {'message': 'Transaction not found'}, 404

        args = transaction_parser.parse_args()
        transaction.description = args['description']
        transaction.amount = args['amount']
        transaction.category_id = args['category_id']
        date_str = args['date']
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return {'message': 'Invalid date format. Please use YYYY-MM-DD format.'}, 400

        transaction.date = date

        db.session.commit()
        return {'message': 'Transaction updated successfully'}

    @jwt_required()
    def delete(self, transaction_id):
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {'message': 'Transaction not found'}, 404

        db.session.delete(transaction)
        db.session.commit()
        return {'message': 'Transaction deleted successfully'}

# Resource untuk kategori transaksi
class CategoryResource(Resource):
    @jwt_required()
    def get(self, category_id=None):
        if category_id:
            category = Category.query.get(category_id)
            if category:
                return {'id': category.id, 'name': category.name}
            return {'message': 'Category not found'}, 404

        categories = Category.query.all()
        return [{'id': c.id, 'name': c.name} for c in categories]

    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name is required')
        args = parser.parse_args()

        category = Category(name=args['name'])
        db.session.add(category)
        db.session.commit()
        return {'message': 'Category created successfully'}, 201

    @jwt_required()
    def put(self, category_id):
        category = Category.query.get(category_id)
        if not category:
            return {'message': 'Category not found'}, 404

        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name is required')
        args = parser.parse_args()

        category.name = args['name']
        db.session.commit()
        return {'message': 'Category updated successfully'}

    @jwt_required()
    def delete(self, category_id):
        category = Category.query.get(category_id)
        if not category:
            return {'message': 'Category not found'}, 404

        db.session.delete(category)
        db.session.commit()
        return {'message': 'Category deleted successfully'}

# Resource untuk registrasi pengguna
class RegisterResource(Resource):
    def post(self):
        args = register_parser.parse_args()
        username = args['username']
        password = args['password']

        # Periksa keberadaan pengguna dalam database
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return {'message': 'Username already exists'}, 400

        # Buat pengguna baru
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        return {'message': 'User registered successfully'}, 201

# Resource untuk login pengguna
class LoginResource(Resource):
    def post(self):
        args = login_parser.parse_args()
        username = args['username']
        password = args['password']

        # Periksa keberadaan pengguna dalam database
        user = User.query.filter_by(username=username).first()
        if not user:
            return {'message': 'Invalid username or password'}, 401

        # Periksa kecocokan kata sandi
        if not check_password_hash(user.password, password):
            return {'message': 'Invalid username or password'}, 401

        # Buat token akses
        access_token = create_access_token(identity=user.id)

        return {'access_token': access_token}, 200

api.add_resource(CategoryResource, '/categories', '/categories/<int:category_id>')
api.add_resource(TransactionResource, '/transactions', '/transactions/<int:transaction_id>')
api.add_resource(RegisterResource, '/register')
api.add_resource(LoginResource, '/login')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
