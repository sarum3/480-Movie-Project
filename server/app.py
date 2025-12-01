from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import sqlite3
from pathlib import Path


def createDB():
    DATA_DIR = Path(__file__).parent
    RATINGS_SMALL_CSV = DATA_DIR / "ratings.csv"
    MOVIES_CSV = DATA_DIR / "movies_metadata.csv"
    DB_PATH = DATA_DIR / "movies.db"

    movies = pd.read_csv(MOVIES_CSV)
    ratings = pd.read_csv(RATINGS_SMALL_CSV)

    conn = sqlite3.connect(DB_PATH)

    movies.to_sql("movies_metadata", conn, if_exists="replace", index=False)
    ratings.to_sql("ratings", conn, if_exists="replace", index=False)

    conn.close()
    print("Done creating DB")


createDB()

app = Flask(__name__)
CORS(app)

DB_PATH = Path(__file__).parent / "movies.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def get_movies():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, original_title FROM movies_metadata LIMIT 10", conn
    )
    conn.close()
    return df.to_json(orient="records")


@app.route("/movie/search")
def search_movies():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"exists": False, "results": []})

    conn = get_connection()

    # Case-insensitive title search
    query = """
        SELECT id, original_title
        FROM movies_metadata
        WHERE LOWER(original_title) LIKE ?
        LIMIT 20
    """
    param = f"%{title.lower()}%"

    cur = conn.execute(query, (param,))
    rows = [{"id": r["id"], "original_title": r["original_title"]} for r in cur.fetchall()]
    conn.close()

    return jsonify({"exists": len(rows) > 0, "results": rows})


@app.route("/movie/details")
def movie_details():
    # movie title the user clicked (coming from frontend)
    movie_title = request.args.get("title", "").strip()
    if not movie_title:
        return jsonify({"error": "Missing title parameter"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # get movie title, id, and overview
    movie_query = """
        SELECT id, original_title, overview
        FROM movies_metadata
        WHERE LOWER(original_title) = LOWER(?)
        LIMIT 1;
    """
    cur.execute(movie_query, (movie_title,))
    movie_row = cur.fetchone()

    if movie_row is None:
        conn.close()
        return jsonify({"error": "Movie not found"}), 404

    movie_id = movie_row["id"]

    #get the average rating for the movie
    avg_query = """
        SELECT AVG(r.rating) AS average_rating
        FROM ratings r
        JOIN movies_metadata m
          ON r.movieId = m.id
        WHERE LOWER(m.original_title) = LOWER(?);
    """
    cur.execute(avg_query, (movie_title,))
    avg_row = cur.fetchone()
    conn.close()

    average_rating = avg_row["average_rating"] if avg_row and avg_row["average_rating"] is not None else None

    # send info to the frontend
    return jsonify({
        "id": movie_row["id"],
        "title": movie_row["original_title"],
        "original_title": movie_row["original_title"],
        "overview": movie_row["overview"],
        "average_rating": average_rating,
    })
#get movies only with their ratings
@app.route("/rated-movies")
def get_rated_movies():
    title = request.args.get("title", "").strip().lower() #Used for sort

    conn = get_connection()
    cur = conn.cursor()

    query = """
            SELECT
                m.id,
                m.original_title,
                m.overview,
                AVG(r.rating) AS average_rating,
                COUNT(r.rating) AS rating_count
            FROM movies_metadata m
            JOIN ratings r ON r.movieId = m.id
            """
    #Implementation for sort to work along with display only movies with ratings
    params = []

    if title:
        query += " WHERE LOWER(m.original_title) LIKE ?"
        params.append(f"%{title}%")

    query += """
        GROUP BY m.id, m.original_title, m.overview
        ORDER BY average_rating DESC
    """

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    results = [
        {
            "id": row["id"],
            "original_title": row["original_title"],
            "overview": row["overview"],
            "average_rating": row["average_rating"],
            "rating_count": row["rating_count"],
        }
        for row in rows
    ]

    return jsonify(results)

# Sort movies in alphabetical, release date, and rating and in ASC and DESC order each
# Displays only rated movies if checkbox is active, and can filter by title or genre
@app.route("/sort-movies")
def sort_movies():
    title = request.args.get("title", "").strip().lower()
    genre_id = request.args.get("genreId", "").strip()
    sort = request.args.get("sort", "").strip()
    order = request.args.get("order", "").strip()

    #Used to toggle movies with ratings
    rated_only_param = request.args.get("rated_only") or request.args.get("onlyRated")
    rated_only = (rated_only_param or "").lower() == "true"

    #Decide which column to sort by
    if sort == "title":
        column = "m.original_title"
    elif sort == "year":
        column = "DATE(m.release_date)"  
    elif sort == "rating":
        column = "average_rating" if rated_only else "m.vote_average"
    else:
        column = "m.original_title"

    conn = get_connection()
    cur = conn.cursor()
    params = []
    conditions = []


    if rated_only:
        #Query only rated movies
        query = f"""
            SELECT
                m.id,
                m.original_title,
                m.release_date,
                AVG(r.rating) AS average_rating,
                COUNT(r.rating) AS rating_count
            FROM movies_metadata m
            JOIN ratings r ON r.movieId = m.id
        """

        #Apply filters
        if title:
            conditions.append("LOWER(m.original_title) LIKE ?")
            params.append(f"%{title}%")
        if genre_id:
            conditions.append("m.genres LIKE ?")
            params.append(f"%'id': {genre_id}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f"""
            GROUP BY m.id, m.original_title, m.release_date
            ORDER BY {column} {order.upper()}
        """

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return jsonify([
            {
                "id": row["id"],
                "original_title": row["original_title"],
                "release_date": row["release_date"],
                "average_rating": row["average_rating"],
                "rating_count": row["rating_count"],
            }
            for row in rows
        ])


    #Include movies with no ratings
    query = f"""
        SELECT id, original_title, release_date, vote_average, vote_count
        FROM movies_metadata m
    """

    #Apply filters
    if title:
        conditions.append("LOWER(original_title) LIKE ?")
        params.append(f"%{title}%")
    if genre_id:
        conditions.append("m.genres LIKE ?")
        params.append(f"%'id': {genre_id}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY {column} {order.upper()}"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return df.to_json(orient="records")


conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# total rows from metadent
print("movies_metadata count:", cur.execute("SELECT COUNT(*) FROM movies_metadata").fetchone()[0])
# total rows from ratings
print("ratings count:", cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0])
# total rows from joined tables
print("joined count (r.movieId = m.id):", cur.execute(
    "SELECT COUNT(*) FROM ratings r JOIN movies_metadata m ON r.movieId = m.id"
).fetchone()[0])

conn.close()


@app.route("/genres")
def get_genres(): 
    valid_genres = [
        {"id": 28, "name": "Action"},
        {"id": 12, "name": "Adventure"},
        {"id": 16, "name": "Animation"},
        {"id": 35, "name": "Comedy"},
        {"id": 80, "name": "Crime"},
        {"id": 99, "name": "Documentary"},
        {"id": 18, "name": "Drama"},
        {"id": 10751, "name": "Family"},
        {"id": 14, "name": "Fantasy"},
        {"id": 36, "name": "History"},
        {"id": 27, "name": "Horror"},
        {"id": 10402, "name": "Music"},
        {"id": 9648, "name": "Mystery"},
        {"id": 10749, "name": "Romance"},
        {"id": 878, "name": "Science Fiction"},
        {"id": 10770, "name": "TV Movie"},
        {"id": 53, "name": "Thriller"},
        {"id": 10752, "name": "War"},
        {"id": 37, "name": "Western"}
    ]   
    return jsonify(valid_genres)


@app.route("/movies/by-genre")
def get_movies_by_genre():
    genre_id = request.args.get("id")
    

    conn = get_connection()
    cur = conn.cursor()
    

    search_pattern = f"%'id': {genre_id}%"
    query = """
        SELECT 
            m.id,
            m.original_title,
            m.overview
        FROM movies_metadata m
        WHERE m.genres LIKE ?
    """
    cur.execute(query, (search_pattern,))
    
    rows = cur.fetchall()
    conn.close()
    
    results = [
        {
            "id": row["id"],
            "original_title": row["original_title"],
            "overview": row["overview"]
        }
        for row in rows
    ]
    
    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=4000)