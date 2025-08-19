"""MoviWebApp
----------------
A Flask web application that lets users register and manage a list of
favorite movies. Movie info is fetched from the OMDb API.

Features:
    - Register/select users
    - List, add, update, and delete movies for a user
    - Fetch movie metadata (title, director, year, poster) from OMDb
    - Basic error handling and flash messages
    - Jinja2 templates and a simple CSS stylesheet

Run locally:
    1) Create and activate a virtualenv
    2) pip install -r requirements.txt
    3) Copy .env.example to .env and set OMDB_API_KEY (optional but recommended)
    4) python app.py
    5) Visit http://127.0.0.1:5000

Note:
    For simplicity this app stores data in a local SQLite database file
    under the ./data directory.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from data_manager.data_manager import DataManager
from models.models import db, init_db, Movie, User  # noqa: F401  (imported for typing/metadata)
from omdb_movie.omdb import fetch_omdb_by_title

# ---------------------------------------------------------------------------
# Flask app configuration
# ---------------------------------------------------------------------------

load_dotenv()  # Load environment variables from .env if present

BASEDIR = Path(__file__).parent.resolve()
DATA_DIR = BASEDIR / "data"
DATA_DIR.mkdir(exist_ok=True)



def register_error_handlers(app: Flask) -> None:
    """Register error handlers for common HTTP errors.

    Args:
        app: The Flask application.
    """

    @app.errorhandler(404)
    def page_not_found(error):  # type: ignore[override]
        """Render a custom 404 page.

        Args:
            error: Exception information (unused).

        Returns:
            tuple: (rendered template, status code 404)
        """
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):  # type: ignore[override]
        """Render a custom 500 page.

        Args:
            error: Exception information (unused).

        Returns:
            tuple: (rendered template, status code 500)
        """
        return render_template("500.html"), 500


def register_routes(app: Flask) -> None:
    """Attach route functions to the app.

    Args:
        app: The Flask application.
    """

    @app.route("/", methods=["GET"])
    def index():
        """Home page: list all users and show an add-user form.

        Query Parameters:
            none

        Returns:
            Response: Rendered index template with list of users.
        """
        users = app.data_manager.get_users()
        return render_template("index.html", users=users)

    @app.route("/users", methods=["POST"])
    def create_user():
        """Create a new user from the submitted form data.

        Form Data:
            name (str): Required username.

        Returns:
            Response: Redirect back to the home page.
        """
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("index"))

        try:
            app.data_manager.create_user(name)
            flash(f"User “{name}” created!", "success")
        except ValueError as exc:
            # DataManager raises ValueError for duplicates, etc.
            flash(str(exc), "error")

        return redirect(url_for("index"))

    @app.route("/users/<int:user_id>/movies", methods=["GET"])
    def list_movies(user_id: int):
        """List all movies for a given user.

        Args:
            user_id: The selected user's ID.

        Returns:
            Response: Rendered movies template for that user.
        """
        user = app.data_manager.get_user(user_id)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("index"))

        movies = app.data_manager.get_movies(user_id)
        return render_template("movies.html", user=user, movies=movies)

    @app.route("/users/<int:user_id>/movies", methods=["POST"])
    def add_movie(user_id: int):
        """Add a new movie to the user's favorites.

        Form Data:
            title (str): The movie title to search on OMDb.

        Behavior:
            - Fetches metadata from OMDb using the provided title.
            - Stores title, director, year, poster_url.
            - Shows flash messages on success/failure.

        Returns:
            Response: Redirect to the user's movies page.
        """
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Movie title is required.", "error")
            return redirect(url_for("list_movies", user_id=user_id))

        try:
            info = fetch_omdb_by_title(title)
        except Exception as exc:  # Broad except to surface network/key issues
            flash(f"Failed to fetch movie info: {exc}", "error")
            return redirect(url_for("list_movies", user_id=user_id))

        if not info or info.get("Response") == "False":
            flash(f"No OMDb results for “{title}”.", "error")
            return redirect(url_for("list_movies", user_id=user_id))

        # Extract fields with safe defaults
        director = info.get("Director") or "Unknown"
        year_str = (info.get("Year") or "").split("–")[0].strip()
        try:
            year: Optional[int] = int(year_str) if year_str.isdigit() else None
        except ValueError:
            year = None

        poster_url = info.get("Poster") if info.get("Poster") not in (None, "N/A") else None

        # Upsert (prevent duplicate titles for the same user)
        try:
            app.data_manager.add_movie(
                user_id=user_id,
                title=info.get("Title") or title,
                director=director,
                year=year,
                poster_url=poster_url,
            )
            flash(f"Added “{info.get('Title') or title}”.", "success")
        except ValueError as exc:
            flash(str(exc), "error")

        return redirect(url_for("list_movies", user_id=user_id))

    @app.route(
        "/users/<int:user_id>/movies/<int:movie_id>/update", methods=["POST"]
    )
    def update_movie(user_id: int, movie_id: int):
        """Update a movie. Optionally refetch data from OMDb.

        Form Data:
            title (str): New title to set (optional).
            refetch (str): "on" to trigger re-fetch from OMDb (optional).

        Returns:
            Response: Redirect to user's movie list.
        """
        title = (request.form.get("title") or "").strip()
        refetch = request.form.get("refetch") == "on"

        movie = app.data_manager.get_movie(movie_id)
        if not movie or movie.user_id != user_id:
            flash("Movie not found.", "error")
            return redirect(url_for("list_movies", user_id=user_id))

        new_data = {}
        if title:
            new_data["title"] = title

        if refetch or title:
            try:
                info = fetch_omdb_by_title(title or movie.title)
                if info and info.get("Response") != "False":
                    new_data["title"] = info.get("Title") or new_data.get("title", movie.title)
                    new_data["director"] = info.get("Director") or movie.director
                    year_str = (info.get("Year") or "").split("–")[0].strip()
                    if year_str.isdigit():
                        new_data["year"] = int(year_str)
                    poster_url = info.get("Poster")
                    new_data["poster_url"] = None if poster_url in (None, "N/A") else poster_url
            except Exception as exc:
                flash(f"OMDb fetch failed: {exc}", "error")

        try:
            app.data_manager.update_movie(movie_id, **new_data)
            flash("Movie updated.", "success")
        except ValueError as exc:
            flash(str(exc), "error")

        return redirect(url_for("list_movies", user_id=user_id))

    @app.route(
        "/users/<int:user_id>/movies/<int:movie_id>/delete", methods=["POST"]
    )
    def delete_movie(user_id: int, movie_id: int):
        """Delete a movie from a user's list.

        Args:
            user_id: The owning user's ID (for redirect).
            movie_id: The movie's ID to delete.

        Returns:
            Response: Redirect to user's movie list.
        """
        try:
            app.data_manager.delete_movie(movie_id)
            flash("Movie deleted.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("list_movies", user_id=user_id))






def create_app() -> Flask:
    """Application factory to create and configure the Flask app.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATA_DIR / 'moviweb.sqlite3'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize DB and DataManager
    init_db(app)
    app.data_manager = DataManager(db)  # type: ignore[attr-defined]

    # Register error handlers
    register_error_handlers(app)

    # Register routes
    register_routes(app)

    return app

app = create_app()



# --------------------------- Minimal JSON API ---------------------------
@app.route("/api/users", methods=["GET"])
def api_users():
    """Return all users as JSON (id, name)."""
    users = [{"id": u.id, "name": u.name} for u in app.data_manager.get_users()]
    return {"users": users}, 200


@app.route("/api/users", methods=["POST"])
def api_create_user():
    """Create a user from JSON payload: { "name": "Alice" }"""
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return {"error": "name is required"}, 400
    try:
        user = app.data_manager.create_user(name)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    return {"id": user.id, "name": user.name}, 201


@app.route("/api/users/<int:user_id>/movies", methods=["GET"])
def api_user_movies(user_id: int):
    """Return all movies for a user as JSON."""
    user = app.data_manager.get_user(user_id)
    if not user:
        return {"error": "user not found"}, 404
    movies = [
        {
            "id": m.id,
            "title": m.title,
            "director": m.director,
            "year": m.year,
            "poster_url": m.poster_url,
        }
        for m in app.data_manager.get_movies(user_id)
    ]
    return {"user": {"id": user.id, "name": user.name}, "movies": movies}, 200


@app.route("/api/users/<int:user_id>/movies", methods=["POST"])
def api_add_movie(user_id: int):
    """Add a movie to a user via JSON payload: {"title": "..."}"""
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return {"error": "title is required"}, 400
    try:
        info = fetch_omdb_by_title(title)
    except Exception as exc:
        return {"error": f"OMDb request failed: {exc}"}, 502
    if not info or info.get("Response") == "False":
        return {"error": f'no results for "{title}"'}, 404

    director = info.get("Director") or "Unknown"
    year_str = (info.get("Year") or "").split("–")[0].strip()
    year = int(year_str) if year_str.isdigit() else None
    poster_url = info.get("Poster") if info.get("Poster") not in (None, "N/A") else None

    try:
        m = app.data_manager.add_movie(
            user_id=user_id,
            title=info.get("Title") or title,
            director=director,
            year=year,
            poster_url=poster_url,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 400

    return {
        "id": m.id,
        "title": m.title,
        "director": m.director,
        "year": m.year,
        "poster_url": m.poster_url,
    }, 201


@app.route("/api/movies/<int:movie_id>", methods=["PUT", "PATCH"])
def api_update_movie(movie_id: int):
    """Update a movie by id. JSON body can include title, director, year, poster_url."""
    payload = request.get_json(silent=True) or {}
    try:
        m = app.data_manager.update_movie(movie_id, **payload)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    return {
        "id": m.id,
        "title": m.title,
        "director": m.director,
        "year": m.year,
        "poster_url": m.poster_url,
    }, 200


@app.route("/api/movies/<int:movie_id>", methods=["DELETE"])
def api_delete_movie(movie_id: int):
    """Delete a movie by id."""
    try:
        app.data_manager.delete_movie(movie_id)
    except ValueError as exc:
        return {"error": str(exc)}, 404
    return "", 204



@app.route("/users/<int:user_id>", methods=["GET"])
def user_redirect(user_id: int):
    """Compatibility route that redirects /users/<id> to the movies view."""
    return redirect(url_for("list_movies", user_id=user_id))


@app.route("/select_user", methods=["POST"])
def select_user():
    """Handle the user selection form from the index page.

    Form Data:
        user_id (int): Selected user to view.

    Returns:
        Response: Redirect to that user's movies page.
    """
    raw = (request.form.get("user_id") or "").strip()
    try:
        user_id = int(raw)
    except (TypeError, ValueError):
        flash("Please select a valid user.", "error")
        return redirect(url_for("index"))
    return redirect(url_for("list_movies", user_id=user_id))


if __name__ == "__main__":
    app.run(debug=True)