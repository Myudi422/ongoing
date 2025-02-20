from .module import *
import re
import pymysql



class WebScrapper:
    def __init__(self, url: str = None):
        self._url = url
        self.data = []
        self.db_config = {
            "host": "143.198.85.46",
            "user": "ccgnimex",
            "password": "aaaaaaac",
            "db": "ccgnimex"  # asumsi nama database adalah 'otakudesu'
        }

    @property
    def results(self):
        response = self.response()
        data = self.getData(soup=response)
        return data

    def getData(self, soup) -> list:
        self.data.clear()
        venutama = soup.find("div", attrs={"id": "venkonten"}).find("div", attrs={"class": "venutama"})
        konten = venutama.find("div", attrs={"class": "venz"}).find("ul")

        for data_item in konten.findAll("li"):
            detpost = data_item.find("div", attrs={"class": "detpost"})
            thumb = detpost.find("div", attrs={"class": "thumb"}).find("a", href=True)
            thumz = thumb.find("div", attrs={"class": "thumbz"})
            title = thumz.find("h2").string
            cover = thumz.find("img")
            episode = re.findall(" (Episode \d+)", str(detpost.find("div", attrs={"class": "epz"})))
            release_on = re.findall("\/i>\s+(.*?)<\/div>", str(detpost.find("div", attrs={"class": "epztipe"})))
            release = detpost.find("div", attrs={"class": "newnime"}).string

            anime = {
                "judul": title,
                "cover": cover["src"],
                "data": re.findall("https\:\/\/otakudesu\..*?\/anime\/(.*?)\/", str(thumb["href"]))[0],
                "episode": "".join(episode),
                "release": release,
                "release_on_every": release_on[0] if release_on else ""
            }
            self.data.append(anime)

        # Tambahkan parameter anime_id dari database
        self.add_anime_id(self.data)

        if self.route != False:
            pagination = venutama.find("div", attrs={"class": "pagination"})
            next_page = pagination.find("a", attrs={"class": "next page-numbers"})
            return {
                "data_anime": self.data,
                "next": re.findall("\/(page\/\d+)\/", str(next_page["href"]))[0].replace("/", "-") if next_page else "None",
            }
        return self.data

    def add_anime_id(self, anime_list: list) -> None:
        """
        Fungsi untuk mengecek setiap anime berdasarkan slug (field "data")
        di tabel otakudesu dan menambahkan key "anime_id" jika ada.
        """
        try:
            connection = pymysql.connect(
                host=self.db_config["host"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                db=self.db_config["db"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor
            )
            with connection.cursor() as cursor:
                for anime in anime_list:
                    slug = anime.get("data")
                    sql = "SELECT anime_id FROM otakudesu WHERE slug = %s"
                    cursor.execute(sql, (slug,))
                    result = cursor.fetchone()
                    # Jika data ditemukan, tambahkan anime_id, jika tidak None
                    anime["anime_id"] = result["anime_id"] if result else None
            connection.commit()
        except Exception as e:
            print("Error saat koneksi database:", e)
            # Bila terjadi error, set anime_id menjadi None
            for anime in anime_list:
                anime["anime_id"] = None
        finally:
            if connection:
                connection.close()

class Home(WebScrapper):
    def __init__(self, url: str = None, proxy: dict = None, route=False) -> None:
        super().__init__(url=url)
        self.proxies = proxy
        self.route = route

    def response(self) -> str:
        scrap = cloudscraper.create_scraper()
        response = scrap.get(self._url)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup