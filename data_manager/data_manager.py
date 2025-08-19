"""DataManager
--------------
Provides a thin abstraction around SQLAlchemy ORM for CRUD operations on
Users and Movies. Centralizing DB access here keeps route functions simple.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from models.models import Movie, User


class DataManager:
    """High-level CRUD convenience methods for Users and Movies."""

    def __init__(self, database):
        """Create a new DataManager.

        Args:
            database: The SQLAlchemy `db` object.
        """
        self.db = database

    # ------------------------- Users -------------------------
    def create_user(self, name: str) -> User:
        """Create and persist a new user.

        Args:
            name: The new user's name (must be unique and non-empty).

        Returns:
            User: The persisted User instance.

        Raises:
            ValueError: If name is empty or user already exists.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("User name cannot be empty.")

        user = User(name=name)
        self.db.session.add(user)
        try:
            self.db.session.commit()
        except IntegrityError:
            self.db.session.rollback()
            raise ValueError(f'User "{name}" already exists.')

        return user

    def get_users(self) -> List[User]:
        """Return all users ordered by name ascending."""
        return User.query.order_by(User.name.asc()).all()

    def get_user(self, user_id: int) -> Optional[User]:
        """Return a single user by primary key."""
        return User.query.get(user_id)

    # ------------------------- Movies ------------------------
    def get_movies(self, user_id: int) -> List[Movie]:
        """Return all movies for the given user ordered by title ascending."""
        return (
            Movie.query.filter_by(user_id=user_id)
            .order_by(Movie.title.asc())
            .all()
        )

    def get_movie(self, movie_id: int) -> Optional[Movie]:
        """Return a single movie by primary key."""
        return Movie.query.get(movie_id)

    def add_movie(
        self,
        *,
        user_id: int,
        title: str,
        director: Optional[str] = None,
        year: Optional[int] = None,
        poster_url: Optional[str] = None,
    ) -> Movie:
        """Add a movie for a user (enforces per-user unique title).

        Args:
            user_id: Owner user ID.
            title: Movie title (required).
            director: Director name (optional).
            year: Release year (optional).
            poster_url: Poster image URL (optional).

        Returns:
            Movie: The persisted Movie instance.

        Raises:
            ValueError: If title is empty, user doesn't exist, or duplicate.
        """
        title = (title or "").strip()
        if not title:
            raise ValueError("Movie title cannot be empty.")

        user = User.query.get(user_id)
        if not user:
            raise ValueError("User does not exist.")

        movie = Movie(
            title=title,
            director=director,
            year=year,
            poster_url=poster_url,
            user=user,
        )
        self.db.session.add(movie)
        try:
            self.db.session.commit()
        except IntegrityError:
            self.db.session.rollback()
            raise ValueError("This user already has a movie with that title.")

        return movie

    def update_movie(self, movie_id: int, **fields) -> Movie:
        """Update fields on a movie and persist the changes.

        Args:
            movie_id: The movie's primary key.
            **fields: Any of: title, director, year, poster_url.

        Returns:
            Movie: The updated Movie instance.

        Raises:
            ValueError: If movie not found or duplicate constraint violated.
        """
        movie = Movie.query.get(movie_id)
        if not movie:
            raise ValueError("Movie not found.")

        allowed = {"title", "director", "year", "poster_url"}
        for key, value in list(fields.items()):
            if key not in allowed:
                fields.pop(key)
        if "title" in fields and not (fields["title"] or "").strip():
            raise ValueError("Title cannot be empty.")

        for key, value in fields.items():
            setattr(movie, key, value)

        try:
            self.db.session.commit()
        except IntegrityError:
            self.db.session.rollback()
            raise ValueError("Duplicate movie title for this user.")
        return movie

    def delete_movie(self, movie_id: int) -> None:
        """Delete a movie by primary key.

        Args:
            movie_id: The movie to delete.

        Raises:
            ValueError: If the movie does not exist.
        """
        movie = Movie.query.get(movie_id)
        if not movie:
            raise ValueError("Movie not found.")
        self.db.session.delete(movie)
        self.db.session.commit()