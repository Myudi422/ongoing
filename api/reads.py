from .module import *
import re
import pymysql
import cloudscraper
from bs4 import BeautifulSoup

# Konfigurasi database (sama dengan DB_CONFIG di atas)
DB_CONFIG = {
    "host": "143.198.85.46",
    "user": "ccgnimex",
    "password": "aaaaaaac",
    "db": "ccgnimex",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

class WebScrapper:
    def __init__(self, url: str = None) -> None:
        self._url = url
        self.data = {}
    
    @property
    def results(self):
        response = self.response()
        data = self.getData(soup=response)
        return data

    def getDataEpisode(self, soup) -> list:
        data_private = []
        # Ambil elemen kedua dari daftar div episodelist
        venkonten = soup.find("div", attrs={"id": "venkonten"}).findAll("div", attrs={"class": "episodelist"})[1]
        for data in venkonten.find("ul").findAll("li"):
            span = data.find("span").find("a")
            title_episode = span.string
            href_episode = span["href"]
            release_episode = data.find("span", attrs={"class": "zeebr"}).string

            # Ambil bagian URL episode (contoh: "wdbrkr-s2-episode-1-sub-indo" atau "yami-heal-sub-indo")
            episode_data_list = re.findall(r"https\:\/\/otakudesu\..*?\/episode\/(.*?)\/", str(href_episode))
            episode_data = episode_data_list[0] if episode_data_list else ""
            
            # Parse nomor episode dari episode_data
            ep_match = re.search(r'episode-(\d+)', episode_data)
            if ep_match:
                episode_number = ep_match.group(1)
            else:
                # Jika tidak ditemukan pola "episode-<nomor>" di URL, asumsikan episode 1
                episode_number = "1"

            # Ambil detail tambahan dari tabel nonton dan thumbnail jika memungkinkan
            if episode_number and hasattr(self, 'nonton_anime_id') and self.nonton_anime_id:
                episode_details = self.getEpisodeDetails(episode_number)
            else:
                episode_details = {
                    "anime_id": None,
                    "episode_number": None,
                    "title": None,
                    "video_url": None,
                    "subtitle_links": None,
                    "subtitle_url": None,
                    "resolusi": None,
                    "ditonton": "0",
                    "video_time": None,
                    "link_gambar": None
                }
            
            episode_dict = {
                "data": episode_data,
                "judul_episode": title_episode,
                "release": release_episode
            }
            # Gabungkan data scraping dengan detail dari database
            episode_dict.update(episode_details)
            data_private.append(episode_dict)
        return data_private

    def getEpisodeDetails(self, episode_number) -> dict:
        details = {}
        try:
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                # Jika telegram_id tersedia, gunakan join query untuk mendapatkan video_time dari tabel waktu_terakhir_tontonan
                if hasattr(self, 'telegram_id') and self.telegram_id:
                    sql = """
                    SELECT n.anime_id, n.episode_number, n.title, n.video_url, n.subtitle_links, n.subtitle_url, n.resolusi,
                           w.video_time
                    FROM nonton n
                    LEFT JOIN waktu_terakhir_tontonan w 
                      ON n.anime_id = w.anime_id 
                     AND n.episode_number = w.episode_number 
                     AND w.telegram_id = %s
                    WHERE n.anime_id = %s AND n.episode_number = %s
                    """
                    cursor.execute(sql, (self.telegram_id, self.nonton_anime_id, episode_number))
                else:
                    sql = """
                    SELECT anime_id, episode_number, title, video_url, subtitle_links, subtitle_url, resolusi
                    FROM nonton
                    WHERE anime_id = %s AND episode_number = %s
                    """
                    cursor.execute(sql, (self.nonton_anime_id, episode_number))
                result = cursor.fetchone()
                if result:
                    details.update(result)
                            
                    details["episode_number"] = str(details["episode_number"]) if details["episode_number"] is not None else None
                    details["anime_id"] = str(details["anime_id"]) if details["anime_id"] is not None else None

                    # Jika video_time ada dan bukan None, pastikan outputnya berupa string dengan format "x.x"
                    if "video_time" in details and details["video_time"] is not None:
                        if isinstance(details["video_time"], (int, float)):
                            details["video_time"] = f"{details['video_time']:.1f}"
                        else:
                            details["video_time"] = str(details["video_time"])
                    else:
                        details["video_time"] = None
                    details["ditonton"] = "0"
                else:
                    details.update({
                        "anime_id": None,
                        "episode_number": episode_number,
                        "title": None,
                        "video_url": None,
                        "subtitle_links": None,
                        "subtitle_url": None,
                        "resolusi": None,
                        "ditonton": "0",
                        "video_time": None
                    })
                # Ambil link_gambar dari tabel thumbnail
                sql_thumb = """
                SELECT link_gambar FROM thumbnail
                WHERE anime_id = %s AND episode_number = %s
                """
                cursor.execute(sql_thumb, (self.nonton_anime_id, episode_number))
                thumb_result = cursor.fetchone()
                details["link_gambar"] = thumb_result["link_gambar"] if thumb_result else None
            connection.commit()
        except Exception as e:
            print("Error querying episode details:", e)
            details = {
                "anime_id": None,
                "episode_number": episode_number,
                "title": None,
                "video_url": None,
                "subtitle_links": None,
                "subtitle_url": None,
                "resolusi": None,
                "ditonton": "0",
                "video_time": None,
                "link_gambar": None
            }
        finally:
            if connection:
                connection.close()
        return details

    def getData(self, soup):
        self.data.clear()
        venkonten = soup.find("div", attrs={"id": "venkonten"}).find("div", attrs={"class": "fotoanime"})
        info = venkonten.find("div", attrs={"class": "infozin"})
        info_anime = info.find("div", attrs={"class": "infozingle"})
        sinopsis = re.findall(r"\>(.*?)\<\/div\>", str(venkonten.find("div", attrs={"class": "sinopc"})))[0]
        for data in info_anime.findAll("p"):
            dat = data.find("span")
            key = re.findall(r"\<b\>(.*?)\<\/b\>", str(dat))[0].lower().replace(" ", "_")
            value = re.findall(r"\:\s(.*?)\<\/span\>", str(dat))[0]
            if key == "genre":
                value = ", ".join(re.findall(r">(.*?)<\/a>", str(value)))
            self.data.update({key: value})
        self.data.update({
            "cover": venkonten.find("img")["src"],
            "sinopsis": str(sinopsis),
            "data_episode": self.getDataEpisode(soup=soup),
        })
        return self.data

class Reads(WebScrapper):
    def __init__(self, url: str = None, proxies: dict = None, nonton_anime_id=None, telegram_id=None) -> None:
        super().__init__(url=url)
        self.proxies = proxies
        self.nonton_anime_id = nonton_anime_id  # digunakan untuk query ke tabel nonton dan thumbnail
        self.telegram_id = telegram_id          # digunakan untuk join dengan tabel waktu_terakhir_tontonan

    def response(self) -> BeautifulSoup:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(self._url)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup
