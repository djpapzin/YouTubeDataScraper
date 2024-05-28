import streamlit as st
from apiclient.discovery import build
import pandas as pd
import re

# Function to extract video ID from YouTube URL
def extract_video_id(url):
    # Remove query string if present
    url = url.split("?")[0]
    video_id = re.search(r"(?<=v=)[^&#]+", url)
    if video_id is None:
        video_id = re.search(r"(?<=be/)[^&#]+", url)
    return video_id.group(0) if video_id else None

# Function to scrape YouTube comments
def scrape_youtube_comments(api_key, video_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    comments = []

    def get_comments(youtube, video_id, next_page_token):
        results = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            maxResults=100,
            pageToken=next_page_token
        ).execute()

        for item in results["items"]:
            comment = item["snippet"]["topLevelComment"]["snippet"]
            comments.append([
                comment["authorDisplayName"],
                comment["textDisplay"],
                comment["likeCount"],
                comment["publishedAt"],
                item["snippet"]["totalReplyCount"]
            ])

        return results.get("nextPageToken")

    next_page_token = None
    while True:
        next_page_token = get_comments(youtube, video_id, next_page_token)
        if not next_page_token:
            break

    df = pd.DataFrame(comments, columns=["Name", "Comment", "Likes", "Time", "Reply Count"])
    return df

# Streamlit app
st.title("YouTube Data Scraper")

api_key = st.text_input("Enter your YouTube API Key")
video_url = st.text_input("Enter YouTube Video URL")

if st.button("Scrape Comments"):
    video_id = extract_video_id(video_url)
    if video_id:
        with st.spinner("Scraping comments..."):
            df = scrape_youtube_comments(api_key, video_id)
            st.success("Scraping complete!")
            st.write(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="Download CSV", data=csv, file_name="youtube_comments.csv", mime="text/csv")
    else:
        st.error("Invalid YouTube URL")
