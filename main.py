from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from api.index import Home
from api.reads import Reads
from api.view import View
import pymysql
from api.search import Search
from api.genre import Genres
from results import Output

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

# Konfigurasi database (sesuaikan jika diperlukan)
DB_CONFIG = {
    "host": "143.198.85.46",
    "user": "ccgnimex",
    "password": "aaaaaaac",
    "db": "ccgnimex",  # asumsi nama database adalah 'ccgnimex'
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}



# Set header response
@app.after_request
def add_header(response):
    response.headers["Content-Type"] = "application/json"
    return response


# INDEX API
@app.route("/")
def index():
    return Output.results(None, "Welcome to my API", 200)


# INDEX API
@app.route("/api/otakudesu/")
def otakudesu():
    return Output.results(
        None, "Check Documentation on github.com/Latip176/otakudesu-api", 200
    )


@app.route("/episode/")
def info():
    try:
        anime_id = request.args.get("anime_id")
        if anime_id:
            telegram_id = request.args.get("telegram_id")  # parameter baru untuk tracking video_time
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                sql = "SELECT slug FROM otakudesu WHERE anime_id = %s"
                cursor.execute(sql, (anime_id,))
                result = cursor.fetchone()
            connection.close()
            
            if result:
                slug = result["slug"]
                # Buat instance Reads dengan nonton_anime_id dan telegram_id (jika tersedia)
                Main = Reads(
                    url="https://otakudesu.cloud/anime/" + slug,
                    nonton_anime_id=anime_id,
                    telegram_id=telegram_id
                )
                soup = Main.response()
                episodes = Main.getDataEpisode(soup)
                # Balik urutan list agar episode pertama berada di atas
                episodes.reverse()
                return jsonify(episodes), 200
            else:
                return jsonify({"error": "Anime ID not found"}), 404
        
        # Fallback: jika parameter anime_id tidak disediakan, gunakan parameter 'data'
        data_param = request.args.get("data")
        if data_param:
            Main = Reads(url="https://otakudesu.cloud/anime/" + data_param)
            return Output.results(Main.results, "success", 200)
        
        return Output.results(None, "Data is required!", 400)
    except Exception as e:
        return Output.results({"data": None}, f"error {e}", 400)

#resolusi
@app.route("/resolusi/")
def resolusi():
    try:
        anime_id = request.args.get("anime_id")
        episode_number = request.args.get("episode_number")
        if not anime_id or not episode_number:
            return jsonify({"error": "Parameters anime_id and episode_number are required"}), 400

        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            sql = """
            SELECT resolusi, video_url
            FROM nonton
            WHERE anime_id = %s AND episode_number = %s
            """
            cursor.execute(sql, (anime_id, episode_number))
            results = cursor.fetchall()
        connection.close()

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# STREAM
@app.route("/api/otakudesu/view/")
def view():
    try:
        url = request.args.get("data")
        if url:
            Main = View(url="https://otakudesu.cloud/episode/" + url)
            return Output.results(Main.results, "success", 200)
        return Output.results(None, "Data is required!", 400)
    except Exception as e:
        return Output.results({"data": None}, f"error {e}", 400)


# HOME
@app.route("/api/otakudesu/home/")
def home():
    try:
        data = Home("https://otakudesu.cloud/")
        return Output.results(data.results, "success", 200)
    except Exception as e:
        return Output.results({"data": None}, f"error {e}", 400)

@app.route("/ongoing/")
def ongoing():
    try:
        url_param = request.args.get("next")
        base_url = "https://otakudesu.cloud/ongoing-anime/"
        # Jika ada parameter next, gunakan untuk membangun URL awal; jika tidak, gunakan base_url
        current_url = base_url if not url_param else base_url + url_param.replace("-", "/")
        
        all_data = []  # Menyimpan data dari tiap halaman
        pages_to_fetch = 4  # Jumlah halaman yang diambil
        
        for _ in range(pages_to_fetch):
            home = Home(current_url, route=True)
            page_results = home.results  # Menghasilkan dict: {"data_anime": [...], "next": "page-1" atau "None"}
            all_data.extend(page_results["data_anime"])
            
            # Hentikan perulangan jika tidak ada halaman selanjutnya
            if page_results["next"] == "None":
                break
            
            # Bangun URL untuk halaman berikutnya
            next_page = page_results["next"]
            current_url = base_url + next_page.replace("-", "/")
        
        # Pisahkan data berdasarkan adanya anime_id (tidak None) dan sebaliknya
        ongoing_anime_data = [anime for anime in all_data if anime.get("anime_id") is not None]
        null_anime_data = [anime for anime in all_data if anime.get("anime_id") is None]
        
        result_json = {
            "ongoing_anime_data": ongoing_anime_data,
            "null_anime_data": null_anime_data
        }
        return jsonify(result_json), 200
    except Exception as e:
        # Bila terjadi error, kembalikan response dengan format yang sama namun data kosong
        return jsonify({
            "ongoing_anime_data": [],
            "null_anime_data": []
        }), 400


# COMPLETED
@app.route("/api/otakudesu/complete/")
def complete():
    try:
        url = request.args.get("next")
        data = (
            Home(
                "https://otakudesu.cloud/complete-anime/" + url.replace("-", "/"),
                route=True,
            )
            if url
            else Home("https://otakudesu.cloud/complete-anime/", route=True)
        )
        return Output.results(data.results, "success", 200)
    except Exception as e:
        return Output.results({"data": None}, f"error {e}", 400)


# SEARCH
@app.route("/api/otakudesu/search/")
def searchAnime():
    try:
        keyword = request.args.get("keyword")
        if keyword:
            keyword = keyword.replace(" ", "+")
            data = Search(url=f"https://otakudesu.cloud/?s={keyword}&post_type=anime")
            return Output.results(data.results, "success", 200)
        return Output.results(None, "Keyword is required!", 400)
    except Exception as e:
        return Output.results({"data": None}, f"error {e}", 400)


# GENRES
@app.route("/api/otakudesu/genres/")
def get_all_genres():
    try:
        data = Genres("https://otakudesu.cloud/genre-list/")
        return Output.results(data.get_genres(), "success", 200)
    except Exception as e:
        return Output.results({"data": None}, f"error {e}", 400)


@app.route("/api/otakudesu/genres/<genre>/")
@app.route("/api/otakudesu/genres/<genre>/<page>")
def get_genres(genre, page=None):
    try:
        data = Genres("https://otakudesu.cloud/genre-list/")
        if page:
            return Output.results(
                data.get_data(genre + "/page/" + page), "success", 200
            )
        return Output.results(data.get_data(genre), "success", 200)
    except Exception as e:
        return Output.results({"data": None}, f"error {e}", 400)


if __name__ == "__main__":
    app.run(debug=True)
