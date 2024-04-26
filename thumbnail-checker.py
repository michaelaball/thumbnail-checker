import os
import csv
from googleapiclient.discovery import build
from google.cloud import vision

# YouTube API Setup
DEVELOPER_KEY = '<PUT YOUR KEY HERE>'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

# Google Cloud Vision Setup
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = './<YOUR APP CREDENTIALS HERE>.json'
client = vision.ImageAnnotatorClient()


def get_channel_videos(channel_id):
    videos = []
    request = youtube.search().list(
        part="id",
        channelId=channel_id,
        maxResults=50,  # Max allowed by the API
        order="viewCount",  # Sort by view count
        type="video"
    )
    while request:
        response = request.execute()
        if 'items' not in response:
            print("No video items found in response.")
            break
        video_ids = [item['id']['videoId'] for item in response["items"]]
        videos.extend(video_ids)
        request = youtube.search().list_next(request, response)
    return videos


def get_video_details(video_id):
    response = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    ).execute()
    if 'items' not in response or not response['items']:
        print(f"No details found for video ID: {video_id}")
        return None
    video_details = response['items'][0]
    # Using 'high' resolution thumbnail
    thumbnail_url = video_details['snippet']['thumbnails'].get('high', {}).get('url')
    if not thumbnail_url:  # Fallback to 'default' if 'high' is not available
        thumbnail_url = video_details['snippet']['thumbnails']['default']['url']
    return {
        'title': video_details['snippet']['title'],
        'views': int(video_details['statistics']['viewCount']),
        'thumbnail_url': thumbnail_url,
        'video_url': f"https://www.youtube.com/watch?v={video_id}"
    }


def analyze_thumbnail(url):
    image = vision.Image()
    image.source.image_uri = url

    response = client.safe_search_detection(image=image)
    if response.error.message:
        raise Exception(f"Error processing image: {response.error.message}")
    safe = response.safe_search_annotation
    return {
        "Adult": safe.adult.name,
        "Spoof": safe.spoof.name,
        "Medical": safe.medical.name,
        "Violence": safe.violence.name,
        "Racy": safe.racy.name
    }


def write_to_csv(video_data, filename='youtube_videos_report.csv'):
    if not video_data:
        print("No video data to write.")
        return
    keys = video_data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(video_data)


def main():
    channel_id = 'UCE7rRhCrEW8OxA6tpAye1kg'
    print("Fetching video IDs...")
    video_ids = get_channel_videos(channel_id)
    print(f"Found {len(video_ids)} videos.")

    video_data = []
    for video_id in video_ids:
        print(f"Processing video ID: {video_id}")
        details = get_video_details(video_id)
        if details:
            safe_search = analyze_thumbnail(details['thumbnail_url'])
            details.update(safe_search)
            video_data.append(details)

    # Sort the data by views in descending order
    sorted_video_data = sorted(video_data, key=lambda x: x['views'], reverse=True)
    write_to_csv(sorted_video_data)
    print("Video data has been written to youtube_videos_report.csv")



if __name__ == '__main__':
    main()