"""Database models for MoviWebApp.

Defines SQLAlchemy ORM models for User and Movie, and helpers to initialize
the database within a Flask application.
"""
from __future__ import annotations

from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from flask import Flask

db = SQLAlchemy()


class User(db.Model):
    """User model representing a person maintaining a list of favorite movies."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    movies = db.relationship(
        "Movie",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - for debugging
        return f"<User id={self.id} name={self.name!r}>"


class Movie(db.Model):
    """Movie model storing a single favorite movie linked to a user."""

    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    director = db.Column(db.String(255))
    year = db.Column(db.Integer)
    poster_url = db.Column(db.String(500))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", back_populates="movies", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("user_id", "title", name="uq_user_movie_title"),
    )

    def __repr__(self) -> str:  # pragma: no cover - for debugging
        return f"<Movie id={self.id} title={self.title!r} user_id={self.user_id}>"


def init_db(app: Flask) -> None:
    """Bind the SQLAlchemy db to the app and create tables if needed.

    Args:
        app: The Flask application to bind to.
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()