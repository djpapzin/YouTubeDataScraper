# -*- coding: utf-8 -*-
#!/bin/env python3
# Telegram Group: http://t.me/cyberclans
# Please give me credits if you use any codes from here.

from apiclient.discovery import build
import pandas as pd
import configparser

# Read config.data for API Key and Video ID
cpass = configparser.RawConfigParser()
cpass.read('config.data')

Api_Key = cpass.get('cred', 'id')
Video_ID = cpass.get('cred', 'hash')

youtube = build('youtube', 'v3', developerKey=Api_Key)

List = [['Name', 'Comment', 'Likes', 'Time', 'Reply Count']]

def scrape_all_with_replies():
    data = youtube.commentThreads().list(part='snippet', videoId=Video_ID, maxResults='100', textFormat="plainText").execute()

    for i in data["items"]:
        name = i["snippet"]['topLevelComment']["snippet"]["authorDisplayName"]
        comment = i["snippet"]['topLevelComment']["snippet"]["textDisplay"]
        likes = i["snippet"]['topLevelComment']["snippet"]['likeCount']
        published_at = i["snippet"]['topLevelComment']["snippet"]['publishedAt']
        replies = i["snippet"]['totalReplyCount']

        List.append([name, comment, likes, published_at, replies])

        total_reply_count = i["snippet"]['totalReplyCount']

        if total_reply_count > 0:
            parent = i["snippet"]['topLevelComment']["id"]
            data2 = youtube.comments().list(part='snippet', maxResults='100', parentId=parent, textFormat="plainText").execute()

            for j in data2["items"]:
                name = j["snippet"]["authorDisplayName"]
                comment = j["snippet"]["textDisplay"]
                likes = j["snippet"]['likeCount']
                published_at = j["snippet"]['publishedAt']
                replies = ""

                List.append([name, comment, likes, published_at, replies])

    while "nextPageToken" in data:
        data = youtube.commentThreads().list(part='snippet', videoId=Video_ID, pageToken=data["nextPageToken"], maxResults='100', textFormat="plainText").execute()

        for i in data["items"]:
            name = i["snippet"]['topLevelComment']["snippet"]["authorDisplayName"]
            comment = i["snippet"]['topLevelComment']["snippet"]["textDisplay"]
            likes = i["snippet"]['topLevelComment']["snippet"]['likeCount']
            published_at = i["snippet"]['topLevelComment']["snippet"]['publishedAt']
            replies = i["snippet"]['totalReplyCount']

            List.append([name, comment, likes, published_at, replies])

            total_reply_count = i["snippet"]['totalReplyCount']

            if total_reply_count > 0:
                parent = i["snippet"]['topLevelComment']["id"]
                data2 = youtube.comments().list(part='snippet', maxResults='100', parentId=parent, textFormat="plainText").execute()

                for j in data2["items"]:
                    name = j["snippet"]["authorDisplayName"]
                    comment = j["snippet"]["textDisplay"]
                    likes = j["snippet"]['likeCount']
                    published_at = j["snippet"]['publishedAt']
                    replies = ''

                    List.append([name, comment, likes, published_at, replies])

    df = pd.DataFrame({'Name': [i[0] for i in List], 'Comment': [i[1] for i in List], 'Likes': [i[2] for i in List], 'Time': [i[3] for i in List], 'Reply Count': [i[4] for i in List]})

    df.to_csv('YT-Scrape-Result.csv', index=False, header=False)

    return "Successful! Check the CSV file that you have just created."

scrape_all_with_replies()
