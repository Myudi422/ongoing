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
            telegram_id = request.args.get("telegram_id")  # parameter untuk watch_time
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                # Cari data di tabel otakudesu berdasarkan anime_id
                sql_otakudesu = "SELECT slug FROM otakudesu WHERE anime_id = %s"
                cursor.execute(sql_otakudesu, (anime_id,))
                result_otakudesu = cursor.fetchone()
            
            if result_otakudesu:
                # Jika ditemukan, lakukan scraping menggunakan slug
                slug = result_otakudesu["slug"]
                Main = Reads(
                    url="https://otakudesu.cloud/anime/" + slug,
                    nonton_anime_id=anime_id,  # anime_id sudah berupa string
                    telegram_id=telegram_id
                )
                soup = Main.response()
                episodes = Main.getDataEpisode(soup)
                # Pastikan anime_id dan episode_number berupa string untuk setiap episode
                for ep in episodes:
                    ep["anime_id"] = str(ep["anime_id"]) if ep.get("anime_id") is not None else None
                    ep["episode_number"] = str(ep["episode_number"]) if ep.get("episode_number") is not None else None
                episodes.reverse()  # agar episode pertama muncul di atas
                connection.close()
                return jsonify(episodes), 200
            else:
                # Jika tidak ditemukan di otakudesu, ambil data langsung dari tabel nonton
                with connection.cursor() as cursor:
                    if telegram_id:
                        sql_nonton = """
                        SELECT n.anime_id, n.episode_number, n.title, n.video_url, n.subtitle_links, n.subtitle_url, n.resolusi,
                               w.video_time
                        FROM nonton n
                        LEFT JOIN waktu_terakhir_tontonan w 
                          ON n.anime_id = w.anime_id 
                         AND n.episode_number = w.episode_number 
                         AND w.telegram_id = %s
                        WHERE n.anime_id = %s
                        ORDER BY n.episode_number
                        """
                        cursor.execute(sql_nonton, (telegram_id, anime_id))
                    else:
                        sql_nonton = """
                        SELECT anime_id, episode_number, title, video_url, subtitle_links, subtitle_url, resolusi
                        FROM nonton
                        WHERE anime_id = %s
                        ORDER BY episode_number
                        """
                        cursor.execute(sql_nonton, (anime_id,))
                    
                    episodes = cursor.fetchall()
                    
                    # Untuk setiap episode, pastikan anime_id dan episode_number berupa string dan tambahkan link_gambar
                    for ep in episodes:
                        ep["anime_id"] = str(ep["anime_id"]) if ep.get("anime_id") is not None else None
                        ep["episode_number"] = str(ep["episode_number"]) if ep.get("episode_number") is not None else None
                        
                        sql_thumb = """
                        SELECT link_gambar FROM thumbnail
                        WHERE anime_id = %s AND episode_number = %s
                        """
                        cursor.execute(sql_thumb, (anime_id, ep["episode_number"]))
                        thumb_result = cursor.fetchone()
                        ep["link_gambar"] = thumb_result["link_gambar"] if thumb_result else None

                        # Format video_time jika ada, pastikan dalam bentuk string dengan format "x.x"
                        if "video_time" in ep and ep["video_time"] is not None:
                            if isinstance(ep["video_time"], (int, float)):
                                ep["video_time"] = f"{ep['video_time']:.1f}"
                            else:
                                ep["video_time"] = str(ep["video_time"])
                        else:
                            ep["video_time"] = None
                        ep["ditonton"] = "0"  # default jika belum ada data
                    connection.close()
                    return jsonify(episodes), 200

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
    app.run(host="0.0.0.0", port=5000, debug=True)


