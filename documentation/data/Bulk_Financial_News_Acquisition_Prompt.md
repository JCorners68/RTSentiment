# Bulk Financial News Acquisition Strategy

## Overview
Create a data pipeline to collect large volumes of historical financial news from free or low-cost sources, focusing on quantity over pre-analyzed sentiment (since we have FinBERT for analysis). Target sources with minimal API limitations that allow bulk downloading or efficient scraping.

## Target Sources

### Internet Archive (Wayback Machine)
- **Strategy**: Use the Wayback Machine API to access archived versions of financial news sites
- **Implementation**:
  1. Identify key financial news websites (CNBC, MarketWatch, Yahoo Finance, etc.)
  2. Use the Wayback CDX Server API to find all archived snapshots
  3. Download HTML content from key dates (daily/weekly snapshots)
  4. Extract article text, publication dates, and tickers using custom parsers
  5. Example API call: `https://web.archive.org/cdx/search/cdx?url=finance.yahoo.com&matchType=domain&limit=1000&from=20180101&to=20230101`

### Financial News RSS Archives
- **Strategy**: Collect historical RSS feed data from financial news sources
- **Implementation**:
  1. Identify financial news sites with extensive RSS archives
  2. Use tools like rssdb.org or archive.org to access historical RSS feeds
  3. Extract article metadata, links, and summaries
  4. Follow links to full articles where available

### SEC EDGAR Database
- **Strategy**: Mine SEC filings for company news, earnings reports, and official disclosures
- **Implementation**:
  1. Use SEC EDGAR API to access all public company filings
  2. Focus on 8-K forms (current reports), earnings releases (10-Q, 10-K)
  3. Extract plain text from key sections using pattern matching
  4. Example: `https://www.sec.gov/Archives/edgar/daily-index/`

### Google News Archive
- **Strategy**: Use Google News advanced search with date filters for historical news retrieval
- **Implementation**:
  1. Create automated search queries for ticker symbols + date ranges
  2. Use custom scraper to extract article headlines, snippets, and source URLs
  3. Follow links to original sources where possible
  4. Implement date range batching (3-month periods) to maximize coverage

### Financial News APIs with Free Tiers
- **Strategy**: Utilize free tiers of multiple news APIs, rotating between them to maximize volume
- **Implementation**:
  1. Sign up for free tiers of multiple services:
     - News API (100 requests/day free)
     - Marketaux Financial News API (free tier)
     - Yahoo Finance API (unofficial)
     - Seeking Alpha API (limited free access)
  2. Implement API rotation to avoid rate limits
  3. Use multiple developer accounts where permitted

### Academic Datasets
- **Strategy**: Source financial news datasets from academic repositories
- **Implementation**:
  1. Search repositories like Kaggle, Harvard Dataverse, and UCI ML Repository
  2. Look for financial news datasets used in research papers
  3. Example datasets:
     - Financial Phrasebank
     - Reuters-21578 Financial News
     - Bloomberg Financial News Dataset (academic access)

### Social Media Archive Projects
- **Strategy**: Access archived financial discussions from Reddit, Twitter, etc.
- **Implementation**:
  1. Use Pushshift API for Reddit archive data
  2. Access Twitter Archive projects
  3. Focus on financial subreddits: r/investing, r/stocks, r/wallstreetbets
  4. Filter content by ticker mentions and financial terms

## Technical Implementation

### 1. Wayback Machine Crawler

```python
import requests
import time
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def get_wayback_snapshots(domain, start_date, end_date, limit=1000):
    """Get list of snapshots from Wayback Machine for a domain in a date range."""
    cdx_api_url = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": domain,
        "matchType": "domain",
        "limit": limit,
        "from": start_date,
        "to": end_date,
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,urlkey"
    }
    
    response = requests.get(cdx_api_url, params=params)
    if response.status_code != 200:
        return []
    
    # Parse results and convert to DataFrame
    snapshots = response.json()
    if not snapshots or len(snapshots) <= 1:  # Check if there's data beyond header row
        return []
    
    # First row contains column headers
    headers = snapshots[0]
    data = snapshots[1:]
    
    df = pd.DataFrame(data, columns=headers)
    
    # Filter for HTML content and successful responses
    df = df[(df['mimetype'] == 'text/html') & (df['statuscode'] == '200')]
    
    # Only keep article pages (filter out homepage, section pages, etc.)
    # Customize for each domain to identify article URL patterns
    if domain == 'finance.yahoo.com':
        df = df[df['original'].str.contains('/news/')]
    elif domain == 'cnbc.com':
        df = df[df['original'].str.contains('/2020/') | df['original'].str.contains('/2021/')]
    
    return df

def download_wayback_content(snapshot_url, timestamp):
    """Download content from Wayback Machine."""
    wayback_url = f"https://web.archive.org/web/{timestamp}/{snapshot_url}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(wayback_url, headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Error downloading {wayback_url}: {e}")
        return None

def extract_article_content(html, domain):
    """Extract article content from HTML using domain-specific extractors."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Domain-specific content extraction
    if domain == 'finance.yahoo.com':
        # Extract Yahoo Finance article content
        title_element = soup.find('h1')
        title = title_element.text if title_element else ""
        
        date_element = soup.find('time')
        date = date_element.get('datetime') if date_element else ""
        
        content_div = soup.find('div', {'class': 'caas-body'})
        paragraphs = content_div.find_all('p') if content_div else []
        content = ' '.join([p.text for p in paragraphs])
        
        # Extract ticker symbols if present
        tickers = []
        ticker_elements = soup.find_all('a', {'class': 'caas-header-linkcard'})
        for element in ticker_elements:
            ticker = element.text.strip()
            if ticker.isupper() and len(ticker) < 6:  # Simple validation for ticker symbols
                tickers.append(ticker)
        
        return {
            'title': title,
            'date': date,
            'content': content,
            'tickers': tickers
        }
    
    # Add more domain-specific extractors here
    
    # Generic extractor as fallback
    title_element = soup.find('h1')
    title = title_element.text if title_element else ""
    
    paragraphs = soup.find_all('p')
    content = ' '.join([p.text for p in paragraphs])
    
    return {
        'title': title,
        'date': '',  # No reliable way to extract date with generic extractor
        'content': content,
        'tickers': []
    }

def process_domain(domain, start_date, end_date, output_file, max_articles=1000):
    """Process a domain to extract articles from Wayback Machine."""
    print(f"Processing {domain} from {start_date} to {end_date}")
    
    # Get snapshots
    snapshots = get_wayback_snapshots(domain, start_date, end_date)
    print(f"Found {len(snapshots)} snapshots")
    
    # Process snapshots
    articles = []
    for i, (_, row) in enumerate(snapshots.iterrows()):
        if i >= max_articles:
            break
            
        if i % 10 == 0:
            print(f"Processing snapshot {i+1}/{min(len(snapshots), max_articles)}")
        
        # Download content
        html = download_wayback_content(row['original'], row['timestamp'])
        if not html:
            continue
            
        # Extract article
        article = extract_article_content(html, domain)
        if not article['title'] or len(article['content']) < 100:
            continue  # Skip articles with no title or very short content
            
        # Add metadata
        article['url'] = row['original']
        article['timestamp'] = row['timestamp']
        article['domain'] = domain
        
        articles.append(article)
        
        # Respect Wayback Machine rate limits
        time.sleep(1)
    
    # Save to file
    df = pd.DataFrame(articles)
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} articles to {output_file}")

# Example usage
domains_to_process = [
    'finance.yahoo.com',
    'cnbc.com',
    'marketwatch.com',
    'reuters.com',
    'bloomberg.com',
    'fool.com',
    'investing.com'
]

for domain in domains_to_process:
    process_domain(
        domain=domain,
        start_date='20200101',  # January 1, 2020
        end_date='20210101',    # January 1, 2021
        output_file=f'wayback_{domain.replace(".", "_")}_2020.csv',
        max_articles=500
    )
```

### 2. SEC EDGAR Filings Extractor

```python
import requests
import zipfile
import io
import re
import os
import pandas as pd
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

def download_daily_index(date):
    """Download daily index file from SEC EDGAR."""
    # Format: YYYY/QTR{1-4}/form.YYYYMMDD.idx
    year = date[:4]
    month = int(date[4:6])
    qtr = (month - 1) // 3 + 1
    
    url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{qtr}/form.{date}.idx"
    headers = {
        'User-Agent': 'FinancialNewsResearch contact@example.com'  # Replace with your info
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to download index for {date}: {response.status_code}")
        return None
        
    return response.text

def parse_daily_index(index_content):
    """Parse daily index file to find 8-K and earnings related filings."""
    if not index_content:
        return []
        
    # Skip header section
    data_section = index_content.split('--------------')[1]
    
    # Parse entries
    entries = []
    for line in data_section.strip().split('\n'):
        parts = line.split('|')
        if len(parts) < 5:
            continue
            
        form_type = parts[2].strip()
        company = parts[1].strip()
        cik = parts[0].strip()
        file_name = parts[4].strip()
        
        # Filter for relevant filings (8-K, 10-Q, 10-K)
        if form_type in ['8-K', '10-Q', '10-K']:
            entries.append({
                'cik': cik,
                'company': company,
                'form_type': form_type,
                'file_name': file_name
            })
    
    return entries

def download_filing(file_name):
    """Download a specific filing from SEC EDGAR."""
    url = f"https://www.sec.gov/Archives/{file_name}"
    headers = {
        'User-Agent': 'FinancialNewsResearch contact@example.com'  # Replace with your info
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to download filing {file_name}: {response.status_code}")
        return None
        
    return response.text

def extract_filing_text(filing_content, form_type):
    """Extract relevant text from filing based on form type."""
    if not filing_content:
        return ""
        
    # For 8-K filings, focus on Item sections
    if form_type == '8-K':
        # Try to find Item sections (varies by filing format)
        items = re.findall(r'(Item\s+[1-9]\..*?)(?=Item\s+[1-9]\.|$)', filing_content, re.DOTALL)
        if items:
            return "\n\n".join(items)
    
    # For 10-Q/10-K, focus on MD&A and financial results
    if form_type in ['10-Q', '10-K']:
        # Try to extract MD&A section
        mda = re.search(r'(Management\'s Discussion and Analysis.*?)\n(?=[A-Z]{2,})', filing_content, re.DOTALL | re.IGNORECASE)
        results = re.search(r'(Results of Operations.*?)\n(?=[A-Z]{2,})', filing_content, re.DOTALL | re.IGNORECASE)
        
        sections = []
        if mda:
            sections.append(mda.group(1))
        if results:
            sections.append(results.group(1))
            
        if sections:
            return "\n\n".join(sections)
    
    # Fallback: just return first 5000 characters
    return filing_content[:5000]

def extract_ticker_from_company(company_name):
    """Try to extract ticker symbol from company name."""
    # Common pattern: "Company Name (Ticker)"
    ticker_match = re.search(r'\(([A-Z]{1,5})\)$', company_name)
    if ticker_match:
        return ticker_match.group(1)
    return None

def process_sec_filings(start_date, end_date, output_dir):
    """Process SEC filings between given dates."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate list of dates to process (yyyymmdd format)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.date_range(start, end).strftime('%Y%m%d').tolist()
    
    all_filings = []
    
    for date in dates:
        print(f"Processing SEC filings for {date}")
        
        # Get daily index
        index_content = download_daily_index(date)
        if not index_content:
            continue
            
        # Parse index to find relevant filings
        filings = parse_daily_index(index_content)
        print(f"Found {len(filings)} relevant filings")
        
        # Process each filing
        for i, filing in enumerate(filings):
            if i % 10 == 0:
                print(f"Processing filing {i+1}/{len(filings)}")
                
            # Download filing
            content = download_filing(filing['file_name'])
            if not content:
                continue
                
            # Extract relevant text
            text = extract_filing_text(content, filing['form_type'])
            if not text or len(text) < 200:
                continue
                
            # Extract ticker if possible
            ticker = extract_ticker_from_company(filing['company'])
            
            # Store filing data
            filing_data = {
                'cik': filing['cik'],
                'company': filing['company'],
                'form_type': filing['form_type'],
                'file_name': filing['file_name'],
                'date': date,
                'ticker': ticker,
                'content': text
            }
            
            all_filings.append(filing_data)
            
            # Respect SEC.gov rate limits
            time.sleep(0.1)
    
    # Save all filings to CSV
    df = pd.DataFrame(all_filings)
    output_file = os.path.join(output_dir, f"sec_filings_{start_date}_to_{end_date}.csv")
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} filings to {output_file}")

# Example usage
process_sec_filings('20200101', '20200131', 'sec_filings')
```

### 3. Reddit Financial Data Collector

```python
import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta

def get_pushshift_data(subreddit, start_date, end_date, limit=1000):
    """Get Reddit data from Pushshift API."""
    start_timestamp = int(datetime.strptime(start_date, '%Y%m%d').timestamp())
    end_timestamp = int(datetime.strptime(end_date, '%Y%m%d').timestamp())
    
    url = "https://api.pushshift.io/reddit/submission/search/"
    params = {
        "subreddit": subreddit,
        "after": start_timestamp,
        "before": end_timestamp,
        "sort": "desc",
        "sort_type": "created_utc",
        "size": limit
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()['data']
        else:
            print(f"Error: Received status code {response.status_code}")
            return []
    except Exception as e:
        print(f"Error accessing Pushshift API: {e}")
        return []

def extract_ticker_symbols(text):
    """Extract potential ticker symbols from text using pattern matching."""
    import re
    
    # Look for common ticker patterns (1-5 uppercase letters, often with $ prefix)
    ticker_pattern = r'\$([A-Z]{1,5})\b|\b([A-Z]{1,5})\b'
    matches = re.findall(ticker_pattern, text)
    
    # Flatten and filter matches
    potential_tickers = []
    for match in matches:
        for group in match:
            if group and len(group) >= 1:
                potential_tickers.append(group)
    
    # Filter out common English words and abbreviations often mistaken for tickers
    common_words = {'A', 'I', 'AT', 'BE', 'DO', 'GO', 'IN', 'IS', 'IT', 'ON', 'OR', 'TO', 'CEO', 'CFO', 'CTO', 'COO', 'IPO'}
    filtered_tickers = [t for t in potential_tickers if t not in common_words]
    
    return list(set(filtered_tickers))  # Remove duplicates

def collect_financial_reddit_data(subreddits, start_date, end_date, output_dir):
    """Collect financial data from multiple subreddits."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Break down date range into smaller chunks (30 days each) to avoid API limits
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    current_start = start
    
    all_posts = []
    
    while current_start < end:
        current_end = min(current_start + timedelta(days=30), end)
        
        chunk_start = current_start.strftime('%Y%m%d')
        chunk_end = current_end.strftime('%Y%m%d')
        
        print(f"Processing {chunk_start} to {chunk_end}")
        
        for subreddit in subreddits:
            print(f"Collecting data from r/{subreddit}")
            
            # Get submissions from subreddit
            submissions = get_pushshift_data(subreddit, chunk_start, chunk_end)
            print(f"Found {len(submissions)} submissions")
            
            # Process submissions
            for submission in submissions:
                # Extract basic metadata
                post_data = {
                    'id': submission.get('id'),
                    'subreddit': subreddit,
                    'title': submission.get('title', ''),
                    'selftext': submission.get('selftext', ''),
                    'created_utc': submission.get('created_utc'),
                    'author': submission.get('author', '[deleted]'),
                    'score': submission.get('score', 0),
                    'url': submission.get('url', '')
                }
                
                # Extract potential ticker symbols from title and text
                full_text = post_data['title'] + ' ' + post_data['selftext']
                tickers = extract_ticker_symbols(full_text)
                post_data['tickers'] = tickers
                
                all_posts.append(post_data)
            
            # Respect API rate limits
            time.sleep(1)
        
        # Move to next time chunk
        current_start = current_end
    
    # Save to CSV
    df = pd.DataFrame(all_posts)
    output_file = os.path.join(output_dir, f"reddit_financial_{start_date}_to_{end_date}.csv")
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} posts to {output_file}")

# Example usage
financial_subreddits = [
    'investing',
    'stocks',
    'wallstreetbets',
    'SecurityAnalysis',
    'finance',
    'StockMarket',
    'options',
    'forex',
    'personalfinance',
    'financialindependence'
]

collect_financial_reddit_data(financial_subreddits, '20200101', '20210101', 'reddit_data')
```

## Batch Processing Strategy

To efficiently process large volumes of collected data:

1. **Date Partitioning**: Process data in monthly batches to manage memory usage
2. **Deduplication Pipeline**:
   ```python
   def compute_content_hash(content):
       """Compute stable hash for content to detect duplicates."""
       import hashlib
       # Normalize text (lowercase, remove excessive whitespace)
       normalized = ' '.join(content.lower().split())
       # Hash the content
       return hashlib.md5(normalized.encode('utf-8')).hexdigest()
   
   def batch_deduplicate(input_file, output_file):
       """Deduplicate articles based on content similarity."""
       df = pd.read_csv(input_file)
       
       # Compute hashes
       df['content_hash'] = df['content'].apply(compute_content_hash)
       
       # Remove duplicates
       df_unique = df.drop_duplicates(subset=['content_hash'])
       
       # Log deduplication metrics
       original_count = len(df)
       unique_count = len(df_unique)
       duplicates = original_count - unique_count
       
       print(f"Deduplicated {input_file}:")
       print(f"Original: {original_count}, Unique: {unique_count}")
       print(f"Removed {duplicates} duplicates ({duplicates/original_count:.1%})")
       
       # Save deduplicated data
       df_unique.to_csv(output_file, index=False)
   ```

3. **Incremental Processing**: Track processed files in a metadata database
4. **Error Recovery**: Implement checkpointing to resume from failures

## Storage Optimization

1. **Partitioning Strategy**:
   - Organize data by year/month/source
   - `financial_news/2023/01/wayback/finance_yahoo_com.parquet`
   - `financial_news/2023/01/sec/8k_filings.parquet`

2. **Column-oriented Storage**:
   - Convert all data to Parquet for efficient compression and query
   - Include only essential fields (title, content, date, source, tickers)

3. **Compression Settings**:
   ```python
   df.to_parquet(
       'output.parquet',
       compression='snappy',  # Good balance of compression/speed
       index=False
   )
   ```

## Legal and Ethical Considerations

1. **Respect Terms of Service**:
   - Implement proper rate limiting for all APIs
   - Include identifying User-Agent headers
   - Honor robots.txt directives

2. **Attribution**:
   - Maintain source attribution in all scraped content
   - Document source licenses and usage restrictions

3. **Fair Use Documentation**:
   - Document research/non-commercial purpose
   - Store only necessary content for sentiment analysis

## Implementation Checklist

1. Set up infrastructure for bulk downloading
2. Initialize database for tracking processed content
3. Create custom extractors for each data source
4. Implement robust error handling and retry logic
5. Setup incremental processing to handle large archives
6. Configure deduplication pipeline
7. Connect to FinBERT for sentiment analysis validation
8. Implement monitoring for data quality and coverage