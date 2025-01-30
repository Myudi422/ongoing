from .module import *

class View:
    def __init__(self, url: str = None, proxies: dict = None) -> None:
        self._url = url
        self._data = {}
        self.proxies = proxies

    # Fungsi untuk mendapatkan link download Pixeldrain
    def __getDownloadLinks(self, soup) -> dict:
        download_links = {}
        try:
            # Cari elemen <div class="download"> yang berisi daftar download
            download_div = soup.find("div", attrs={"class": "download"})
            if not download_div:
                print("Tidak ditemukan elemen <div class='download'>")
                return download_links  # Return empty dict jika tidak ada list

            # Cari semua elemen <ul> di dalam <div class="download">
            download_lists = download_div.find_all("ul")
            if not download_lists:
                print("Tidak ditemukan elemen <ul> di dalam <div class='download'>")
                return download_links  # Return empty dict jika tidak ada list

            # Iterasi setiap <ul>
            for download_list in download_lists:
                # Iterasi setiap <li> dalam <ul>
                for item in download_list.find_all("li"):
                    # Periksa apakah tag <strong> ada
                    strong_tag = item.find("strong")
                    if not strong_tag:
                        continue  # Skip item jika tidak ada resolusi

                    # Ambil teks resolusi dan ekstrak angka dengan regex
                    resolution_text = strong_tag.text.strip()
                    resolution_match = re.search(r"(\d{3,4})p", resolution_text)
                    if not resolution_match:
                        continue  # Skip jika tidak ada angka resolusi

                    resolution = f"{resolution_match.group(1)}p"

                    # Cari link PDrain
                    pd_link = None
                    for link in item.find_all("a", href=True):
                        if "Pdrain" in link.text or "PDrain" in link.text:
                            pd_link = link["href"]
                            break

                    # Jika link PDrain ditemukan, cek URL asli
                    if pd_link:
                        pd_link = self.__resolveSafelink(pd_link)

                    # Ubah URL Pixeldrain ke format API
                    if pd_link and "pixeldrain.com/u/" in pd_link:
                        file_id = pd_link.split("/")[-1]
                        pd_link = f"https://pixeldrain.com/api/file/{file_id}?download"

                    # Tambahkan ke dictionary download_links
                    download_links[resolution] = pd_link or "Link PDrain tidak ditemukan"

        except Exception as e:
            print(f"Error saat mengambil link download: {e}")

        return download_links

    # Fungsi untuk menyelesaikan safelink
    def __resolveSafelink(self, safelink_url: str) -> str:
        try:
            # Gunakan session untuk mengikuti redirect
            with requests.Session() as session:
                response = session.get(safelink_url, allow_redirects=True, timeout=10)
                if response.status_code == 200:
                    return response.url  # Kembalikan URL akhir setelah redirect
                else:
                    print(f"Gagal mengakses safelink: {response.status_code}")
                    return "Gagal mendapatkan link asli"
        except Exception as e:
            print(f"Error saat menyelesaikan safelink: {e}")
            return "Gagal mendapatkan link asli"

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