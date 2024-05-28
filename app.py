import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import re
from dotenv import load_dotenv
import os
import logging
import subprocess
subprocess.call(["pip", "install", "google-api-python-client"])
from apiclient.discovery import build

# Load API key from .env file
load_dotenv()
api_key = os.getenv('YOUTUBE_API_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to extract video ID from YouTube URL
def extract_video_id(url):
    patterns = [
        r"(?<=v=)[^&]+",
        r"(?<=be\/)[^?]+",
        r"(?<=embed\/)[^\"?]+",
        r"(?<=youtu.be\/)[^\"?]+"
    ]
    for pattern in patterns:
        video_id = re.search(pattern, url)
        if video_id:
            return video_id.group(0)
    return None

# Function to scrape YouTube comments
def scrape_youtube_comments(api_key, video_id):
    youtube = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
    comments = []

    try:
        # Retrieve video comments in pages
        next_page_token = None
        while True:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token
            )
            response = request.execute()

            # Add comments to the list
            for item in response["items"]:
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append([
                    comment["authorDisplayName"],
                    comment["textDisplay"],
                    comment["likeCount"],
                    comment["publishedAt"],
                    item["snippet"]["totalReplyCount"]
                ])

                # Add replies to the list
                if "replies" in item:
                    for reply in item["replies"]["comments"]:
                        reply_comment = reply["snippet"]
                        comments.append([
                            reply_comment["authorDisplayName"],
                            reply_comment["textDisplay"],
                            reply_comment["likeCount"],
                            reply_comment["publishedAt"],
                            0  # Replies do not have replies
                        ])

            # Check if there are more pages of comments
            if "nextPageToken" in response:
                next_page_token = response["nextPageToken"]
            else:
                break

        # Create a DataFrame from the comments list
        df = pd.DataFrame(comments, columns=["Name", "Comment", "Likes", "Time", "Reply Count"])
        total_comments = len(comments)

        return df, total_comments

    except Exception as e:
        logging.error(f"Error scraping comments: {e}")
        return None, None

# Streamlit app
st.title("YouTube Data Scraper")
video_url = st.text_input("Enter YouTube Video URL")

if st.button("Scrape Comments"):
    video_id = extract_video_id(video_url)
    if video_id:
        with st.spinner("Scraping comments..."):
            df, total_comments = scrape_youtube_comments(api_key, video_id)
            if df is None or total_comments is None:
                st.error("Error scraping comments. Please try again.")
            else:
                st.success(f"Scraping complete! Total Comments: {total_comments}")
                st.write(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Download CSV", data=csv, file_name="youtube_comments.csv", mime="text/csv")
    else:
        st.error("Invalid YouTube URL")
