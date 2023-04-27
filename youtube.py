import os
import requests
import xmltodict
from googleapiclient.discovery import build

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")



youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY, credentials=None)

def get_video_id(url):
    if "watch?v=" in url:
        return url.split("watch?v=")[1][:11]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1][:11]
    return None

def get_captions(video_id):
    api_key = "YOUTUBE_API_KEY" # replace with your actual API key
    url = f"https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        captions_dict = response.json()
        if "items" in captions_dict:
            captions_text = ""
            for caption in captions_dict["items"]:
                if caption["snippet"]["language"] == "en":
                    caption_url = caption["snippet"]["url"]
                    caption_response = requests.get(caption_url)
                    if caption_response.status_code == 200:
                        xml = caption_response.content.decode("utf-8")
                        captions_dict = xmltodict.parse(xml)
                        for caption in captions_dict["transcript"]["text"]:
                            captions_text += caption["#text"] + " "
            return captions_text.strip()
    return ""

