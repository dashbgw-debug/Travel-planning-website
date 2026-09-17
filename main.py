from random import choices

from sqlalchemy.util.langhelpers import repr_tuple_names
from werkzeug import security
import sqlalchemy
import requests
from flask import Flask, render_template, session, request, redirect, url_for
from flask_bootstrap import Bootstrap
from sqlalchemy import create_engine, String, Table, insert, select, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase, Session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user, login_remembered

import os
from dotenv import load_dotenv
load_dotenv()

login_manager = LoginManager()

CITY_NAMES_API_KEY = os.getenv('CITY_NAMES_API_KEY')
CITY_NAMES_HEADERS = {'X-CSCAPI-KEY': CITY_NAMES_API_KEY}


app = Flask(__name__)
bootstrap = Bootstrap(app)
app.secret_key = os.getenv('SECRET_KEY')

class Base(DeclarativeBase):
    pass

class User(Base, UserMixin):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(String(50))
    password: Mapped[str] = mapped_column(String(50))
    cities: Mapped[list["City"]] = relationship(back_populates='user')


class City(Base):
    __tablename__ = "Cities"
    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    city: Mapped[str] = mapped_column(String(50))
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="cities")


db = sqlalchemy.create_engine('sqlite:///users.db', echo=True)
Base.metadata.create_all(db)
session = Session(db)


login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    stmt = select(User).where(User.id == user_id)
    user = session.execute(stmt).scalars().first()
    return user



@app.route("/")
def home():
    if login_user(current_user):
        return redirect(url_for('hub'))
    return render_template('index.html')

@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        stmt = select(User).where(User.username == username)
        user = session.execute(stmt).scalars().first()
        if user:
            return redirect(url_for('login'))
        else:
            new_user = User(
                username=username,
                password=security.generate_password_hash(password, method='pbkdf2', salt_length=10))
            session.add(new_user)
            session.commit()
            login_user(new_user)
            return redirect(url_for('hub'))
    return render_template('signup.html')


@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        stmt = select(User).where(User.username == username)
        user = session.execute(stmt).scalars().first()
        if user:
            if security.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('hub'))
    return render_template('login.html')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/account_hub")
@login_required
def hub():
    all_cities = session.scalars(select(City)).all()
    return render_template('hub.html', all_cities=all_cities)


@app.route("/choose_state")
@login_required
def choose_state():
    response = requests.get(url='https://api.countrystatecity.in/v1/countries/US/states', headers=CITY_NAMES_HEADERS)
    states = response.json()
    return render_template('choose_state.html', choices=states)

@app.route('/choose_city/<state>')
@login_required
def choose_city(state):
    response = requests.get(url=f'https://api.countrystatecity.in/v1/countries/US/states/{state}/cities', headers=CITY_NAMES_HEADERS)
    cities = response.json()
    return render_template('choose_city.html', choices=cities)


if __name__ == '__main__':
    app.run(debug=True)