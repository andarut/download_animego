#!.venv/bin/python3.11

import os
import time
import inspect # for debug
import filecmp # for chunk diff
from enum import StrEnum

import re

from seleniumwire import webdriver # not just selenium to support local drivers

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException

URLS_PATH = "urls.txt"

class Colors(StrEnum):
	HEADER = '\033[95m'
	BLUE = '\033[94m'
	CYAN = '\033[96m'
	GREEN = '\033[92m'
	YELLOW = '\033[93m'
	RED = '\033[91m'
	END = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'


class Logger:

	@staticmethod
	def print(text: str, color: str):
		print("[" + inspect.stack()[2].function.lower() + "]: " + color + text + Colors.END)

	@staticmethod
	def log(text):
		Logger.print(text, Colors.CYAN)

	@staticmethod
	def ok(text):
		Logger.print(text, Colors.GREEN)

	@staticmethod
	def error(text):
		Logger.print(text, Colors.RED)

	@staticmethod
	def warning(text):
		Logger.print(text, Colors.YELLOW)


class Element:

	def __init__(self, name: str|None, xpath: str|None):
		self.name = name
		self.xpath = xpath
		self.selenium_element: WebElement = WebElement(None, None)

	def text(self):
		return self.selenium_element.text

	def clear(self):
		self.selenium_element.clear()

	def type(self, text: str, clear=False, enter=False):
		# clear field
		if clear: self.clear()

		# type text
		self.selenium_element.send_keys(text)

		# hit enter
		if enter: self.selenium_element.send_keys(Keys.ENTER)

	def get(self, attr: str) -> str:
		res = self.selenium_element.get_attribute(attr)
		if res is None:
			Logger.error(f"{self.name} do not have attribute {attr}")
			return ""
		return res

	@staticmethod
	def none():
		return Element(None, None)

	def is_none(self):
		return self.name == None and self.xpath == None


class Engine:

	ACTION_TIMEOUT = 5
	STARTUP_TIMEOUT = 5

	def __init__(self, url: str, debug = os.environ.get('DEBUG', False)):
		self.url = url
		# self.service = Service(executable_path='./yandexdriver')
		self.options = webdriver.ChromeOptions()
		self.options.add_argument("--mute-audio")
		self.DEBUG = debug
		self.driver = webdriver.Chrome(options=self.options)
		self.driver.maximize_window()
		self.driver.set_page_load_timeout(300)
		while True:
			try:
				self.driver.get(self.url)
				break
			except TimeoutException:
				Logger.warning(f"Driver timeout for {self.url}, trying again")
		time.sleep(self.STARTUP_TIMEOUT)

	def zoom(self, zoom):
		self.driver.execute_script(f"document.body.style.zoom='{zoom}%'")
		time.sleep(self.ACTION_TIMEOUT)

	def find_element(self, name: str, xpath: str) -> Element:
		element = Element(name, xpath)

		try:
			element.selenium_element = self.driver.find_element(By.XPATH, element.xpath)
		except NoSuchElementException:
			if self.DEBUG:
				Logger.error(f"{element.name} not found")
			return Element.none()

		if self.DEBUG:
			Logger.log(f"{element.name} found")

		return element

	def find_elements(self, name: str, class_name: str) -> list[Element]:
		elements = []

		try:
			for el in self.driver.find_elements(By.CLASS_NAME, class_name):
				element = Element(name, "")
				element.selenium_element = el
				elements.append(element)
		except NoSuchElementException:
			if self.DEBUG:
				Logger.error(f"{name} not found")
			return []

		if self.DEBUG:
			Logger.log(f"{name} found {len(elements)} times")

		return elements

	def click(self, element: Element):
		self.driver.execute_script("arguments[0].click();", element.selenium_element)
		if self.DEBUG:
			Logger.log(f"{element.name} clicked")
		time.sleep(self.ACTION_TIMEOUT)

	def type(self, element: Element, text: str, clear=False, enter=False) -> bool:
		try:
			element.type(text, clear, enter)
		except ElementNotInteractableException:
			return False
		if self.DEBUG:
			Logger.log(f"{element.name} typed {text} with clear={clear}, enter={enter}")
		time.sleep(self.ACTION_TIMEOUT)
		return True

	def quit(self):
		self.driver.quit()

class Downloader:

	@staticmethod
	def write_url(url):
		with open(URLS_PATH, "a") as f:
			f.write(f"{url}\n")

	@staticmethod
	def url_exist(i):
		with open(URLS_PATH, "r") as f:
			urls_count = len(f.readlines())
			if i <= urls_count:
				return True
		return False

	@staticmethod
	def download_aot(URL, SEASON, DIR):
		TITLE = "Attack.on.Titan"
		print(f"DOWNLOADING {DIR}/{TITLE}.S{SEASON:02}")
		engine = Engine(URL)
		engine.zoom(30)
		hrefs = [a.get("href") for a in engine.find_elements("EPISODE_i", "one-series")]
		engine.quit()

		print(len(hrefs))


		urls = []
		i = 1
		for href in hrefs:

			print(f"TRY {DIR}/{TITLE}.S{SEASON:02}.E{i:02}.mp4")

			if os.path.isfile(f"{DIR}/{TITLE}.S{SEASON:02}.E{i:02}.mp4"):
				print(f"SKIP")
				i += 1
				continue

			subengine = Engine(href)

			PLAYER_FRAME = subengine.find_element(
				"PLAYER_FRAME",
				'//*[@id="iframe-player"]'
			)
			subengine.driver.switch_to.frame(PLAYER_FRAME.selenium_element)

			PLAY_BUTTON = subengine.find_element(
				"PLAY_BUTTON",
				'/html/body/div[1]/div[5]/a'
			)
			subengine.click(PLAY_BUTTON)
			time.sleep(30)

			for request in subengine.driver.requests:
				if request.response:
					if ".m3u8" in request.url:
						m3u8_url = request.url.split('m3u8')[0] + "m3u8"
						mp4_url = m3u8_url.replace(':hls:manifest.m3u8', '')
						mp4_url = mp4_url.replace('360.mp4', '720.mp4')
						urls.append(mp4_url)
						print(f"FOUND {mp4_url}")
						Downloader.write_url(mp4_url)
						break

			subengine.quit()
			i += 1

		j = 0
		for i in range(1, len(hrefs)+1):
			if os.path.isfile(f"{DIR}/{TITLE}.S{SEASON:02}.E{i:02}.mp4"):
				print(f"SKIP DOWNLOADING {DIR}/{TITLE}.S{SEASON:02}.E{i:02}.mp4")
				continue
			url = urls[j]
			filename = f"{DIR}/{TITLE}.S{SEASON:02}.E{i:02}.mp4"
			Downloader.download_video(url, filename)
			j += 1

	@staticmethod
	def download_animego(URL, AUDIO, SEASON, DIR, VPN):

		if VPN:
			print("STARTING VPN...")
			os.system('./vpn_on.sh')
			time.sleep(3)


		engine = Engine(URL)

		EPISODS_COUNT_TEXT = engine.find_element(
			"EPISODS_COUNT_TEXT",
			'//*[@id="content"]/div/div[1]/div[2]/div[3]/dl/dd[2]'
		)
		if EPISODS_COUNT_TEXT.is_none():
			return Downloader.download_animego(URL, AUDIO, SEASON, DIR, VPN)

		TITLE_TEXT = engine.find_element(
			"TITLE_TEXT",
			'//*[@id="content"]/div/div[1]/div[2]/div[2]/div/div/div[1]/ul/li[1]'
		)
		if TITLE_TEXT.is_none() or re.search('[a-zA-Z]', TITLE_TEXT.text()) is None:
			TITLE_TEXT = engine.find_element(
				"TITLE_TEXT",
				'//*[@id="content"]/div/div[1]/div[2]/div[2]/div/div/div[1]/ul/li[2]'
			)
			if TITLE_TEXT.is_none() or re.search('[a-zA-Z]', str(TITLE_TEXT.text())) is None:
				Logger.error("TITLE not found, specify name manually")
				TITLE = str(input("TITLE: "))

		TITLE = ''.join(e for e in TITLE if e.isalnum() or e == ' ')
		TITLE = TITLE.replace(" ", ".")
		print(f"DOWNLOADING {TITLE}")
		epidods_count = int(EPISODS_COUNT_TEXT.text())
		print(f"epidods_count = {epidods_count}")

		AGING_TEXT = engine.find_element(
			"AGING_TEXT",
			'//*[@id="content"]/div/div[1]/div[2]/div[3]/dl/dd[10]/span'
		)
		if AGING_TEXT.is_none():
			AGING_TEXT = engine.find_element(
				"AGING_TEXT",
				'//*[@id="content"]/div/div[1]/div[2]/div[3]/dl/dd[8]/span'
			)
			if AGING_TEXT.is_none():
				Downloader.download_animego(URL, AUDIO, SEASON, DIR, VPN)
				return

		AGING = str(AGING_TEXT.text())

		if "NC" in AGING:
			AGING_TEXT = engine.find_element(
				"AGING_TEXT",
				'//*[@id="content"]/div/div[1]/div[2]/div[3]/dl/dd[9]/span'
			)
			AGING = str(AGING_TEXT.text())

		print(f"AGING = {AGING}")

		engine.quit()

		base_urls = []

		i = 1
		while i <= epidods_count:

			print(i)

			if Downloader.url_exist(i):
				print(f"URL for {i} exist - skip")
				i += 1
				continue


			subengine = Engine(URL)

			WATCH_BUTTON = subengine.find_element(
				"WATCH_BUTTON",
				'//*[@id="content"]/div/div[1]/div[1]/div[2]/a/span[2]'
			)

			if WATCH_BUTTON.is_none():
				subengine.quit()
				continue

			subengine.click(WATCH_BUTTON)

			subengine.zoom(30)

			if "18" in AGING:

				BUTTON_18 = subengine.find_element(
					"BUTTON_18",
					'//*[@id="video-player"]/div[1]/div/div[2]/button[2]'
				)

				if BUTTON_18.is_none():
					subengine.quit()
					continue

				subengine.click(BUTTON_18)


			# доступные озвучки
			try:
				AUDIO_BUTTON = [el for el in subengine.find_elements("audio", "video-player-toggle-item") if el.text() == AUDIO][0]
			except IndexError:
				subengine.quit()
				continue

			subengine.click(AUDIO_BUTTON)

			if i != 1:
				EPISODE_INPUT = subengine.find_element(
					"EPISODE_INPUT",
					'//*[@id="video-series-number-input"]'
				)

				if EPISODE_INPUT.is_none():
					subengine.quit()
					continue

				if not subengine.type(EPISODE_INPUT, str(i), clear=True, enter=True):
					subengine.quit()
					continue

			PLAYER_FRAME = subengine.find_element(
				"PLAYER_FRAME",
				'//*[@id="video-player"]/div[2]/div[1]/div[1]/iframe'
			)

			if PLAYER_FRAME.is_none():
				subengine.quit()
				continue

			subengine.driver.switch_to.frame(PLAYER_FRAME.selenium_element)

			PLAY_BUTTON = subengine.find_element(
				"PLAY_BUTTON",
				'//*[@id="vjs_video_3"]/button'
			)

			if PLAY_BUTTON.is_none():
				# sometimes xpath is different
				PLAY_BUTTON = subengine.find_element(
					"PLAY_BUTTON",
					"/html/body/div[1]/div[5]/a"
				)
				if PLAY_BUTTON.is_none():
					PLAY_BUTTON = subengine.find_element(
						"PLAY_BUTTON",
						'//*[@id="video_html5_wrapper"]/div[6]'
					)
					if PLAY_BUTTON.is_none():
						subengine.quit()
						continue

			# subengine.click(PLAY_BUTTON)
			js_script = """
			var element = document.evaluate(arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
			if (element) {
			    element.click();
			}
			"""

			subengine.driver.execute_script(js_script, '//*[@id="vjs_video_3"]/button')

			# wait for ads
			time.sleep(120)

			# wait for content
			time.sleep(10)

			# get base_url for future downloades
			base_url = ""
			for request in subengine.driver.requests:
				if request.response:
					if ".m4s" in request.url and "yandex" not in request.url:
						base_url = request.url.split("_")[0]
						print(f"FOUND BASE URL {base_url}")
						Downloader.write_url(base_url)
						base_urls.append(base_url)
						break

			if len(base_url) == 0:
				mp4_url = ""
				print("TRYING TO FIND M3U8 MANIFEST...")
				# find m3u8 manifest
				for request in subengine.driver.requests:
					if request.response:
						if ".m3u8" in request.url:
							m3u8_url = request.url.split('m3u8')[0] + "m3u8"
							mp4_url = m3u8_url.replace(':hls:manifest.m3u8', '')
							mp4_url = mp4_url.replace('360.mp4', '720.mp4')
							print(f"FOUND BASE URL {mp4_url}")
							base_urls.append(mp4_url)
							Downloader.write_url(mp4_url)
							break
				if len(mp4_url) == 0:
					mp4_url = ""
					print("TRYING TO FIND FULL MP4 ...")
					# find full mp4
					for request in subengine.driver.requests:
						if request.response:
							if ".mp4" in request.url and "noip" in request.url:
								mp4_url = request.url
								print(f"FOUND BASE URL {mp4_url}")
								base_urls.append(mp4_url)
								Downloader.write_url(mp4_url)
								break
					if len(mp4_url) == 0:
						Logger.error("BASE_URL NOT FOUND")
						subengine.quit()
						continue

			subengine.quit()

			i += 1

		engine.quit()

		if VPN:
			os.system('./vpn_off.sh')
			time.sleep(3)

		base_urls = []
		with open(URLS_PATH, "r") as f:
			for line in f.readlines():
				if line != "\n":
					base_urls.append(line.replace("\n", ""))

		if len(base_urls) != epidods_count:
			print(f"not enough urls {len(base_urls)}/{epidods_count}")
			exit(1)

		print(f"BASE_URLS = {base_urls}")

		for i in range(1, len(base_urls)+1):
			base_url = base_urls[i-1]
			filename = f"{DIR}/{TITLE}.S{SEASON:02}.E{i:02}.mp4" if SEASON != 0 else f"{DIR}/{TITLE}.E{i:02}.mp4"
			Downloader.download_video(base_url, filename)
			if not os.path.isfile(filename):
				print("donwloading error")
				exit(1)

		os.system(f"rm -f {URLS_PATH} && touch {URLS_PATH}")

	@staticmethod
	def download(URL: str, AUDIO: str, SEASON: int, DIR: str, VPN: bool):
		if "ataka-titanov" in URL:
			Downloader.download_aot(URL, SEASON, DIR)
		else:
			Downloader.download_animego(URL, AUDIO, SEASON, DIR, VPN)

	@staticmethod
	def download_video(base_url: str, filename: str):

		if ".mp4" in base_url:
			os.system(f'wget -O {filename} "{base_url}"')
			return

		# chunk_type = 6 -> video type
		# chunk_type = 1 -> video type
		def download_chunk(chunk_url: str, chunk_path: str):
			print(f"[DOWNLOAD_CHUNK] {chunk_path} {chunk_url}")
			os.system(f"""curl '{chunk_url}' \
			-H 'Accept: */*' \
			-H 'Accept-Language: ru,en;q=0.9' \
			-H 'Connection: keep-alive' \
			-H 'Origin: https://aniboom.one' \
			-H 'Referer: https://aniboom.one/' \
			-H 'Sec-Fetch-Dest: empty' \
			-H 'Sec-Fetch-Mode: cors' \
			-H 'Sec-Fetch-Site: cross-site' \
			-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/24.1.0.0 Safari/537.36' \
			-H 'sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120", "YaBrowser";v="24.1", "Yowser";v="2.5"' \
			-H 'sec-ch-ua-mobile: ?0' \
			-H 'sec-ch-ua-platform: "macOS"' \
			--compressed \
			-o {chunk_path}""")
			try:
				chunk_size = os.stat(chunk_path).st_size
			except FileNotFoundError:
				Logger.error("curl error, redownloading chunk")
				download_chunk(chunk_url, chunk_path)

		download_chunk(f"{base_url}_init_6.m4s", f"video_0.m4s")
		download_chunk(f"{base_url}_init_1.m4s", f"audio_0.m4s")

		i = 1

		video_chunks_downloaded = 1
		audio_chunks_downloaded = 1

		while True:

			if video_chunks_downloaded > 0:
				download_chunk(f"{base_url}_chunk_6_{i:05}.m4s", f"video_{i}.m4s")
				video_chunk_size = os.stat(f"video_{i}.m4s").st_size
				if video_chunk_size == 548:
					os.system(f"rm -f video_{i}.m4s")
					video_chunks_downloaded *= -1
				else:
					video_chunks_downloaded += 1

			if audio_chunks_downloaded > 0:
				download_chunk(f"{base_url}_chunk_1_{i:05}.m4s", f"audio_{i}.m4s")
				audio_chunk_size = os.stat(f"audio_{i}.m4s").st_size
				if audio_chunk_size == 548:
					os.system(f"rm -f audio_{i}.m4s")
					audio_chunks_downloaded *= -1
				else:
					audio_chunks_downloaded += 1

			if video_chunks_downloaded < 0 and audio_chunks_downloaded < 0:
				break

			i += 1

		video_chunks_downloaded *= -1
		audio_chunks_downloaded *= -1

		print(f"downloaded {video_chunks_downloaded} video chunks")
		print(f"downloaded {audio_chunks_downloaded} audio chunks")

		# check for chunk diff
		for i in range(video_chunks_downloaded):
			for j in range(video_chunks_downloaded):
				if i != j and filecmp.cmp(f"video_{i}.m4s", f"video_{j}.m4s"):
					print(f"equal video chunks {i} {j}")
					exit(1)

		for i in range(audio_chunks_downloaded):
			for j in range(audio_chunks_downloaded):
				if i != j and filecmp.cmp(f"audio_{i}.m4s", f"audio_{j}.m4s"):
					print(f"equal audio chunks {i} {j}")
					exit(1)

		video_chunks_list = ""
		for i in range(video_chunks_downloaded):
			video_chunks_list += f"video_{i}.m4s "

		audio_chunks_list = ""
		for i in range(audio_chunks_downloaded):
			audio_chunks_list += f"audio_{i}.m4s "

		# concat video chunks
		os.system(f"cat {video_chunks_list} >> video.m4s")

		# concat audio chunks
		os.system(f"cat {audio_chunks_list} >> audio.m4s")

		# convert from chunks to video
		os.system("ffmpeg -i video.m4s -c copy video.mp4")

		# convert from chunks to audio
		os.system("ffmpeg -i audio.m4s -c copy audio.mp4")

		# merge video and audio
		os.system(f"ffmpeg -i video.mp4 -i audio.mp4 -c copy {filename}")

		# cleanup
		os.system("rm -f *.m4s video.mp4 audio.mp4")


#  TODO: check for banned content and auto enable vpn
LIST = [

	# Кабанэри
	{
		"URL": "https://animego.org/anime/kabaneri-zheleznoy-kreposti-966",
		"AUDIO": "Профессиональный многоголосый",
		"SEASON": 0,
		"VPN": False
	},

	# Фрирен
	# {
	# 	"URL": "https://animego.org/anime/provozhayuschaya-v-posledniy-put-friren-2430",
	# 	"AUDIO": "Студийная Банда",
	# 	"SEASON": 0
	# },

	# Гены AI
	# {
	# 	"URL": "https://animego.org/anime/geny-iskusstvennogo-intellekta-2340",
	# 	"AUDIO": "AniLibria",
	# 	"SEASON": 0
	# },

	# Атака титанов (Сезон 1)
	# {
	# 	"URL": "https://ataka-titanov.com/1-sezon/",
	# 	"AUDIO": "Studio Band",
	# 	"SEASON": 1
	# },

	# Атака титанов (Сезон 2)
	# {
	# 	"URL": "https://ataka-titanov.com/2-sezon/",
	# 	"AUDIO": "",
	# 	"SEASON": 2
	# },

	# # Атака титанов (Сезон 3)
	# {
	# 	"URL": "https://ataka-titanov.com/3-sezon/",
	# 	"AUDIO": "",
	# 	"SEASON": 3
	# },

	# # Атака титанов (Сезон 4)
	# {
	# 	"URL": "https://ataka-titanov.com/4-sezon/",
	# 	"AUDIO": "",
	# 	"SEASON": 4
	# }

	# Токоийский гуль (Пинто)
	# {
	# 	"URL": "https://animego.org/anime/tokiyskiy-gul-pinto-246",
	# 	"AUDIO": "AniDUB",
	# 	"SEASON": 0,
	# 	"VPN": False
	# },

	# # Токоийский гуль (Джек)
	# {
	# 	"URL": "https://animego.org/anime/tokiyskiy-gul-dzhek-247",
	# 	"AUDIO": "AniLibria",
	# 	"SEASON": 0,
	# 	"VPN": False
	# },

	# # Токийский гуль (Сезон 1)
	# {
	# 	"URL": "https://animego.org/anime/tokyo-ghoul-sv1-243",
	# 	"AUDIO": "AniLibria",
	# 	"SEASON": 1,
	# 	"VPN": True
	# },

	# # Токийский гуль (Сезон 2)
	# {
	# 	"URL": "https://animego.org/anime/tokiyskiy-gul-2-244",
	# 	"AUDIO": "AniLibria",
	# 	"SEASON": 2,
	# 	"VPN": True
	# },

	# Токийский гуль (Сезон 3)
	# {
	# 	"URL": "https://animego.org/anime/tokyo-ghoul-re-245",
	# 	"AUDIO": "AniLibria",
	# 	"SEASON": 3,
	# 	"VPN": False
	# },

	# # Токийский гуль (Сезон 4)
	# {
	# 	"URL": "https://animego.org/anime/tokyo-ghoul-re-2nd-season-709",
	# 	"AUDIO": "AniLibria",
	# 	"SEASON": 4,
	# 	"VPN": False
	# },

	# # Человек бензопила
	# {
	# 	"URL": "https://animego.org/anime/chelovek-benzopila-2119",
	# 	"AUDIO": "Профессиональный многоголосый",
	# 	"SEASON": 0,
	# 	"VPN": False
	# }

	# Тетрадь смерти
	# {
	# 	"URL": "https://animego.org/anime/death-note-v2-95",
	# 	"AUDIO": "2x2",
	# 	"SEASON": 0,
	# 	"VPN": True
	# },

	# Тетрадь смерти (фильмы)
	# {
	# 	"URL": "https://animego.org/anime/tetrad-smerti-perezapis-glazami-boga-96",
	# 	"AUDIO": "AniDUB",
	# 	"SEASON": 0,
	# 	"VPN": True
	# },

	# Dr Stone (сезон 1)
	# {
	# 	"URL": "https://animego.org/anime/dr-stone-2v-1105",
	# 	"AUDIO": "Профессиональный многоголосый",
	# 	"SEASON": 1,
	# 	"VPN": True
	# },

	# Dr Stone (сезон 2)
	# {
	# 	"URL": "https://animego.org/anime/doktor-stoun-kamennye-voyny-1698",
	# 	"AUDIO": "Профессиональный многоголосый",
	# 	"SEASON": 2,
	# 	"VPN": True
	# }

	# Dr Stone (сезон 3)
	# ждем озвучку
	# {
	# 	"URL": "https://animego.org/anime/doktor-stoun-kamennye-voyny-1698",
	# 	"AUDIO": "Профессиональный многоголосый",
	# 	"SEASON": 1,
	# 	"VPN": True
	# }

	# One Piece
	#

	# Наруто
	# {
	# 	"URL": "https://animego.org/anime/naruto-102",
	# 	"AUDIO": "2x2",
	# 	"SEASON": 0,
	# 	"VPN": False
	# }

	# # Наруто Ураганные хроники
	# {
	# 	"URL": "https://animego.org/anime/naruto-uragannye-hroniki-103",
	# 	"AUDIO": "2x2",
	# 	"SEASON": 0,
	# 	"VPN": False
	# }

]

DIR = "."
for anime in LIST:
	URL, AUDIO, SEASON, VPN = anime.values()
	Downloader.download(URL, AUDIO, SEASON, DIR, VPN)
