from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow, base_fields
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from flask_socketio import SocketIO

import os
import random
import string
from functools import reduce

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://" + os.environ.get("DATABASE_URL").partition("://")[2]
socketio = SocketIO(app, cors_allowed_origins="*")
app.wsgi_app = ProxyFix(app.wsgi_app)

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
CORS(app)

# SQLAlchemy Tables
categories_table = db.Table('categories_table',
    db.Column('meal_id', db.Integer, db.ForeignKey('meal.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

mealplans_table = db.Table('mealplans_table',
    db.Column('mealplan_id', db.Integer, db.ForeignKey('mealplan.id')),
    db.Column('meal_id', db.Integer, db.ForeignKey('meal.id'))
)

shared_meals_table = db.Table('shared_meals_table',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('meal_id', db.Integer, db.ForeignKey('meal.id'))
)

shared_mealplans_table = db.Table('shared_mealplans_table',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('mealplan_id', db.Integer, db.ForeignKey('mealplan.id'))
)

shared_shoppinglists_table = db.Table('shared_shoppinglists_table',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('shoppinglist_id', db.Integer, db.ForeignKey('shoppinglist.id'))
)

outgoing_friend_requests_table = db.Table('outgoing_friend_requests_table',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)

incoming_friend_requests_table = db.Table('incoming_friend_requests_table',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)

friends_table = db.Table('friends_table',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False, unique=False)
    email = db.Column(db.String, nullable=False, unique=False)
    sessions = db.relationship("Session", backref="user", cascade='all, delete, delete-orphan')
    meals = db.relationship("Meal", backref="user", cascade='all, delete, delete-orphan')
    categories = db.relationship("Category", backref="user", cascade='all, delete, delete-orphan')
    mealplans = db.relationship("Mealplan", backref="user", cascade='all, delete, delete-orphan')
    mealplanoutlines = db.relationship("Mealplanoutline", backref="user", cascade='all, delete, delete-orphan')
    shoppinglists = db.relationship("Shoppinglist", backref="user", cascade='all, delete, delete-orphan')
    notifications = db.relationship("Notification", backref="user", cascade='all, delete, delete-orphan')
    settings = db.relationship("Settings", backref="user", cascade='all, delete, delete-orphan')
    shared_meals = db.relationship("Meal", secondary="shared_meals_table")
    shared_mealplans = db.relationship("Mealplan", secondary="shared_mealplans_table")
    shared_shoppinglists = db.relationship("Shoppinglist", secondary="shared_shoppinglists_table")
    outgoing_friend_requests = db.relationship("User", secondary="outgoing_friend_requests_table", primaryjoin=id==outgoing_friend_requests_table.c.user_id, secondaryjoin=id==outgoing_friend_requests_table.c.friend_id)
    incoming_friend_requests = db.relationship("User", secondary="incoming_friend_requests_table", primaryjoin=id==incoming_friend_requests_table.c.user_id, secondaryjoin=id==incoming_friend_requests_table.c.friend_id)
    friends = db.relationship("User", secondary="friends_table", primaryjoin=id==friends_table.c.user_id, secondaryjoin=id==friends_table.c.friend_id)
    
    def __init__(self, username, password, email):
        self.username = username
        self.password = password
        self.email = email

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, nullable=False, unique=True)
    ip = db.Column(db.String, nullable=False, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    def __init__(self, token, ip, user_id):
        self.token = token
        self.ip = ip
        self.user_id = user_id

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    default_mealplan_outline = db.Column(db.Integer, nullable=True, unique=False)
    autodelete_mealplans = db.Column(db.Boolean, nullable=False, unique=False)
    autodelete_mealplans_schedule_number = db.Column(db.Integer, nullable=False, unique=False)
    autodelete_mealplans_schedule_unit = db.Column(db.String, nullable=False, unique=False)
    default_shoppinglist_sort = db.Column(db.String, nullable=False, unique=False)
    autodelete_shoppinglists = db.Column(db.Boolean, nullable=False, unique=False)
    autodelete_shoppinglists_schedule_number = db.Column(db.Integer, nullable=False, unique=False)
    autodelete_shoppinglists_schedule_unit = db.Column(db.String, nullable=False, unique=False)
    allow_notifications = db.Column(db.Boolean, nullable=False, unique=False)
    allow_nonfriend_sharing = db.Column(db.Boolean, nullable=False, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    def __init__(self, default_mealplan_outline, autodelete_mealplans, autodelete_mealplans_schedule_number, autodelete_mealplans_schedule_unit, default_shoppinglist_sort, autodelete_shoppinglists, autodelete_shoppinglists_schedule_number, autodelete_shoppinglists_schedule_unit, allow_notifications, allow_nonfriend_sharing, user_id):
        self.default_mealplan_outline = default_mealplan_outline
        self.autodelete_mealplans = autodelete_mealplans
        self.autodelete_mealplans_schedule_number = autodelete_mealplans_schedule_number
        self.autodelete_mealplans_schedule_unit = autodelete_mealplans_schedule_unit
        self.default_shoppinglist_sort = default_shoppinglist_sort
        self.autodelete_shoppinglists = autodelete_shoppinglists
        self.autodelete_shoppinglists_schedule_number = autodelete_shoppinglists_schedule_number
        self.autodelete_shoppinglists_schedule_unit = autodelete_shoppinglists_schedule_unit
        self.allow_notifications = allow_notifications
        self.allow_nonfriend_sharing = allow_nonfriend_sharing
        self.user_id = user_id

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String, nullable=False, unique=False)
    username = db.Column(db.String, nullable=True, unique=False)
    name = db.Column(db.String, nullable=True, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    
    def __init__(self, category, username, name, user_id):
        self.category = category
        self.username = username
        self.name = name
        self.user_id = user_id

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    description = db.Column(db.String, nullable=True, unique=False)
    image_url = db.Column(db.String, nullable=True, unique=False)
    difficulty = db.Column(db.Integer, nullable=False, unique=False)
    sleep_until = db.Column(db.String, nullable=True, unique=False)
    user_username = db.Column(db.String, nullable=False, unique=False)
    owner_username = db.Column(db.String, nullable=False, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe = db.relationship("Recipe", backref="meal", cascade='all, delete, delete-orphan')
    categories = db.relationship("Category", secondary="categories_table")
    mealplans = db.relationship("Mealplan", secondary="mealplans_table")
    shared_users = db.relationship("User", secondary="shared_meals_table")
    
    def __init__(self, name, description, image_url, difficulty, user_username, owner_username, user_id):
        self.name = name
        self.description = description
        self.image_url = image_url
        self.difficulty = difficulty
        self.sleep_until = None
        self.user_username = user_username
        self.owner_username = owner_username
        self.user_id = user_id

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    meals = db.relationship("Meal", secondary="categories_table")
    
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey("meal.id"), nullable=False)
    stepsections = db.relationship("Stepsection", backref="recipe", cascade='all, delete, delete-orphan')
    steps = db.relationship("Step", backref="recipe", cascade='all, delete, delete-orphan')
    ingredientsections = db.relationship("Ingredientsection", backref="recipe", cascade='all, delete, delete-orphan')
    ingredients = db.relationship("Ingredient", backref="recipe", cascade='all, delete, delete-orphan')
    
    def __init__(self, meal_id):
        self.meal_id = meal_id

class Stepsection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False, unique=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    steps = db.relationship("Step", backref="stepsection", cascade='all, delete, delete-orphan')
    
    def __init__(self, title, recipe_id):
        self.title = title
        self.recipe_id = recipe_id

class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False, unique=False)
    text = db.Column(db.String, nullable=False, unique=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    stepsection_id = db.Column(db.Integer, db.ForeignKey("stepsection.id"), nullable=True)
    
    def __init__(self, number, text, recipe_id, stepsection_id):
        self.number = number
        self.text = text
        self.recipe_id = recipe_id
        self.stepsection_id = stepsection_id

class Ingredientsection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False, unique=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    ingredients = db.relationship("Ingredient", backref="ingredientsection", cascade='all, delete, delete-orphan')
    
    def __init__(self, title, recipe_id):
        self.title = title
        self.recipe_id = recipe_id

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    amount = db.Column(db.String, nullable=False, unique=False)
    unit = db.Column(db.String, nullable=True, unique=False)
    category = db.Column(db.String, nullable=True, unique=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    shoppingingredients = db.relationship("Shoppingingredient", backref="ingredient", cascade='all, delete, delete-orphan')
    ingredientsection_id = db.Column(db.Integer, db.ForeignKey("ingredientsection.id"), nullable=True)
    
    def __init__(self, name, amount, unit, category, recipe_id, ingredientsection_id):
        self.name = name
        self.amount = amount
        self.unit = unit
        self.category = category
        self.recipe_id = recipe_id
        self.ingredientsection_id = ingredientsection_id

class Mealplan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    created_on = db.Column(db.String, nullable=False, unique=False)
    user_username = db.Column(db.String, nullable=False, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    meals = db.relationship("Meal", secondary="mealplans_table")
    rules = db.relationship("Rule", backref="mealplan", cascade='all, delete, delete-orphan')
    shoppinglists = db.relationship("Shoppinglist", backref="mealplan", cascade='all, delete, delete-orphan')
    shared_users = db.relationship("User", secondary="shared_mealplans_table")
    
    def __init__(self, name, created_on, user_username, user_id):
        self.name = name
        self.created_on = created_on
        self.user_username = user_username
        self.user_id = user_id

class Mealplanoutline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    number = db.Column(db.String, nullable=False, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rules = db.relationship("Rule", backref="mealplanoutline", cascade='all, delete, delete-orphan')
    
    def __init__(self, name, number, user_id):
        self.name = name
        self.number = number
        self.user_id = user_id

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rule_type = db.Column(db.String, nullable=False, unique=False)
    rule = db.Column(db.String, nullable=False, unique=False)
    amount = db.Column(db.Integer, nullable=False, unique=False)
    value = db.Column(db.String, nullable=False, unique=False)
    mealplan_id = db.Column(db.Integer, db.ForeignKey("mealplan.id"), nullable=True)
    mealplanoutline_id = db.Column(db.Integer, db.ForeignKey("mealplanoutline.id"), nullable=True)
    
    def __init__(self, rule_type, rule, amount, value, mealplan_id, mealplanoutline_id):
        self.rule_type = rule_type
        self.rule = rule
        self.amount = amount
        self.value = value
        self.mealplan_id = mealplan_id
        self.mealplanoutline_id = mealplanoutline_id

class Shoppinglist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    created_on = db.Column(db.String, nullable=False, unique=False)
    updates_hidden = db.Column(db.Boolean, nullable=False, unique=False)
    is_sublist = db.Column(db.Boolean, nullable=False, unique=False)
    user_username = db.Column(db.String, nullable=False, unique=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    mealplan_id = db.Column(db.Integer, db.ForeignKey("mealplan.id"), nullable=True)
    shoppingingredients = db.relationship("Shoppingingredient", backref="shoppinglist", cascade='all, delete, delete-orphan')
    shared_users = db.relationship("User", secondary="shared_shoppinglists_table")
    
    def __init__(self, name, created_on, updates_hidden, is_sublist, user_username, user_id, mealplan_id):
        self.name = name
        self.created_on = created_on
        self.updates_hidden = updates_hidden
        self.is_sublist = is_sublist
        self.user_username = user_username
        self.user_id = user_id
        self.mealplan_id = mealplan_id

class Shoppingingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    amount = db.Column(db.String, nullable=False, unique=False)
    unit = db.Column(db.String, nullable=True, unique=False)
    category = db.Column(db.String, nullable=True, unique=False)
    obtained = db.Column(db.Boolean, nullable=False, unique=False)
    multiplier = db.Column(db.Integer, nullable=False, unique=False)
    meal_name = db.Column(db.String, nullable=True, unique=False)
    shoppinglist_id = db.Column(db.Integer, db.ForeignKey("shoppinglist.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("ingredient.id"), nullable=True)
    
    def __init__(self, name, amount, unit, category, multiplier, meal_name, shoppinglist_id, ingredient_id):
        self.name = name
        self.amount = amount
        self.unit = unit
        self.category = category
        self.obtained = False
        self.multiplier = multiplier
        self.meal_name = meal_name
        self.shoppinglist_id = shoppinglist_id
        self.ingredient_id = ingredient_id

# Marshmallow Schemas
class ShoppingingredientSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "amount", "unit", "category", "obtained", "multiplier", "meal_name", "shoppinglist_id", "ingredient_id")

shoppingingredient_schema = ShoppingingredientSchema()
multiple_shoppingingredient_schema = ShoppingingredientSchema(many=True)

class ShoppinglistSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "created_on", "updates_hidden", "is_sublist", "user_username", "user_id", "mealplan_id", "shoppingingredients")
    shoppingingredients = ma.Nested(multiple_shoppingingredient_schema)

shoppinglist_schema = ShoppinglistSchema()
multiple_shoppinglist_schema = ShoppinglistSchema(many=True)

class RuleSchema(ma.Schema):
    class Meta:
        fields = ("id", "rule_type", "rule", "amount", "value", "mealplan_id", "mealplanoutline_id")

rule_schema = RuleSchema()
multiple_rule_schema = RuleSchema(many=True)

class MealplanoutlineSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "number", "user_id", "rules")
    rules = ma.Nested(multiple_rule_schema)

mealplanoutline_schema = MealplanoutlineSchema()
multiple_mealplanoutline_schema = MealplanoutlineSchema(many=True)

class IngredientSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "amount", "unit", "category", "recipe_id", "shoppingingredients", "ingredientsection_id")
    shoppingingredients = ma.Nested(multiple_shoppingingredient_schema)

ingredient_schema = IngredientSchema()
multiple_ingredient_schema = IngredientSchema(many=True)

class IngredientsectionSchema(ma.Schema):
    class Meta:
        fields = ("id", "title", "recipe_id", "ingredients")
    ingredients = ma.Nested(multiple_ingredient_schema)

ingredientsection_schema = IngredientsectionSchema()
multiple_ingredientsection_schema = IngredientsectionSchema(many=True)

class StepSchema(ma.Schema):
    class Meta:
        fields = ("id", "number", "text", "recipe_id", "stepsection_id")

step_schema = StepSchema()
multiple_step_schema = StepSchema(many=True)

class StepsectionSchema(ma.Schema):
    class Meta:
        fields = ("id", "title", "recipe_id", "steps")
    steps = ma.Nested(multiple_step_schema)

stepsection_schema = StepsectionSchema()
multiple_stepsection_schema = StepsectionSchema(many=True)

class RecipeSchema(ma.Schema):
    class Meta:
        fields = ("id", "meal_id", "stepsections", "steps", "ingredientsections", "ingredients")
    stepsections = ma.Nested(multiple_stepsection_schema)
    steps = ma.Nested(multiple_step_schema)
    ingredientsections = ma.Nested(multiple_ingredientsection_schema)
    ingredients = ma.Nested(multiple_ingredient_schema)

recipe_schema = RecipeSchema()
multiple_recipe_schema = RecipeSchema(many=True)

class CategorySchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "user_id")

category_schema = CategorySchema()
multiple_category_schema = CategorySchema(many=True)

class MealSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "description", "image_url", "difficulty", "sleep_until", "categories", "user_username", "owner_username", "user_id", "recipe")
    categories = ma.Nested(multiple_category_schema)
    recipe = base_fields.Function(lambda fields: recipe_schema.dump(fields.recipe[0] if len(fields.recipe) > 0 else None))

meal_schema = MealSchema()
multiple_meal_schema = MealSchema(many=True)

class MealplanSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "created_on", "meals", "rules", "user_username", "user_id", "shoppinglist", "sub_shoppinglist")
    meals = ma.Nested(multiple_meal_schema)
    rules = ma.Nested(multiple_rule_schema)
    shoppinglist = base_fields.Function(lambda fields: shoppinglist_schema.dump(list(filter(lambda shoppinglist: not shoppinglist.is_sublist, fields.shoppinglists))[0] if len(fields.shoppinglists) > 0 else None))
    sub_shoppinglist = base_fields.Function(lambda fields: shoppinglist_schema.dump(list(filter(lambda shoppinglist: shoppinglist.is_sublist, fields.shoppinglists))[0] if len(fields.shoppinglists) > 1 else None))

mealplan_schema = MealplanSchema()
multiple_mealplan_schema = MealplanSchema(many=True)

class NotificationSchema(ma.Schema):
    class Meta:
        fields = ("id", "category", "username", "name", "user_id")

notification_schema = NotificationSchema()
multiple_notification_schema = NotificationSchema(many=True)

class SettingsSchema(ma.Schema):
    class Meta:
        fields = ("id", "default_mealplan_outline", "autodelete_mealplans", "autodelete_mealplans_schedule_number", "autodelete_mealplans_schedule_unit", "default_shoppinglist_sort", "autodelete_shoppinglists", "autodelete_shoppinglists_schedule_number", "autodelete_shoppinglists_schedule_unit", "allow_notifications", "allow_nonfriend_sharing", "user_id")

settings_schema = SettingsSchema()
multiple_settings_schema = SettingsSchema(many=True)

class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "username", "email", "meals", "categories", "mealplans", "mealplanoutlines", "shoppinglists", "notifications", "settings", "shared_meals", "shared_mealplans", "shared_shoppinglists", "outgoing_friend_requests", "incoming_friend_requests", "friends")
    meals = ma.Nested(multiple_meal_schema)
    categories = ma.Nested(multiple_category_schema)
    mealplans = ma.Nested(multiple_mealplan_schema)
    mealplanoutlines = ma.Nested(multiple_mealplanoutline_schema)
    shoppinglists = ma.Nested(multiple_shoppinglist_schema)
    notifications = ma.Nested(multiple_notification_schema)
    settings = base_fields.Function(lambda fields: settings_schema.dump(fields.settings[0]))
    shared_meals = ma.Nested(multiple_meal_schema)
    shared_mealplans = ma.Nested(multiple_mealplan_schema)
    shared_shoppinglists = ma.Nested(multiple_shoppinglist_schema)
    outgoing_friend_requests = base_fields.Function(lambda fields: list(map(lambda friend: { "user_id": friend.id, "username": friend.username }, fields.outgoing_friend_requests)))
    incoming_friend_requests = base_fields.Function(lambda fields: list(map(lambda friend: { "user_id": friend.id, "username": friend.username }, fields.incoming_friend_requests)))
    friends = base_fields.Function(lambda fields: list(map(lambda friend: { "user_id": friend.id, "username": friend.username }, fields.friends)))

user_schema = UserSchema()
multiple_user_schema = UserSchema(many=True)

# Flask Endpoints
@app.before_request
def before_request():
    if request.authorization is None or request.authorization.username != os.environ.get("AUTH_USERNAME") or request.authorization.password != os.environ.get("AUTH_PASSWORD"):
        return jsonify({
            "status": 403,
            "message": "Unauthorized",
            "data": {}
        })

@app.route("/user/add", methods=["POST"])
def add_user():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    username_taken_check = db.session.query(User).filter(User.username == username).first()
    if username_taken_check is not None:
        return jsonify({
            "status": 400,
            "message": "Username already taken.",
            "data": {}
        })

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    record = User(username, hashed_password, email)
    db.session.add(record)
    db.session.commit()

    settings = Settings(None, False, 1, "week", "arbitrary", False, 1, "week", True, True, record.id)
    db.session.add(settings)
    db.session.commit()

    token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
    while db.session.query(Session).filter(Session.token == token).first() != None:
        token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))

    hashed_ip = bcrypt.generate_password_hash(request.remote_addr).decode("utf-8")

    session = Session(token, hashed_ip, record.id)
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "User Added",
        "data": {
            "user": user_schema.dump(record),
            "token": token
        }
    })

@app.route("/user/login", methods=["POST"])
def login_user():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    record = db.session.query(User).filter(User.username == username).first()
    if record is None:
        return jsonify({
            "status": 400,
            "message": "Invalid username or password",
            "data": {}
        })

    password_check = bcrypt.check_password_hash(record.password, password)
    if password_check is False:
        return jsonify({
            "status": 400,
            "message": "Invalid username or password",
            "data": {}
        })

    token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
    while db.session.query(Session).filter(Session.token == token).first() != None:
        token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))

    hashed_ip = bcrypt.generate_password_hash(str(request.remote_addr)).decode("utf-8")

    session = Session(token, hashed_ip, record.id)
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Valid username and password",
        "data": {
            "user": user_schema.dump(record),
            "token": token
        }
    })

@app.route("/user/friend/request", methods=["POST"])
def request_friend():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    user_id = data.get("user_id")
    friend_username = data.get("friend_username")

    user = db.session.query(User).filter(User.id == user_id).first()
    friend = db.session.query(User).filter(User.username == friend_username).first()

    if friend is None:
        return jsonify({
            "status": 400,
            "message": "User doesn't exist.",
            "data": {}
        })
    if user.friends.count(friend) > 0:
        return jsonify({
            "status": 400,
            "message": "User already friended.",
            "data": {}
        })
    if user.outgoing_friend_requests.count(friend) > 0:
        return jsonify({
            "status": 400,
            "message": "Friend request already sent.",
            "data": {}
        })

    user.outgoing_friend_requests.append(friend)
    db.session.commit()

    friend.incoming_friend_requests.append(user)
    db.session.commit()

    notification = Notification("friendrequest", user.username, None, friend.id)
    db.session.add(notification)
    db.session.commit()

    socketio.emit("friend-request-update", {
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend),
            "notification": notification_schema.dump(notification)
        },
        "type": "add"
    })

    return jsonify({
        "status": 200,
        "message": "Friend Request Added",
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend)
        }
    })

@app.route("/user/get", methods=["GET"])
def get_all_users():
    records = db.session.query(User).all()
    return jsonify(multiple_user_schema.dump(records))

@app.route("/user/get/id/<id>", methods=["GET"])
def get_user_by_id(id):
    record = db.session.query(User).filter(User.id == id).first()
    return jsonify(user_schema.dump(record))

@app.route("/user/get/token/<token>", methods=["GET"])
def get_user_by_token(token):
    session = db.session.query(Session).filter(Session.token == token).first()
    if session is None:
        return jsonify({
            "status": 403,
            "message": "User not authenticated.",
            "data": {}
        })
    if bcrypt.check_password_hash(session.ip, str(request.remote_addr)) is False:
        return jsonify({
            "status": 403,
            "message": "User not authenticated.",
            "data": {}
        })

    record = db.session.query(User).filter(User.id == session.user_id).first()
    return jsonify({
        "status": 200,
        "message": "User authenticated.",
        "data": user_schema.dump(record)
    })

@app.route("/user/update/<id>", methods=["PUT"])
def update_user(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    record = db.session.query(User).filter(User.id == id).first()
    if username is not None:
        username_taken_check = db.session.query(User).filter(User.username == username).first()
        if username_taken_check is not None:
            return jsonify({
                "status": 400,
                "message": "Username already taken.",
                "data": {}
            })
        record.username = username
    if password is not None:
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        record.password = hashed_password
    if email is not None:
        record.email = email

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "User Updated",
        "data": user_schema.dump(record)
    })

@app.route("/user/delete/<id>", methods=["DELETE"])
def delete_user(id):
    record = db.session.query(User).filter(User.id == id).first()
    for friend in record.friends:
        friend.friends.remove(record)
        db.session.commit()
        friend.incoming_friend_requests.remove(record)
        db.session.commit()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "User Deleted",
        "data": user_schema.dump(record)
    })

@app.route("/user/logout/single/<token>", methods=["DELETE"])
def logout_user(token):
    record = db.session.query(Session).filter(Session.token == token).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "User Logged Out",
        "data": {}
    })

@app.route("/user/logout/all/<id>", methods=["DELETE"])
def logout_user_all(id):
    record = db.session.query(User).filter(User.id == id).first()
    for session in record.sessions:
        db.session.delete(session)
        db.session.commit()
    return jsonify({
        "status": 200,
        "message": "User Logged Out",
        "data": {}
    })

@app.route("/user/friend/cancel/<id>/<friend_id>", methods=["DELETE"])
def cancel_friend_request(id, friend_id):
    user = db.session.query(User).filter(User.id == id).first()
    friend = db.session.query(User).filter(User.id == friend_id).first()
    
    if user.outgoing_friend_requests.count(friend) == 0:
        return jsonify({
                "status": 400,
                "message": "Error: Friend request does not exist.",
                "data": {}
            })

    user.outgoing_friend_requests.remove(friend)
    db.session.commit()

    friend.incoming_friend_requests.remove(user)
    db.session.commit()

    notification = db.session.query(Notification).filter(Notification.category == "friendrequest").filter(Notification.username == user.username).filter(Notification.user_id == friend.id).first()
    if notification is not None:
        db.session.delete(notification)
        db.session.commit()

    socketio.emit("friend-request-update", {
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend),
            "notification": notification_schema.dump(notification)
        },
        "type": "delete"
    })

    return jsonify({
        "status": 200,
        "message": "Friend Request Deleted",
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend)
        }
    })

@app.route("/user/friend/accept/<id>/<friend_id>", methods=["DELETE"])
def accept_friend_request(id, friend_id):
    user = db.session.query(User).filter(User.id == id).first()
    friend = db.session.query(User).filter(User.id == friend_id).first()
    
    if user.incoming_friend_requests.count(friend) == 0:
        return jsonify({
                "status": 400,
                "message": "Error: Friend request does not exist.",
                "data": {}
            })

    user.friends.append(friend)
    db.session.commit()

    friend.friends.append(user)
    db.session.commit()

    user.incoming_friend_requests.remove(friend)
    db.session.commit()

    friend.outgoing_friend_requests.remove(user)
    db.session.commit()

    if user.outgoing_friend_requests.count(friend) > 0:
        user.outgoing_friend_requests.remove(friend)
        db.session.commit()
        friend.incoming_friend_requests.remove(user)
        db.session.commit()

    removed_notification = db.session.query(Notification).filter(Notification.category == "friendrequest").filter(Notification.username == user.username).filter(Notification.user_id == friend.id).first()
    if removed_notification is not None:
        db.session.delete(removed_notification)
        db.session.commit()

    notification = Notification("friend", user.username, None, friend.id)
    db.session.add(notification)
    db.session.commit()

    socketio.emit("friend-update", {
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend),
            "removed_notification": notification_schema.dump(removed_notification),
            "notification": notification_schema.dump(notification)
        },
        "type": "add"
    })

    return jsonify({
        "status": 200,
        "message": "Friend Added",
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend)
        }
    })

@app.route("/user/friend/reject/<id>/<friend_id>", methods=["DELETE"])
def reject_friend_request(id, friend_id):
    user = db.session.query(User).filter(User.id == id).first()
    friend = db.session.query(User).filter(User.id == friend_id).first()
    
    if user.incoming_friend_requests.count(friend) == 0:
        return jsonify({
                "status": 400,
                "message": "Error: Friend request does not exist.",
                "data": {}
            })

    user.incoming_friend_requests.remove(friend)
    db.session.commit()

    friend.outgoing_friend_requests.remove(user)
    db.session.commit()

    socketio.emit("shared-friend-request-update", {
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend)
        },
        "type": "delete"
    })

    return jsonify({
        "status": 200,
        "message": "Friend Request Deleted",
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend)
        }
    })

@app.route("/user/friend/delete/<id>/<friend_id>", methods=["DELETE"])
def delete_friend(id, friend_id):
    user = db.session.query(User).filter(User.id == id).first()
    friend = db.session.query(User).filter(User.id == friend_id).first()
    
    if user.friends.count(friend) == 0:
        return jsonify({
                "status": 400,
                "message": "Error: Friend does not exist.",
                "data": {}
            })

    user.friends.remove(friend)
    db.session.commit()

    friend.friends.remove(user)
    db.session.commit()

    notification = db.session.query(Notification).filter(Notification.category == "friend").filter(Notification.username == user.username).filter(Notification.user_id == friend.id).first()
    if notification is not None:
        db.session.delete(notification)
        db.session.commit()

    socketio.emit("friend-update", {
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend),
            "notification": notification_schema.dump(notification)
        },
        "type": "delete"
    })

    return jsonify({
        "status": 200,
        "message": "Friend Deleted",
        "data": {
            "user": user_schema.dump(user),
            "friend": user_schema.dump(friend)
        }
    })


@app.route("/settings/get", methods=["GET"])
def get_all_settings():
    records = db.session.query(Settings).all()
    return jsonify(multiple_settings_schema.dump(records))

@app.route("/settings/get/<id>", methods=["GET"])
def get_settings_by_id(id):
    record = db.session.query(Settings).filter(Settings.id == id).first()
    return jsonify(settings_schema.dump(record))

@app.route("/settings/update/<id>", methods=["PUT"])
def update_settings(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    default_mealplan_outline = data.get("default_mealplan_outline", -1)
    autodelete_mealplans = data.get("autodelete_mealplans")
    autodelete_mealplans_schedule_number = data.get("autodelete_mealplans_schedule_number")
    autodelete_mealplans_schedule_unit = data.get("autodelete_mealplans_schedule_unit")
    default_shoppinglist_sort = data.get("default_shoppinglist_sort")
    autodelete_shoppinglists = data.get("autodelete_shoppinglists")
    autodelete_shoppinglists_schedule_number = data.get("autodelete_shoppinglists_schedule_number")
    autodelete_shoppinglists_schedule_unit = data.get("autodelete_shoppinglists_schedule_unit")
    allow_notifications = data.get("allow_notifications")
    allow_nonfriend_sharing = data.get("allow_nonfriend_sharing")

    record = db.session.query(Settings).filter(Settings.id == id).first()
    if default_mealplan_outline != -1:
        record.default_mealplan_outline = default_mealplan_outline
    if autodelete_mealplans is not None:
        record.autodelete_mealplans = autodelete_mealplans
    if autodelete_mealplans_schedule_number is not None:
        record.autodelete_mealplans_schedule_number = autodelete_mealplans_schedule_number
    if autodelete_mealplans_schedule_unit is not None:
        record.autodelete_mealplans_schedule_unit = autodelete_mealplans_schedule_unit
    if default_shoppinglist_sort is not None:
        record.default_shoppinglist_sort = default_shoppinglist_sort
    if autodelete_shoppinglists is not None:
        record.autodelete_shoppinglists = autodelete_shoppinglists
    if autodelete_shoppinglists_schedule_number is not None:
        record.autodelete_shoppinglists_schedule_number = autodelete_shoppinglists_schedule_number
    if autodelete_shoppinglists_schedule_unit is not None:
        record.autodelete_shoppinglists_schedule_unit = autodelete_shoppinglists_schedule_unit
    if allow_notifications is not None:
        record.allow_notifications = allow_notifications
    if allow_nonfriend_sharing is not None:
        record.allow_nonfriend_sharing = allow_nonfriend_sharing

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Settings Updated",
        "data": settings_schema.dump(record)
    })


@app.route("/notification/add", methods=["POST"])
def add_notification():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    category = data.get("category")
    username = data.get("username")
    name = data.get("name")
    user_id = data.get("user_id")

    record = Notification(category, username, name, user_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Notification Added",
        "data": notification_schema.dump(record)
    })

@app.route("/notification/get", methods=["GET"])
def get_all_notifications():
    records = db.session.query(Notification).all()
    return jsonify(multiple_notification_schema.dump(records))

@app.route("/notification/get/<id>", methods=["GET"])
def get_notification_by_id(id):
    record = db.session.query(Notification).filter(Notification.id == id).first()
    return jsonify(notification_schema.dump(record))

@app.route("/notification/delete/single/<id>", methods=["DELETE"])
def delete_notification(id):
    record = db.session.query(Notification).filter(Notification.id == id).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "Notification Deleted",
        "data": notification_schema.dump(record)
    })

@app.route("/notification/delete/all/<user_id>", methods=["DELETE"])
def delete_all_notifications(user_id):
    user = db.session.query(User).filter(User.id == user_id).first()
    records = []
    for notification in user.notifications:
        record = db.session.query(Notification).filter(Notification.id == notification.id).first()
        db.session.delete(record)
        db.session.commit()
        records.append(record)
    return jsonify({
        "status": 200,
        "message": "Notifications Deleted",
        "data": {
            "user": user_schema.dump(user),
            "notifications": multiple_notification_schema.dump(records)
        }
    })


@app.route("/meal/add", methods=["POST"])
def add_meal():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    description = data.get("description")
    image_url = data.get("image_url")
    difficulty = data.get("difficulty", 0)
    owner_username = data.get("owner_username")
    user_id = data.get("user_id")

    user = db.session.query(User).filter(User.id == user_id).first()

    record = Meal(name, description, image_url, difficulty, user.username, owner_username, user_id)
    db.session.add(record)
    db.session.commit()

    recipe = Recipe(record.id)
    db.session.add(recipe)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Meal Added",
        "data": meal_schema.dump(record)
    })

@app.route("/meal/share", methods=["POST"])
def share_meal():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    meal_id = data.get("meal_id")
    username = data.get("username")

    shared_meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
    shared_user = db.session.query(User).filter(User.username == username).first()
    user = db.session.query(User).filter(User.id == shared_meal.user_id).first()

    if shared_user is None:
        return jsonify({
            "status": 400,
            "message": "User doesn't exist.",
            "data": {}
        })

    if not shared_user.settings[0].allow_nonfriend_sharing and not user in shared_user.friends:
        return jsonify({
            "status": 400,
            "message": f"Sorry, {shared_user.username} is only accepting shares from friends.",
            "data": {}
        })

    shared_user.shared_meals.append(shared_meal)
    db.session.commit()

    notification = Notification("meal", shared_meal.user_username, shared_meal.name, shared_user.id)
    db.session.add(notification)
    db.session.commit()

    socketio.emit("meal-share-update", {
        "data": {
            "meal": meal_schema.dump(shared_meal),
            "user": user_schema.dump(shared_user),
            "notification": notification_schema.dump(notification)
        },
        "type": "add"
    })

    return jsonify({
        "status": 200,
        "message": "Meal Shared",
        "data": {
            "meal": meal_schema.dump(shared_meal),
            "user": user_schema.dump(shared_user)
        }
    })

@app.route("/meal/get", methods=["GET"])
def get_all_meals():
    records = db.session.query(Meal).all()
    return jsonify(multiple_meal_schema.dump(records))

@app.route("/meal/get/<id>", methods=["GET"])
def get_meal_by_id(id):
    record = db.session.query(Meal).filter(Meal.id == id).first()
    return jsonify(meal_schema.dump(record))

@app.route("/meal/update/<id>", methods=["PUT"])
def update_meal(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    description = data.get("description")
    difficulty = data.get("difficulty")
    image_url = data.get("image_url", -1)
    sleep_until = data.get("sleep_until")

    record = db.session.query(Meal).filter(Meal.id == id).first()
    if name is not None:
        record.name = name
    if description is not None:
        record.description = description
    if image_url != -1:
        record.image_url = image_url
    if difficulty is not None:
        record.difficulty = difficulty
    if sleep_until is not None:
        record.sleep_until = sleep_until

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Meal Updated",
        "data": meal_schema.dump(record)
    })

@app.route("/meal/delete/<id>", methods=["DELETE"])
def delete_meal(id):
    record = db.session.query(Meal).filter(Meal.id == id).first()
    recipe = db.session.query(Recipe).filter(Recipe.meal_id == record.id).first()
    for user in record.shared_users:
        user.shared_meals.remove(record)
        db.session.commit()
    db.session.delete(record)
    db.session.commit()

    for ingredient in recipe.ingredients:
        for shoppingingredient in ingredient.shoppingingredients:
            db.session.delete(shoppingingredient)
            db.session.commit()
            socketio.emit("shared-shoppingingredient-update", {
                "data": shoppingingredient_schema.dump(shoppingingredient),
                "type": "delete"
            })

    return jsonify({
        "status": 200,
        "message": "Meal Deleted",
        "data": meal_schema.dump(record)
    })

@app.route("/meal/unshare/<id>/<user_id>", methods=["DELETE"])
def unshare_meal(id, user_id):
    record = db.session.query(Meal).filter(Meal.id == id).first()
    shared_user = db.session.query(User).filter(User.id == user_id).first()

    if shared_user.shared_meals.count(record) == 0:
        return jsonify({
                "status": 400,
                "message": "Error: Shared meal does not exist.",
                "data": {}
            })

    shared_user.shared_meals.remove(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Meal Share Deleted",
        "data":{
            "meal": meal_schema.dump(record),
            "user": user_schema.dump(shared_user)
        }
    })


@app.route("/category/add", methods=["POST"])
def add_category():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    user_id = data.get("user_id")

    record = Category(name, user_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Category Added",
        "data": category_schema.dump(record)
    })

@app.route("/category/add/multiple", methods=["POST"])
def add_multiple_categories():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    records = []
    for data in data:
        name = data.get("name")
        user_id = data.get("user_id")

        record = Category(name, user_id)
        db.session.add(record)
        db.session.commit()

        records.append(record)

    return jsonify({
        "status": 200,
        "message": "Categories Added",
        "data": multiple_category_schema.dump(records)
    })

@app.route("/category/attach", methods=["POST"])
def attach_category():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    category_id = data.get("category_id")
    meal_id = data.get("meal_id")

    record = db.session.query(Category).filter(Category.id == category_id).first()
    meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
    meal.categories.append(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Category Attached",
        "data": {
            "category": category_schema.dump(record),
            "meal": meal_schema.dump(meal)
        }
    })

@app.route("/category/attach/multiple", methods=["POST"])
def attach_multiple_categories():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()

    records = []
    meals = []
    for data in data:
        category_id = data.get("category_id")
        meal_id = data.get("meal_id")

        record = db.session.query(Category).filter(Category.id == category_id).first()
        meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
        meal.categories.append(record)
        db.session.commit()

        records.append(record)
        meals.append(meal)

    return jsonify({
        "status": 200,
        "message": "Category Attached",
        "data": {
            "categories": multiple_category_schema.dump(records),
            "meals": multiple_meal_schema.dump(meals)
        }
    })

@app.route("/category/get", methods=["GET"])
def get_all_categories():
    records = db.session.query(Category).all()
    return jsonify(multiple_category_schema.dump(records))

@app.route("/category/get/<id>", methods=["GET"])
def get_category_by_id(id):
    record = db.session.query(Category).filter(Category.id == id).first()
    return jsonify(category_schema.dump(record))

@app.route("/category/update/<id>", methods=["PUT"])
def update_category(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")

    record = db.session.query(Category).filter(Category.id == id).first()
    if name is not None:
        record.name = name

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Category Updated",
        "data": category_schema.dump(record)
    })

@app.route("/category/unattach", methods=["DELETE"])
def unattach_category():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    category_id = data.get("category_id")
    meal_id = data.get("meal_id")

    record = db.session.query(Category).filter(Category.id == category_id).first()
    meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
    meal.categories.remove(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Category Unattached",
        "data": {
            "category": category_schema.dump(record),
            "meal": meal_schema.dump(meal)
        }
    })

@app.route("/category/unattach/multiple", methods=["DELETE"])
def unattach_multiple_categories():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()

    records = []
    meals = []
    for data in data:
        category_id = data.get("category_id")
        meal_id = data.get("meal_id")

        record = db.session.query(Category).filter(Category.id == category_id).first()
        meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
        meal.categories.remove(record)
        db.session.commit()

        records.append(record)
        meals.append(meal)

    return jsonify({
        "status": 200,
        "message": "Category Unattached",
        "data": {
            "categories": multiple_category_schema.dump(records),
            "meals": multiple_meal_schema.dump(meals)
        }
    })

@app.route("/category/delete/<id>", methods=["DELETE"])
def delete_category(id):
    record = db.session.query(Category).filter(Category.id == id).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "Category Deleted",
        "data": category_schema.dump(record)
    })


@app.route("/recipe/add", methods=["POST"])
def add_recipe():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    meal_id = data.get("meal_id")

    recipe_check = db.session.query(Recipe).filter(Recipe.meal_id == meal_id).first()
    if recipe_check is not None:
        return jsonify({
            "status": 400,
            "message": "Error: Recipe already exists.",
            "data": {}
        })

    record = Recipe(meal_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Recipe Added",
        "data": recipe_schema.dump(record)
    })

@app.route("/recipe/get", methods=["GET"])
def get_all_recipes():
    records = db.session.query(Recipe).all()
    return jsonify(multiple_recipe_schema.dump(records))

@app.route("/recipe/get/<id>", methods=["GET"])
def get_recipe_by_id(id):
    record = db.session.query(Recipe).filter(Recipe.id == id).first()
    return jsonify(meal_schema.dump(record))

@app.route("/recipe/delete/<id>", methods=["DELETE"])
def delete_recipe(id):
    record = db.session.query(Recipe).filter(Recipe.id == id).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "Recipe Deleted",
        "data": recipe_schema.dump(record)
    })


@app.route("/stepsection/add", methods=["POST"])
def add_stepsection():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    title = data.get("title")
    recipe_id = data.get("recipe_id")

    record = Stepsection(title, recipe_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Stepsection Added",
        "data": stepsection_schema.dump(record)
    })

@app.route("/stepsection/add/multiple", methods=["POST"])
def add_multiple_stepsections():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    records = []
    for data in data:
        title = data.get("title")
        recipe_id = data.get("recipe_id")

        record = Stepsection(title, recipe_id)
        db.session.add(record)
        db.session.commit()

        records.append(record)

    return jsonify({
        "status": 200,
        "message": "Stepsections Added",
        "data": multiple_stepsection_schema.dump(records)
    })

@app.route("/stepsection/get", methods=["GET"])
def get_all_stepsections():
    records = db.session.query(Stepsection).all()
    return jsonify(multiple_stepsection_schema.dump(records))

@app.route("/stepsection/get/<id>", methods=["GET"])
def get_stepsection_by_id(id):
    record = db.session.query(Stepsection).filter(Stepsection.id == id).first()
    return jsonify(stepsection_schema.dump(record))

@app.route("/stepsection/update/<id>", methods=["PUT"])
def update_stepsection(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    title = data.get("title")

    record = db.session.query(Stepsection).filter(Stepsection.id == id).first()
    if title is not None:
        record.title = title

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Stepsection Updated",
        "data": stepsection_schema.dump(record)
    })

@app.route("/stepsection/delete/<id>", methods=["DELETE"])
def delete_stepsection(id):
    record = db.session.query(Stepsection).filter(Stepsection.id == id).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "Stepsection Deleted",
        "data": stepsection_schema.dump(record)
    })


@app.route("/step/add", methods=["POST"])
def add_step():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    number = data.get("number")
    text = data.get("text")
    recipe_id = data.get("recipe_id")
    stepsection_id = data.get("stepsection_id")

    record = Step(number, text, recipe_id, stepsection_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Step Added",
        "data": step_schema.dump(record)
    })

@app.route("/step/add/multiple", methods=["POST"])
def add_multiple_steps():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    records = []
    for data in data:
        number = data.get("number")
        text = data.get("text")
        recipe_id = data.get("recipe_id")
        stepsection_id = data.get("stepsection_id")

        record = Step(number, text, recipe_id, stepsection_id)
        db.session.add(record)
        db.session.commit()

        records.append(record)

    return jsonify({
        "status": 200,
        "message": "Steps Added",
        "data": multiple_step_schema.dump(records)
    })

@app.route("/step/get", methods=["GET"])
def get_all_steps():
    records = db.session.query(Step).all()
    return jsonify(multiple_step_schema.dump(records))

@app.route("/step/get/<id>", methods=["GET"])
def get_step_by_id(id):
    record = db.session.query(Step).filter(Step.id == id).first()
    return jsonify(step_schema.dump(record))

@app.route("/step/update/<id>", methods=["PUT"])
def update_step(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    number = data.get("number")
    text = data.get("text")

    record = db.session.query(Step).filter(Step.id == id).first()
    if number is not None:
        record.number = number
    if text is not None:
        record.text = text

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Step Updated",
        "data": step_schema.dump(record)
    })

@app.route("/step/delete/<id>", methods=["DELETE"])
def delete_step(id):
    record = db.session.query(Step).filter(Step.id == id).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "Step Deleted",
        "data": step_schema.dump(record)
    })


@app.route("/ingredientsection/add", methods=["POST"])
def add_ingredientsection():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    title = data.get("title")
    recipe_id = data.get("recipe_id")

    record = Ingredientsection(title, recipe_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Ingredientsection Added",
        "data": ingredientsection_schema.dump(record)
    })

@app.route("/ingredientsection/add/multiple", methods=["POST"])
def add_multiple_ingredientsections():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    records = []
    for data in data:
        title = data.get("title")
        recipe_id = data.get("recipe_id")

        record = Ingredientsection(title, recipe_id)
        db.session.add(record)
        db.session.commit()

        records.append(record)

    return jsonify({
        "status": 200,
        "message": "Ingredientsections Added",
        "data": multiple_ingredientsection_schema.dump(records)
    })

@app.route("/ingredientsection/get", methods=["GET"])
def get_all_ingredientsections():
    records = db.session.query(Ingredientsection).all()
    return jsonify(multiple_ingredientsection_schema.dump(records))

@app.route("/ingredientsection/get/<id>", methods=["GET"])
def get_ingredientsection_by_id(id):
    record = db.session.query(Ingredientsection).filter(Ingredientsection.id == id).first()
    return jsonify(ingredientsection_schema.dump(record))

@app.route("/ingredientsection/update/<id>", methods=["PUT"])
def update_ingredientsection(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    title = data.get("title")

    record = db.session.query(Ingredientsection).filter(Ingredientsection.id == id).first()
    if title is not None:
        record.title = title

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Ingredientsection Updated",
        "data": ingredientsection_schema.dump(record)
    })

@app.route("/ingredientsection/delete/<id>", methods=["DELETE"])
def delete_ingredientsection(id):
    record = db.session.query(Ingredientsection).filter(Ingredientsection.id == id).first()
    db.session.delete(record)
    db.session.commit()

    for ingredient in record.ingredients:
        for shoppingingredient in ingredient.shoppingingredients:
            db.session.delete(shoppingingredient)
            db.session.commit()
            socketio.emit("shoppingingredient-update", {
                "data": shoppingingredient_schema.dump(shoppingingredient),
                "type": "delete"
            })

    return jsonify({
        "status": 200,
        "message": "Ingredientsection Deleted",
        "data": ingredientsection_schema.dump(record)
    })


@app.route("/ingredient/add", methods=["POST"])
def add_ingredient():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    amount = data.get("amount")
    unit = data.get("unit")
    category = data.get("category")
    recipe_id = data.get("recipe_id")
    ingredientsection_id = data.get("ingredientsection_id")

    record = Ingredient(name, amount, unit, category, recipe_id, ingredientsection_id)
    db.session.add(record)
    db.session.commit()

    meal = db.session.query(Meal).join(Recipe).filter(Recipe.id == record.recipe_id).first()
    for mealplan in meal.mealplans:
        if mealplan.shoppinglists is not None:
            shoppinglist = mealplan_schema.dump(mealplan)["shoppinglist"]
            multiplier =  reduce(lambda lowest, next_ingredient: lowest if lowest < next_ingredient["multiplier"] else next_ingredient["multiplier"], shoppinglist["shoppingingredients"], 1 if len(shoppinglist["shoppingingredients"]) == 0 else shoppinglist["shoppingingredients"][0]["multiplier"])
            shoppingingredient = Shoppingingredient(name, amount, unit, category, multiplier, meal.name, shoppinglist["id"], record.id)
            db.session.add(shoppingingredient)
            db.session.commit()
            socketio.emit("shared-shoppingingredient-update", {
                "data": shoppingingredient_schema.dump(shoppingingredient),
                "type": "add"
            })

    return jsonify({
        "status": 200,
        "message": "Ingredient Added",
        "data": ingredient_schema.dump(record)
    })

@app.route("/ingredient/add/multiple", methods=["POST"])
def add_multiple_ingredients():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    records = []
    for data in data:
        name = data.get("name")
        amount = data.get("amount")
        unit = data.get("unit")
        category = data.get("category")
        recipe_id = data.get("recipe_id")
        ingredientsection_id = data.get("ingredientsection_id")

        record = Ingredient(name, amount, unit, category, recipe_id, ingredientsection_id)
        db.session.add(record)
        db.session.commit()

        records.append(record)

        meal = db.session.query(Meal).join(Recipe).filter(Recipe.id == record.recipe_id).first()
        for mealplan in meal.mealplans:
            if mealplan.shoppinglists is not None:
                shoppinglist = mealplan_schema.dump(mealplan)["shoppinglist"]
                multiplier = reduce(lambda lowest, next_ingredient: lowest if lowest < next_ingredient["multiplier"] else next_ingredient["multiplier"], shoppinglist["shoppingingredients"], 1 if len(shoppinglist["shoppingingredients"]) == 0 else shoppinglist["shoppingingredients"][0]["multiplier"])
                shoppingingredient = Shoppingingredient(name, amount, unit, category, multiplier, meal.name, shoppinglist["id"], record.id)
                db.session.add(shoppingingredient)
                db.session.commit()
                socketio.emit("shared-shoppingingredient-update", {
                    "data": shoppingingredient_schema.dump(shoppingingredient),
                    "type": "add"
                })

    return jsonify({
        "status": 200,
        "message": "Ingredients Added",
        "data": multiple_ingredient_schema.dump(records)
    })

@app.route("/ingredient/get", methods=["GET"])
def get_all_ingredients():
    records = db.session.query(Ingredient).all()
    return jsonify(multiple_ingredient_schema.dump(records))

@app.route("/ingredient/get/<id>", methods=["GET"])
def get_ingredient_by_id(id):
    record = db.session.query(Ingredient).filter(Ingredient.id == id).first()
    return jsonify(ingredient_schema.dump(record))

@app.route("/ingredient/update/<id>", methods=["PUT"])
def update_ingredient(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    amount = data.get("amount")
    unit = data.get("unit")
    category = data.get("category")

    record = db.session.query(Ingredient).filter(Ingredient.id == id).first()
    if name is not None:
        record.name = name
        for shoppingingredient in record.shoppingingredients:
            shoppingingredient.name = name
            db.session.commit()
    if amount is not None:
        record.amount = amount
        for shoppingingredient in record.shoppingingredients:
            shoppingingredient.amount = amount
            db.session.commit()
    if unit is not None:
        record.unit = unit
        for shoppingingredient in record.shoppingingredients:
            shoppingingredient.unit = unit
            db.session.commit()
    if category is not None:
        record.category = category
        for shoppingingredient in record.shoppingingredients:
            shoppingingredient.category = category
            db.session.commit()

    for shoppingingredient in record.shoppingingredients:
        socketio.emit("shared-shoppingingredient-update", {
            "data": shoppingingredient_schema.dump(shoppingingredient),
            "type": "update"
        })

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Ingredient Updated",
        "data": ingredient_schema.dump(record)
    })

@app.route("/ingredient/delete/<id>", methods=["DELETE"])
def delete_ingredient(id):
    record = db.session.query(Ingredient).filter(Ingredient.id == id).first()
    db.session.delete(record)
    db.session.commit()

    for shoppingingredient in record.shoppingingredients:
        db.session.delete(shoppingingredient)
        db.session.commit()
        socketio.emit("shared-shoppingingredient-update", {
            "data": shoppingingredient_schema.dump(shoppingingredient),
            "type": "delete"
        })

    return jsonify({
        "status": 200,
        "message": "Ingredient Deleted",
        "data": ingredient_schema.dump(record)
    })


@app.route("/mealplan/add", methods=["POST"])
def add_mealplan():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    created_on = data.get("created_on")
    user_username = data.get("user_username")
    user_id = data.get("user_id")
    meals = data.get("meals")
    multipliers = data.get("multipliers", {})

    record = Mealplan(name, created_on, user_username, user_id)
    db.session.add(record)
    db.session.commit()

    shoppinglist = Shoppinglist(f"{name} Mealplan", created_on, False, False, user_username, user_id, record.id)
    db.session.add(shoppinglist)
    db.session.commit()

    for meal_id in meals:
        meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
        record.meals.append(meal)
        db.session.commit()

        for ingredient in meal.recipe[0].ingredients:
            shoppingingredient = Shoppingingredient(ingredient.name, ingredient.amount, ingredient.unit, ingredient.category, multipliers.get(str(meal.id), 1), meal.name, shoppinglist.id, ingredient.id)
            db.session.add(shoppingingredient)
            db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Mealplan Added",
        "data": mealplan_schema.dump(record)
    })

@app.route("/mealplan/share", methods=["POST"])
def share_mealplan():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    mealplan_id = data.get("mealplan_id")
    username = data.get("username")

    shared_mealplan = db.session.query(Mealplan).filter(Mealplan.id == mealplan_id).first()
    shared_user = db.session.query(User).filter(User.username == username).first()
    user = db.session.query(User).filter(User.id == shared_mealplan.user_id).first()

    if shared_user is None:
        return jsonify({
            "status": 400,
            "message": "User doesn't exist.",
            "data": {}
        })

    if not shared_user.settings[0].allow_nonfriend_sharing and not user in shared_user.friends:
        return jsonify({
            "status": 400,
            "message": f"Sorry, {shared_user.username} is only accepting shares from friends.",
            "data": {}
        })

    shared_user.shared_mealplans.append(shared_mealplan)
    db.session.commit()

    if len(shared_mealplan.shoppinglists) > 0:
        shared_mealplan_schema = mealplan_schema.dump(shared_mealplan)
        shoppinglist = db.session.query(Shoppinglist).filter(Shoppinglist.id == shared_mealplan_schema["shoppinglist"]["id"]).first()
        shared_user.shared_shoppinglists.append(shoppinglist)
        if len(shared_mealplan.shoppinglists) > 1:
            sub_shoppinglist = db.session.query(Shoppinglist).filter(Shoppinglist.id == shared_mealplan_schema["sub_shoppinglist"]["id"]).first()
            shared_user.shared_shoppinglists.append(sub_shoppinglist)
            db.session.commit()

    notification = Notification("mealplan", shared_mealplan.user_username, shared_mealplan.name, shared_user.id)
    db.session.add(notification)
    db.session.commit()

    socketio.emit("mealplan-share-update", {
        "data": {
            "mealplan": mealplan_schema.dump(shared_mealplan),
            "user": user_schema.dump(shared_user),
            "notification": notification_schema.dump(notification)
        },
        "type": "add"
    })

    return jsonify({
        "status": 200,
        "message": "Mealplan Shared",
        "data": {
            "mealplan": mealplan_schema.dump(shared_mealplan),
            "user": user_schema.dump(shared_user)
        }
    })

@app.route("/mealplan/meal/add", methods=["POST"])
def add_meal_to_mealplan():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    mealplan_id = data.get("mealplan_id")
    meal_id = data.get("meal_id")
    multiplier = data.get("multiplier", 1)

    record = db.session.query(Mealplan).filter(Mealplan.id == mealplan_id).first()
    meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
    
    record.meals.append(meal)
    db.session.commit()

    shoppinglist = mealplan_schema.dump(record)["shoppinglist"]
    for ingredient in meal.recipe[0].ingredients:
        shoppingingredient = Shoppingingredient(ingredient.name, ingredient.amount, ingredient.unit, ingredient.category, multiplier, meal.name, shoppinglist["id"], ingredient.id)
        db.session.add(shoppingingredient)
        db.session.commit()
        socketio.emit("shoppingingredient-update", {
            "data": shoppingingredient_schema.dump(shoppingingredient),
            "type": "add"
        })

    return jsonify({
        "status": 200,
        "message": "Meal added to mealplan",
        "data": {
            "mealplan": mealplan_schema.dump(record),
            "meal": meal_schema.dump(meal)
        }
    })

@app.route("/mealplan/get", methods=["GET"])
def get_all_mealplans():
    records = db.session.query(Mealplan).all()
    return jsonify(multiple_mealplan_schema.dump(records))

@app.route("/mealplan/get/<id>", methods=["GET"])
def get_mealplan_by_id(id):
    record = db.session.query(Mealplan).filter(Mealplan.id == id).first()
    return jsonify(mealplan_schema.dump(record))

@app.route("/mealplan/update/<id>", methods=["PUT"])
def update_mealplan(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")

    record = db.session.query(Mealplan).filter(Mealplan.id == id).first()
    if name is not None:
        record.name = name
        for shoppinglist in record.shoppinglists:
            shoppinglist.name = f"{name} Mealplan"

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Mealplan Updated",
        "data": mealplan_schema.dump(record)
    })

@app.route("/mealplan/delete/<id>", methods=["DELETE"])
def delete_mealplan(id):
    record = db.session.query(Mealplan).filter(Mealplan.id == id).first()
    for user in record.shared_users:
        user.shared_mealplans.remove(record)
        db.session.commit()
    db.session.delete(record)
    db.session.commit()

    shoppinglist = mealplan_schema.dump(record)["shoppinglist"]
    for meal in record.meals:
        for ingredient in meal.recipe[0].ingredients:
            for shoppingingredient in ingredient.shoppingingredients:
                if shoppingingredient.shoppinglist_id == shoppinglist["id"]:
                    db.session.delete(shoppingingredient)
                    db.session.commit()
                    socketio.emit("shoppingingredient-update", {
                        "data": shoppingingredient_schema.dump(shoppingingredient),
                        "type": "delete"
                    })

    return jsonify({
        "status": 200,
        "message": "Mealplan Deleted",
        "data": mealplan_schema.dump(record)
    })

@app.route("/mealplan/unshare/<id>/<user_id>", methods=["DELETE"])
def unshare_mealplan(id, user_id):
    record = db.session.query(Mealplan).filter(Mealplan.id == id).first()
    shared_user = db.session.query(User).filter(User.id == user_id).first()

    if shared_user.shared_mealplans.count(record) == 0:
        return jsonify({
                "status": 400,
                "message": "Error: Shared mealplan does not exist.",
                "data": {}
            })

    shared_user.shared_mealplans.remove(record)
    db.session.commit()

    if len(record.shoppinglists) > 0:
        for shoppinglist in record.shoppinglists:
            shared_user.shared_shoppinglists.remove(shoppinglist)
            db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Mealplan Share Deleted",
        "data":{
            "mealplan": mealplan_schema.dump(record),
            "user": user_schema.dump(shared_user)
        }
    })

@app.route("/mealplan/meal/delete", methods=["DELETE"])
def delete_meal_from_mealplan():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    mealplan_id = data.get("mealplan_id")
    meal_id = data.get("meal_id")

    record = db.session.query(Mealplan).filter(Mealplan.id == mealplan_id).first()
    meal = db.session.query(Meal).filter(Meal.id == meal_id).first()
    
    record.meals.remove(meal)
    db.session.commit()

    shoppinglist = mealplan_schema.dump(record)["shoppinglist"]
    for ingredient in meal.recipe[0].ingredients:
        for shoppingingredient in ingredient.shoppingingredients:
            if shoppingingredient.shoppinglist_id == shoppinglist["id"]:
                db.session.delete(shoppingingredient)
                db.session.commit()
                socketio.emit("shoppingingredient-update", {
                    "data": shoppingingredient_schema.dump(shoppingingredient),
                    "type": "delete"
                })

    return jsonify({
        "status": 200,
        "message": "Meal deleted from mealplan",
        "data": {
            "mealplan": mealplan_schema.dump(record),
            "meal": meal_schema.dump(meal)
        }
    })


@app.route("/mealplanoutline/add", methods=["POST"])
def add_mealplanoutline():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    number = data.get("number")
    user_id = data.get("user_id")

    record = Mealplanoutline(name, number, user_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Mealplanoutline Added",
        "data": mealplanoutline_schema.dump(record)
    })

@app.route("/mealplanoutline/get", methods=["GET"])
def get_all_mealplanoutlines():
    records = db.session.query(Mealplanoutline).all()
    return jsonify(multiple_mealplanoutline_schema.dump(records))

@app.route("/mealplanoutline/get/<id>", methods=["GET"])
def get_mealplanoutline_by_id(id):
    record = db.session.query(Mealplanoutline).filter(Mealplanoutline.id == id).first()
    return jsonify(mealplanoutline_schema.dump(record))

@app.route("/mealplanoutline/update/<id>", methods=["PUT"])
def update_mealplanoutline(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    number = data.get("number")

    record = db.session.query(Mealplanoutline).filter(Mealplanoutline.id == id).first()
    if name is not None:
        record.name = name
    if number is not None:
        record.number = number

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Mealplanoutline Updated",
        "data": mealplanoutline_schema.dump(record)
    })

@app.route("/mealplanoutline/delete/<id>", methods=["DELETE"])
def delete_mealplanoutline(id):
    record = db.session.query(Mealplanoutline).filter(Mealplanoutline.id == id).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "Mealplanoutline Deleted",
        "data": mealplanoutline_schema.dump(record)
    })


@app.route("/rule/add", methods=["POST"])
def add_rule():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    rule_type = data.get("rule_type")
    rule = data.get("rule")
    amount = data.get("amount")
    value = data.get("value")
    mealplan_id = data.get("mealplan_id")
    mealplanoutline_id = data.get("mealplanoutline_id")

    record = Rule(rule_type, rule, amount, value, mealplan_id, mealplanoutline_id)
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Rule Added",
        "data": rule_schema.dump(record)
    })

@app.route("/rule/get", methods=["GET"])
def get_all_rules():
    records = db.session.query(Rule).all()
    return jsonify(multiple_rule_schema.dump(records))

@app.route("/rule/get/<id>", methods=["GET"])
def get_rule_by_id(id):
    record = db.session.query(Rule).filter(Rule.id == id).first()
    return jsonify(rule_schema.dump(record))

@app.route("/rule/update/<id>", methods=["PUT"])
def update_rule(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    rule_type = data.get("rule_type")
    rule = data.get("rule")
    amount = data.get("amount")
    value = data.get("value")

    record = db.session.query(Rule).filter(Rule.id == id).first()
    if rule_type is not None:
        record.rule_type = rule_type
    if rule is not None:
        record.rule = rule
    if amount is not None:
        record.amount = amount
    if value is not None:
        record.value = value

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Rule Updated",
        "data": rule_schema.dump(record)
    })

@app.route("/rule/delete/<id>", methods=["DELETE"])
def delete_rule(id):
    record = db.session.query(Rule).filter(Rule.id == id).first()
    db.session.delete(record)
    db.session.commit()
    return jsonify({
        "status": 200,
        "message": "Rule Deleted",
        "data": rule_schema.dump(record)
    })


@app.route("/shoppinglist/add", methods=["POST"])
def add_shoppinglist():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    created_on = data.get("created_on")
    updates_hidden = data.get("updates_hidden")
    is_sublist = data.get("is_sublist", False)
    user_username = data.get("user_username")
    user_id = data.get("user_id")
    mealplan_id = data.get("mealplan_id")

    record = Shoppinglist(name, created_on, updates_hidden, is_sublist, user_username, user_id, mealplan_id)
    db.session.add(record)
    db.session.commit()

    if mealplan_id is not None:
        mealplan = db.session.query(Mealplan).filter(Mealplan.id == mealplan_id).first()
        for user in mealplan.shared_users:
            user.shared_shoppinglists.append(record)
            db.session.commit()

            socketio.emit("shoppinglist-share-update", {
                "data": {
                    "shoppinglist": shoppinglist_schema.dump(record),
                    "user": user_schema.dump(user),
                    "notification": {}
                },
                "type": "add"
            })

    return jsonify({
        "status": 200,
        "message": "Shoppinglist Added",
        "data": shoppinglist_schema.dump(record)
    })

@app.route("/shoppinglist/share", methods=["POST"])
def share_shoppinglist():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    shoppinglist_id = data.get("shoppinglist_id")
    username = data.get("username")

    shared_shoppinglist = db.session.query(Shoppinglist).filter(Shoppinglist.id == shoppinglist_id).first()
    shared_user = db.session.query(User).filter(User.username == username).first()
    user = db.session.query(User).filter(User.id == shared_shoppinglist.user_id).first()

    if shared_user is None:
        return jsonify({
            "status": 400,
            "message": "User doesn't exist.",
            "data": {}
        })

    if not shared_user.settings[0].allow_nonfriend_sharing and not user in shared_user.friends:
        return jsonify({
            "status": 400,
            "message": f"Sorry, {shared_user.username} is only accepting shares from friends.",
            "data": {}
        })

    shared_user.shared_shoppinglists.append(shared_shoppinglist)
    db.session.commit()

    notification = Notification("shoppinglist", shared_shoppinglist.user_username, shared_shoppinglist.name, shared_user.id)
    db.session.add(notification)
    db.session.commit()

    socketio.emit("shoppinglist-share-update", {
        "data": {
            "shoppinglist": shoppinglist_schema.dump(shared_shoppinglist),
            "user": user_schema.dump(shared_user),
            "notification": notification_schema.dump(notification)
        },
        "type": "add"
    })

    return jsonify({
        "status": 200,
        "message": "Shoppinglist Shared",
        "data": {
            "shoppinglist": shoppinglist_schema.dump(shared_shoppinglist),
            "user": user_schema.dump(shared_user)
        }
    })

@app.route("/shoppinglist/get", methods=["GET"])
def get_all_shoppinglists():
    records = db.session.query(Shoppinglist).all()
    return jsonify(multiple_shoppinglist_schema.dump(records))

@app.route("/shoppinglist/get/<id>", methods=["GET"])
def get_shoppinglist_by_id(id):
    record = db.session.query(Shoppinglist).filter(Shoppinglist.id == id).first()
    return jsonify(shoppinglist_schema.dump(record))

@app.route("/shoppinglist/update/<id>", methods=["PUT"])
def update_shoppinglist(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    updates_hidden = data.get("updates_hidden")

    record = db.session.query(Shoppinglist).filter(Shoppinglist.id == id).first()
    if name is not None:
        record.name = name
    if updates_hidden is not None:
        record.updates_hidden = updates_hidden

    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Shoppinglist Updated",
        "data": shoppinglist_schema.dump(record)
    })

@app.route("/shoppinglist/delete/<id>", methods=["DELETE"])
def delete_shoppinglist(id):
    record = db.session.query(Shoppinglist).filter(Shoppinglist.id == id).first()
    for user in record.shared_users:
        user.shared_shoppinglists.remove(record)
        db.session.commit()
    db.session.delete(record)
    db.session.commit()

    if record.mealplan_id is not None:
        mealplan = db.session.query(Mealplan).filter(Mealplan.id == record.mealplan_id).first()
        for user in mealplan.shared_users:
            socketio.emit("shoppinglist-share-update", {
                "data": {
                    "shoppinglist": shoppinglist_schema.dump(record),
                    "user": user_schema.dump(user),
                    "notification": {}
                },
                "type": "delete"
            })

    return jsonify({
        "status": 200,
        "message": "Shoppinglist Deleted",
        "data": shoppinglist_schema.dump(record)
    })

@app.route("/shoppinglist/unshare/<id>/<user_id>", methods=["DELETE"])
def unshare_shoppinglist(id, user_id):
    record = db.session.query(Shoppinglist).filter(Shoppinglist.id == id).first()
    shared_user = db.session.query(User).filter(User.id == user_id).first()

    if shared_user.shared_shoppinglists.count(record) == 0:
        return jsonify({
                "status": 400,
                "message": "Error: Shared shoppinglist does not exist.",
                "data": {}
            })

    shared_user.shared_shoppinglists.remove(record)
    db.session.commit()

    return jsonify({
        "status": 200,
        "message": "Shoppinglist Share Deleted",
        "data":{
            "shoppinglist": shoppinglist_schema.dump(record),
            "user": user_schema.dump(shared_user)
        }
    })


@app.route("/shoppingingredient/add", methods=["POST"])
def add_shoppingingredient():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    amount = data.get("amount")
    unit = data.get("unit")
    category = data.get("category")
    multiplier = data.get("multiplier", 1)
    meal_name = data.get("meal_name")
    shoppinglist_id = data.get("shoppinglist_id")
    ingredient_id = data.get("ingredient_id")

    record = Shoppingingredient(name, amount, unit, category, multiplier, meal_name, shoppinglist_id, ingredient_id)
    db.session.add(record)
    db.session.commit()

    socketio.emit("shoppingingredient-update", {
        "data": shoppingingredient_schema.dump(record),
        "type": "add"
    })

    return jsonify({
        "status": 200,
        "message": "Shoppingingredient Added",
        "data": shoppingingredient_schema.dump(record)
    })

@app.route("/shoppingingredient/add/multiple", methods=["POST"])
def add_multiple_shoppingingredients():
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    records = []
    for data in data:
        name = data.get("name")
        amount = data.get("amount")
        unit = data.get("unit")
        category = data.get("category")
        multiplier = data.get("multiplier", 1)
        meal_name = data.get("meal_name")
        shoppinglist_id = data.get("shoppinglist_id")
        ingredient_id = data.get("ingredient_id")

        record = Shoppingingredient(name, amount, unit, category, multiplier, meal_name, shoppinglist_id, ingredient_id)
        db.session.add(record)
        db.session.commit()

        records.append(record)

    socketio.emit("shoppingingredient-update-multiple", {
        "data": multiple_shoppingingredient_schema.dump(records),
        "type": "add"
    })

    return jsonify({
        "status": 200,
        "message": "Shoppingingredients Added",
        "data": multiple_shoppingingredient_schema.dump(records)
    })

@app.route("/shoppingingredient/get", methods=["GET"])
def get_all_shoppingingredients():
    records = db.session.query(Shoppingingredient).all()
    return jsonify(multiple_shoppingingredient_schema.dump(records))

@app.route("/shoppingingredient/get/<id>", methods=["GET"])
def get_shoppingingredient_by_id(id):
    record = db.session.query(Shoppingingredient).filter(Shoppingingredient.id == id).first()
    return jsonify(ingredient_schema.dump(record))

@app.route("/shoppingingredient/update/<id>", methods=["PUT"])
def update_shoppingingredient(id):
    if request.content_type != "application/json":
        return jsonify({
            "status": 400,
            "message": "Error: Data must be sent as JSON.",
            "data": {}
        })

    data = request.get_json()
    name = data.get("name")
    amount = data.get("amount")
    unit = data.get("unit")
    category = data.get("category")
    multiplier = data.get("multiplier")
    obtained = data.get("obtained")
    meal_name = data.get("meal_name")

    record = db.session.query(Shoppingingredient).filter(Shoppingingredient.id == id).first()
    if name is not None:
        record.name = name
    if amount is not None:
        record.amount = amount
    if unit is not None:
        record.unit = unit
    if category is not None:
        record.category = category
    if multiplier is not None:
        record.multiplier = multiplier
    if obtained is not None:
        record.obtained = obtained
    if meal_name is not None:
        record.meal_name = meal_name

    db.session.commit()
    
    if obtained is not None:
        socketio.emit("shared-shoppingingredient-update", {
            "data": shoppingingredient_schema.dump(record),
            "type": "update"
        })
    else:
        socketio.emit("shoppingingredient-update", {
            "data": shoppingingredient_schema.dump(record),
            "type": "update"
        })

    return jsonify({
        "status": 200,
        "message": "Shoppingingredient Updated",
        "data": shoppingingredient_schema.dump(record)
    })

@app.route("/shoppingingredient/delete/<id>", methods=["DELETE"])
def delete_shoppingingredient(id):
    record = db.session.query(Shoppingingredient).filter(Shoppingingredient.id == id).first()
    db.session.delete(record)
    db.session.commit()

    socketio.emit("shoppingingredient-update", {
        "data": shoppingingredient_schema.dump(record),
        "type": "delete"
    })

    return jsonify({
        "status": 200,
        "message": "Shoppingingredient Deleted",
        "data": shoppingingredient_schema.dump(record)
    })

if __name__ == "__main__":
    socketio.run(app, debug=True)