from .module import *

class View:
    def __init__(self, url: str = None, proxies: dict = None) -> None:
        self._url = url
        self._data = {}
        self.proxies = proxies

    def __getDownloadLinks(self, soup) -> dict:
        download_links = {}
        try:
            download_div = soup.find("div", class_="download")
            if not download_div:
                return download_links

            for ul in download_div.find_all("ul"):
                for li in ul.find_all("li"):
                    strong_tag = li.find("strong")
                    if not strong_tag:
                        continue

                    # Filter hanya MP4
                    resolution_text = strong_tag.get_text().strip().lower()
                    if not resolution_text.startswith("mp4"):
                        continue
                    
                    # Ekstrak resolusi
                    resolution_match = re.search(r"(\d{3,4}p)", resolution_text)
                    if not resolution_match:
                        continue
                    resolution = resolution_match.group(1)

                    # Cari link Pixeldrain
                    pd_link = None
                    for a in li.find_all("a"):
                        if 'pdrain' in a.get_text().lower():
                            pd_link = self.__resolveSafelink(a['href'])
                            break

                    # Format ulang link Pixeldrain
                    if pd_link and "pixeldrain.com/u/" in pd_link:
                        file_id = pd_link.split("/")[-1]
                        pd_link = f"https://pd1.sriflix.myd/api/file/{file_id}?download"

                    download_links[resolution] = pd_link or "Link tidak ditemukan"

        except Exception as e:
            print(f"Error: {str(e)}")
        
        return download_links

    def __resolveSafelink(self, url: str) -> str:
        try:
            with requests.Session() as s:
                resp = s.get(url, timeout=10)
                return resp.url if resp.status_code == 200 else None
        except:
            return None

    # Update fungsi __getData untuk menyertakan link download
    def __getData(self, soup) -> dict:
        venkonten = soup.find("div", attrs={"class": "wowmaskot"}).find(
            "div", attrs={"id": "venkonten"}
        )
        venutama = venkonten.find("div", attrs={"class": "venutama"})
        title = venutama.find("h1", attrs={"class": "posttl"}).string
        prev = venutama.find("div", attrs={"class": "flir"}).findAll("a")
        prev, next = prev[0], prev[-1]
        prev = (
            "None"
            if str(prev.string) == "See All Episodes"
            else re.findall(
                "https\:\/\/otakudesu\..*?\/episode\/(.*?)\/", prev["href"]
            )[0]
        )
        next = (
            "None"
            if str(next.string) == "See All Episodes"
            else re.findall(
                "https\:\/\/otakudesu\..*?\/episode\/(.*?)\/", next["href"]
            )[0]
        )
        stream = venutama.find("div", attrs={"id": "lightsVideo"}).find("iframe")["src"]

        # Ambil data download links
        download_links = self.__getDownloadLinks(soup)

        # Format output sesuai permintaan
        formatted_data = {
            "author": "Latip176",
            "data": {
                "download_links": download_links,
                "judul_episode": title,
                "next": next,
                "prev": prev,
                "stream": stream,
            },
            "msg": "success",
        }
        return formatted_data

    @property
    def results(self) -> dict:
        soup = self.__response()
        return self.__getData(soup=soup)

    def __response(self) -> str:
        scrap = cloudscraper.create_scraper()
        response = scrap.get(self._url)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup
