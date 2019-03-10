import os
from googleapiclient.discovery import build

DEVELOPER_KEY = os.environ['DEV_KEY']

def youtube_list(channel_id, num_pages=1):
    if num_pages > 10:
        raise ValueError('Google caps results at 500. Request less pages.')

    # See https://developers.google.com/youtube/v3/docs/search/list
    youtube = build('youtube', 'v3', developerKey=DEVELOPER_KEY)

    kwargs = {
        'part': 'id',
        'channelId': channel_id,
        'order': 'viewCount',
        'maxResults': 50,
        'videoCaption': 'closedCaption',
        'type': 'video',
    }

    page_token = None
    vid_ids = []
    for _ in range(num_pages):
        if page_token is not None:
            kwargs['pageToken'] = page_token

        search_response = youtube.search().list(**kwargs).execute()

        page_token = search_response.get('nextPageToken')
        for search_result in search_response.get('items', []):
            if search_result['id']['kind'] == 'youtube#video':
                vid_ids.append(search_result['id']['videoId'])

    return vid_ids
