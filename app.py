import streamlit as st
import pandas as pd
import re
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from textblob import TextBlob
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from st_aggrid import AgGrid, GridUpdateMode, DataReturnMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
import gensim
from gensim import corpora
import plotly.express as px

# Load API key from Streamlit secrets
api_key = st.secrets["YOUTUBE_API_KEY"]

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

# Function to perform sentiment analysis
def analyze_sentiment(comment):
    analysis = TextBlob(comment)
    if analysis.sentiment.polarity > 0:
        return 'Positive'
    elif analysis.sentiment.polarity == 0:
        return 'Neutral'
    else:
        return 'Negative'

# Function to scrape YouTube comments
def scrape_youtube_comments(api_key, video_id):
    youtube = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
    comments = []
    try:
        next_page_token = None
        page_count = 0
        progress_bar = st.progress(0)
        while True:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response["items"]:
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append([
                    comment["authorDisplayName"],
                    comment["textDisplay"],
                    comment["likeCount"],
                    comment["publishedAt"],
                    item["snippet"]["totalReplyCount"],
                    analyze_sentiment(comment["textDisplay"])
                ])

                if "replies" in item:
                    for reply in item["replies"]["comments"]:
                        reply_comment = reply["snippet"]
                        comments.append([
                            reply_comment["authorDisplayName"],
                            reply_comment["textDisplay"],
                            reply_comment["likeCount"],
                            reply_comment["publishedAt"],
                            0,
                            analyze_sentiment(reply_comment["textDisplay"])
                        ])

            if "nextPageToken" in response:
                next_page_token = response["nextPageToken"]
            else:
                break

            page_count += 1
            progress_bar.progress(min(page_count / 10, 1.0))

        df = pd.DataFrame(comments, columns=["Name", "Comment", "Likes", "Time", "Reply Count", "Sentiment"])
        total_comments = len(comments)
        return df, total_comments

    except HttpError as e:
        logging.error(f"HTTP error occurred: {e}")
        st.error(f"HTTP error occurred: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Error scraping comments: {e}")
        st.error(f"Error scraping comments: {e}")
        return None, None

# Function to generate a word cloud
def generate_word_cloud(text, stopwords=None, colormap='viridis', contour_color='steelblue'):
    wordcloud = WordCloud(width=800, height=400, background_color='white', stopwords=stopwords, colormap=colormap, contour_color=contour_color).generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    st.pyplot(plt)

# Function to filter comments
def filter_comments(df, filter_criteria):
    filtered_df = df.copy()
    if "sentiment" in filter_criteria:
        filtered_df = filtered_df[filtered_df["Sentiment"].isin(filter_criteria["sentiment"])]
    if "min_likes" in filter_criteria:
        filtered_df = filtered_df[filtered_df["Likes"] >= filter_criteria["min_likes"]]
    if "keywords" in filter_criteria:
        filtered_df = filtered_df[filtered_df["Comment"].str.contains('|'.join(filter_criteria["keywords"]), case=False)]
    if "start_date" in filter_criteria and "end_date" in filter_criteria:
        filtered_df['Time'] = pd.to_datetime(filtered_df['Time'])
        filtered_df = filtered_df[(filtered_df['Time'] >= filter_criteria["start_date"]) & (filtered_df['Time'] <= filter_criteria["end_date"])]
    return filtered_df

# Function to analyze comment length
def analyze_comment_length(df):
    comment_lengths = df["Comment"].str.len()
    st.write("Comment Length Statistics:")
    st.write(f"Average Length: {comment_lengths.mean():.2f} characters")
    st.write(f"Median Length: {comment_lengths.median()} characters")
    st.write(f"Maximum Length: {comment_lengths.max()} characters")
    st.write(f"Minimum Length: {comment_lengths.min()} characters")
    fig, ax = plt.subplots()
    sns.histplot(comment_lengths, kde=True, ax=ax)
    ax.set_title("Comment Length Distribution")
    st.pyplot(fig)

# Function to get top commenters
def get_top_commenters(df, by="comments", top_n=10):
    if by == "comments":
        top_commenters = df["Name"].value_counts().head(top_n)
    elif by == "likes":
        top_commenters = df.groupby("Name")["Likes"].sum().sort_values(ascending=False).head(top_n)
    else:
        st.error("Invalid option for 'by'. Choose 'comments' or 'likes'.")
        return
    st.write(f"Top {top_n} Commenters by {by.capitalize()}:")
    st.write(top_commenters)

# Function to export visualization
def export_visualization(fig, filename):
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    st.success(f"Visualization saved as {filename}")

# Function to analyze sentiment over time
def analyze_sentiment_over_time(df):
    df["Date"] = pd.to_datetime(df["Time"]).dt.date
    sentiment_over_time = df.groupby(["Date", "Sentiment"]).size().unstack(fill_value=0)
    fig = px.line(sentiment_over_time, title='Sentiment Over Time')
    st.plotly_chart(fig)

# Function to display an interactive data table
def display_interactive_table(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gridOptions = gb.build()
    AgGrid(df, gridOptions=gridOptions, enable_enterprise_modules=True, update_mode=GridUpdateMode.SELECTION_CHANGED, data_return_mode=DataReturnMode.FILTERED_AND_SORTED)

# Function to extract topics from comments
def extract_topics(df, num_topics=5, num_words=10):
    comments = df['Comment'].str.lower().str.split()
    dictionary = corpora.Dictionary(comments)
    corpus = [dictionary.doc2bow(comment) for comment in comments]
    lda_model = gensim.models.LdaMulticore(corpus, num_topics=num_topics, id2word=dictionary, passes=10, workers=2)
    topics = lda_model.print_topics(num_words=num_words)
    st.write("Extracted Topics:")
    for idx, topic in topics:
        st.write(f"Topic {idx + 1}: {topic}")

# Function to get trending videos
def get_trending_videos(api_key):
    youtube = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
    request = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode="US", maxResults=10)
    response = request.execute()
    videos = []
    for item in response["items"]:
        video = {
            "videoId": item["id"],
            "title": item["snippet"]["title"],
            "channelTitle": item["snippet"]["channelTitle"],
            "viewCount": item["statistics"].get("viewCount", 0),
            "likeCount": item["statistics"].get("likeCount", 0),
            "commentCount": item["statistics"].get("commentCount", 0)
        }
        videos.append(video)
    return videos

# Function to display video metadata
def display_video_metadata(video):
    st.write("Video Title:", video["title"])
    st.write("Channel Title:", video["channelTitle"])
    st.write("View Count:", video["viewCount"])
    st.write("Like Count:", video["likeCount"])
    st.write("Comment Count:", video["commentCount"])

# Function to calculate user engagement score
def calculate_engagement(df):
    df["EngagementScore"] = df["Likes"] + df["Reply Count"] * 2 + df["Sentiment"].apply(lambda x: 1 if x == 'Positive' else (-1 if x == 'Negative' else 0))
    return df

# Function to monitor API quota
def api_quota_monitor(api_key):
    youtube = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
    quota_request = youtube.videos().list(part="id", chart="mostPopular", regionCode="US")
    quota_response = quota_request.execute()
    return quota_response.get('quota_remaining', None)

# Streamlit App
st.title("YouTube Comment Scraper and Analyzer")

video_url = st.text_input("Enter YouTube video URL")
if st.button("Scrape Comments"):
    video_id = extract_video_id(video_url)
    if video_id:
        with st.spinner("Scraping comments..."):
            progress_bar = st.progress(0)
            df, total_comments = scrape_youtube_comments(api_key, video_id)
            progress_bar.progress(1)
            if df is None or total_comments is None:
                st.error("Error scraping comments. Please try again.")
            else:
                st.success(f"Scraping complete! Total Comments: {total_comments}")
                st.write(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Download CSV", data=csv, file_name="youtube_comments.csv", mime="text/csv")

                # Sentiment Analysis Visualization
                st.subheader("Sentiment Analysis")
                sentiment_counts = df['Sentiment'].value_counts()
                fig, ax = plt.subplots()
                ax.pie(sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%', startangle=140)
                ax.axis('equal')
                st.pyplot(fig)
                export_visualization(fig, "sentiment_analysis.png")

                # Generate Word Cloud
                st.subheader("Word Cloud")
                all_comments = ' '.join(df['Comment'])
                generate_word_cloud(all_comments)

                # Filter Comments
                st.subheader("Filter Comments")
                sentiment_filter = st.selectbox("Filter by Sentiment", ["All", "Positive", "Negative"])
                if sentiment_filter != "All":
                    df = df[df['Sentiment'] == sentiment_filter]

                min_likes_filter = st.number_input("Filter by Minimum Likes", min_value=0, step=1)
                if min_likes_filter > 0:
                    df = df[df["Likes"] >= min_likes_filter]

                keyword_filter = st.text_input("Filter by Keywords (separate by comma)")
                if keyword_filter:
                    keywords = [kw.strip() for kw in keyword_filter.split(",")]
                    df = df[df["Comment"].str.contains('|'.join(keywords), case=False)]

                start_date_filter = st.date_input("Start Date")
                end_date_filter = st.date_input("End Date")
                if start_date_filter and end_date_filter:
                    df = filter_comments(df, {"start_date": start_date_filter, "end_date": end_date_filter})

                st.write(df)

                # Comment Length Analysis
                st.subheader("Comment Length Analysis")
                analyze_comment_length(df)

                # Top Commenters
                st.subheader("Top Commenters")
                top_commenters_by_comments = st.checkbox("Top Commenters by Number of Comments")
                top_commenters_by_likes = st.checkbox("Top Commenters by Total Likes")
                top_n = st.number_input("Number of Top Commenters", min_value=1, value=10, step=1)

                if top_commenters_by_comments:
                    get_top_commenters(df, by="comments", top_n=top_n)

                if top_commenters_by_likes:
                    get_top_commenters(df, by="likes", top_n=top_n)

                # Sentiment Analysis Over Time
                st.subheader("Sentiment Analysis Over Time")
                analyze_sentiment_over_time(df)

                # Interactive Data Table
                st.subheader("Interactive Comment Table")
                display_interactive_table(df)

                # Topic Extraction
                st.subheader("Topic Extraction")
                extract_topics(df)

                # User Engagement Score
                st.subheader("User Engagement Score")
                df = calculate_engagement(df)
                st.write(df[["Name", "Comment", "EngagementScore"]].sort_values(by="EngagementScore", ascending=False))

# Display trending videos
st.header("Trending Videos")
trending_videos = get_trending_videos(api_key)
if trending_videos:
    video_selection = st.selectbox("Select a trending video", [f"{video['title']} (by {video['channelTitle']})" for video in trending_videos])
    selected_video = next(video for video in trending_videos if f"{video['title']} (by {video['channelTitle']})" == video_selection)
    display_video_metadata(selected_video)
    
    if st.button("Scrape Comments for Trending Video"):
        video_id = selected_video['videoId']
        with st.spinner("Scraping comments..."):
            progress_bar = st.progress(0)
            df, total_comments = scrape_youtube_comments(api_key, video_id)
            progress_bar.progress(1)
            if df is None or total_comments is None:
                st.error("Error scraping comments. Please try again.")
            else:
                st.success(f"Scraping complete! Total Comments: {total_comments}")
                st.write(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Download CSV", data=csv, file_name="youtube_comments.csv", mime="text/csv")

                # Sentiment Analysis Visualization
                st.subheader("Sentiment Analysis")
                sentiment_counts = df['Sentiment'].value_counts()
                fig, ax = plt.subplots()
                ax.pie(sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%', startangle=140)
                ax.axis('equal')
                st.pyplot(fig)
                export_visualization(fig, "sentiment_analysis.png")

                # Generate Word Cloud
                st.subheader("Word Cloud")
                all_comments = ' '.join(df['Comment'])
                generate_word_cloud(all_comments)

                # Filter Comments
                st.subheader("Filter Comments")
                sentiment_filter = st.selectbox("Filter by Sentiment", ["All", "Positive", "Negative"])
                if sentiment_filter != "All":
                    df = df[df['Sentiment'] == sentiment_filter]

                min_likes_filter = st.number_input("Filter by Minimum Likes", min_value=0, step=1)
                if min_likes_filter > 0:
                    df = df[df["Likes"] >= min_likes_filter]

                keyword_filter = st.text_input("Filter by Keywords (separate by comma)")
                if keyword_filter:
                    keywords = [kw.strip() for kw in keyword_filter.split(",")]
                    df = df[df["Comment"].str.contains('|'.join(keywords), case=False)]

                start_date_filter = st.date_input("Start Date")
                end_date_filter = st.date_input("End Date")
                if start_date_filter and end_date_filter:
                    df = filter_comments(df, {"start_date": start_date_filter, "end_date": end_date_filter})

                st.write(df)

                # Comment Length Analysis
                st.subheader("Comment Length Analysis")
                analyze_comment_length(df)

                # Top Commenters
                st.subheader("Top Commenters")
                top_commenters_by_comments = st.checkbox("Top Commenters by Number of Comments")
                top_commenters_by_likes = st.checkbox("Top Commenters by Total Likes")
                top_n = st.number_input("Number of Top Commenters", min_value=1, value=10, step=1)

                if top_commenters_by_comments:
                    get_top_commenters(df, by="comments", top_n=top_n)

                if top_commenters_by_likes:
                    get_top_commenters(df, by="likes", top_n=top_n)

                # Sentiment Analysis Over Time
                st.subheader("Sentiment Analysis Over Time")
                analyze_sentiment_over_time(df)

                # Interactive Data Table
                st.subheader("Interactive Comment Table")
                display_interactive_table(df)

                # Topic Extraction
                st.subheader("Topic Extraction")
                extract_topics(df)

                # User Engagement Score
                st.subheader("User Engagement Score")
                df = calculate_engagement(df)
                st.write(df[["Name", "Comment", "EngagementScore"]].sort_values(by="EngagementScore", ascending=False))

# API Quota Monitor
st.sidebar.subheader("API Quota Monitor")
quota_remaining = api_quota_monitor(api_key)
if quota_remaining:
    st.sidebar.write(f"API Quota Remaining: {quota_remaining}")
else:
    st.sidebar.write("Unable to retrieve API quota information.")