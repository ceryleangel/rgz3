from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, login_required, current_user, logout_user, LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "123"
user_db = "arina"
host_ip = "127.0.0.1"
host_port = "5432"
database_name = "ttt"
password = "123"

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user_db}:{password}@{host_ip}:{host_port}/{database_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.init_app(app)

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Переименование таблицы

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Recipe(db.Model):
    __tablename__ = 'recipes'  # Указание имени таблицы

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    steps = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(300), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    recipes = Recipe.query.offset(offset).limit(per_page).all()
    total_recipes = Recipe.query.count()
    return render_template('index.html', recipes=recipes, page=page, per_page=per_page, total_recipes=total_recipes)

@app.route('/search', methods=['GET', 'POST'])
def search():
    query = request.args.get('query', '')
    mode = request.args.get('mode', 'any')
    page = request.args.get('page', 1, type=int)  # Получаем текущую страницу из параметров запроса
    per_page = 10  # Количество рецептов на страницу

    recipes_query = Recipe.query

    if query:
        if mode == 'all':
            ingredients = query.split(',')
            for ingredient in ingredients:
                recipes_query = recipes_query.filter(Recipe.ingredients.ilike(f"%{ingredient.strip()}%"))
        elif mode == 'any':
            recipes_query = recipes_query.filter(Recipe.ingredients.ilike(f"%{query}%"))

    total_recipes = recipes_query.count()  # Общее количество рецептов
    recipes = recipes_query.offset((page - 1) * per_page).limit(per_page).all()  # Пагинация

    return render_template(
        'search.html',
        recipes=recipes,
        query=query,
        mode=mode,
        page=page,  # Передаём текущую страницу в шаблон
        per_page=per_page,
        total_recipes=total_recipes
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        is_admin = request.form.get("is_admin") == 'on'

        if User.query.filter_by(username=username).first():
            flash("Пользователь с таким именем уже существует!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method="pbkdf2")
        new_user = User(username=username, password=hashed_password, is_admin=is_admin)

        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация прошла успешно!", "success")
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))

        flash("Неверное имя пользователя или пароль", "danger")

    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы успешно вышли из системы.", "success")
    return redirect(url_for('index'))

@app.route('/create_recipe', methods=['GET', 'POST'])
@login_required
def create_recipe():
    if not current_user.is_admin:
        flash("Доступ запрещён!", "danger")
        return redirect(url_for('index'))

    if request.method == "POST":
        title = request.form.get("title")
        ingredients = request.form.get("ingredients")
        steps = request.form.get("steps")
        photo_url = request.form.get("photo_url")

        new_recipe = Recipe(title=title, ingredients=ingredients, steps=steps, photo_url=photo_url)
        db.session.add(new_recipe)
        db.session.commit()
        flash("Рецепт успешно добавлен!", "success")
        return redirect(url_for('index'))

    return render_template("create_recipe.html")

@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    if not current_user.is_admin:
        flash("Доступ запрещён! Только администраторы могут редактировать рецепты.", "danger")
        return redirect(url_for('index'))

    # Получаем рецепт по ID
    recipe = Recipe.query.get_or_404(recipe_id)

    if request.method == 'POST':
        recipe.title = request.form['title']
        recipe.ingredients = request.form['ingredients']
        recipe.steps = request.form['steps']
        recipe.photo_url = request.form['photo_url']
        
        db.session.commit()
        flash("Рецепт успешно обновлён!", "success")
        return redirect(url_for('index'))

    return render_template('edit_recipe.html', recipe=recipe)


@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    if not current_user.is_admin:
        flash("Доступ запрещён!", "danger")
        return redirect(url_for('index'))

    recipe = Recipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    flash("Рецепт успешно удалён!", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
