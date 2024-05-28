# YouTubeDataScraper

A tool to scrape YouTube video data including comments, likes, and more.

## Features
- Count
- Video Description
- Video Comments
- Video Likes Count
- Subscribers Count
- Time And Date
- Video Comments Reply

## Upcoming Features
- Extracting more video metadata (views, duration, etc.)
- Fetching video details from a playlist
- Sentiment analysis for comments
- Enhanced output formats (Excel, Database)

## How to Setup
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/YouTubeDataScraper.git
   cd YouTubeDataScraper
   ```

2. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup API Key and Video ID**:
   - Create a file named `config.data` and add your API key and video ID:
     ```
     [cred]
     id = YOUR_API_KEY
     hash = VIDEO_ID
     ```

## How to Use
1. **Run the Setup Script**:
   ```bash
   python Setup.py
   ```

2. **Run the Scraper**:
   ```bash
   python YT_Scraper.py
   ```

3. **Check the Output**:
   - The final output will be stored in a `CSV` file in the same directory.

## Requirements
- Python 3.5+
- Pandas
- Google API Client

## Supported Devices
- Linux
- Windows
- MacOS
- BSD
- Termux

## Contact
For any help, support, suggestions, or requests, contact me on [Gmail](mailto:your-email@gmail.com) / [Telegram](https://t.me/YourTelegramUsername).

## Disclaimer
This is a research project. Use it at your own risk. I am not responsible for any misuse of this tool.
```

### Next Steps
1. **Make the Initial Enhancements**:
   - Start by making some of the suggested enhancements or any other features you have in mind.

2. **Push the Changes**:
   - Commit and push your changes to your GitHub repository regularly.

3. **Collaborate and Share**:
   - Share your repository link with collaborators or friends who might be interested in contributing.

By following these steps, you'll have your own customized version of the YouTube data scraper project, ready for further development and enhancements.