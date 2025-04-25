I'll research the current state of free financial data collection methods for sentiment analysis. Let me gather comprehensive information to help with this project.

First, let's check the current status of key data sources mentioned in your project.

I'll continue researching the SEC EDGAR API, which is another key component of your project.

Now let's research the Reddit data collection part of your project, particularly the current status of the Pushshift API:

Let's continue by researching RSS feeds as a news source:

Now, let's explore financial news APIs with free tiers:

Finally, let's look at academic and public datasets for financial sentiment:

Based on my comprehensive research, I'll provide a detailed report on implementing free data collection methods for financial sentiment analysis.

# Comprehensive Survey and Implementation of Free Data Collection Methods for Financial Sentiment Analysis

## Executive Summary

This report outlines multiple approaches for collecting financial news and textual data suitable for sentiment analysis without cost. The research covers methods for both bulk historical data retrieval and near real-time feeds, with a focus on practical implementation. Key findings include: the viability of Wayback Machine for historical news archives through Python libraries like waybackpy; SEC EDGAR as a reliable source for regulatory filings via libraries such as sec-api (free tier) and edgartools; and alternatives to the unstable Pushshift API for Reddit data collection. Additionally, the report analyzes RSS feeds, free API tiers from providers like Alpha Vantage and Finnhub, and public datasets from Kaggle and academic repositories.

## 1. Scope Definition for Financial News Data

For this project, "financial news" encompasses:

- **Company-specific news**: Earnings reports, leadership changes, product launches, M&A activity
- **Market commentary**: Analysis of market trends, sector performance, trading patterns
- **Economic news**: Macroeconomic indicators, central bank decisions, economic policy changes
- **Regulatory announcements**: SEC filings, compliance changes, legal proceedings
- **Financial social media**: Discussions on platforms like Reddit focusing on investment and markets

## 2. Core Implementation Tasks

### 2.1 Wayback Machine Crawler

The Wayback Machine provides a valuable resource for accessing historical financial news through their CDX Server API. Based on my research, multiple Python libraries exist for interacting with this API.

**Current Status:**
- The Wayback CDX Server API allows programmatic access to the Internet Archive's historical web captures through a standalone HTTP servlet that serves the index the Wayback Machine uses for lookups.
- Python clients can interact with both the CDX API and Memento API, with libraries implementing methods for these standards.

**Recommended Implementation:**
- **Library Choice**: The `waybackpy` library appears most suitable as it interfaces with the Internet Archive's Wayback Machine APIs, allowing for archiving pages and retrieving archived pages.
- **Alternative**: For more advanced requirements, the `wayback` package offers a Python client that can speak both CDX API and Memento API standards.

**Implementation Code Approach:**
```python
import waybackpy
from datetime import datetime, timedelta
import logging
import os
import time

class WaybackFinancialNewsCrawler:
    def __init__(self, target_domains, start_date, end_date, user_agent, output_dir):
        """
        Initialize the Wayback Machine crawler for financial news
        
        Parameters:
        - target_domains: List of financial news domains to search (e.g., ['finance.yahoo.com', 'cnbc.com'])
        - start_date: Start date for historical search (datetime object)
        - end_date: End date for historical search (datetime object)
        - user_agent: User agent string for API requests
        - output_dir: Directory to save retrieved content
        """
        self.target_domains = target_domains
        self.start_date = start_date
        self.end_date = end_date
        self.user_agent = user_agent
        self.output_dir = output_dir
        self.logger = self._setup_logger()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger("wayback_crawler")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler("wayback_crawler.log")
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def crawl_domain(self, domain, max_captures=1000):
        """
        Crawl a specific domain for financial news articles
        
        Parameters:
        - domain: Domain to crawl
        - max_captures: Maximum number of captures to retrieve
        
        Returns:
        - List of successful captures
        """
        self.logger.info(f"Starting crawl for domain: {domain}")
        
        # Initialize the CDX API client
        cdx_api = waybackpy.WaybackMachineCDXServerAPI(
            url=f"https://{domain}",
            user_agent=self.user_agent,
            start_timestamp=self._datetime_to_timestamp(self.start_date),
            end_timestamp=self._datetime_to_timestamp(self.end_date)
        )
        
        successful_captures = []
        
        try:
            # Get captures (with pagination if needed)
            captures = []
            for i, capture in enumerate(cdx_api.snapshots()):
                if i >= max_captures:
                    break
                captures.append(capture)
                
                # Apply rate limiting to avoid overwhelming the API
                if i > 0 and i % 10 == 0:
                    self.logger.info(f"Retrieved {i} captures for {domain}, pausing briefly...")
                    time.sleep(2)  # Brief pause every 10 requests
            
            self.logger.info(f"Found {len(captures)} captures for {domain}")
            
            # Process and save each capture
            for i, capture in enumerate(captures):
                try:
                    # Get the archive URL
                    archive_url = capture.archive_url
                    
                    # Create a Wayback Machine availability API object
                    availability_api = waybackpy.WaybackMachineAvailabilityAPI(
                        url=archive_url,
                        user_agent=self.user_agent
                    )
                    
                    # Save the content
                    file_path = self._save_capture(domain, capture.timestamp, availability_api)
                    if file_path:
                        successful_captures.append({
                            'domain': domain,
                            'timestamp': capture.timestamp,
                            'url': archive_url,
                            'file_path': file_path
                        })
                    
                    # Apply rate limiting for content retrieval
                    if i > 0 and i % 5 == 0:
                        time.sleep(3)  # More substantial pause for content retrieval
                
                except Exception as e:
                    self.logger.error(f"Error processing capture {capture.timestamp} for {domain}: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error crawling domain {domain}: {str(e)}")
        
        return successful_captures
    
    def _save_capture(self, domain, timestamp, availability_api):
        """
        Save the HTML content of a capture
        
        Parameters:
        - domain: Domain being crawled
        - timestamp: Capture timestamp
        - availability_api: WaybackMachineAvailabilityAPI instance
        
        Returns:
        - Path to saved file or None if failed
        """
        try:
            # Get the raw HTML content
            response = availability_api.get()
            
            # Create domain subdirectory if it doesn't exist
            domain_dir = os.path.join(self.output_dir, domain.replace('.', '_'))
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)
            
            # Save to file
            file_path = os.path.join(domain_dir, f"{timestamp}.html")
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"Saved capture {timestamp} for {domain} to {file_path}")
            return file_path
        
        except Exception as e:
            self.logger.error(f"Failed to save capture {timestamp} for {domain}: {str(e)}")
            return None
    
    def crawl_all_domains(self):
        """
        Crawl all target domains
        
        Returns:
        - Dictionary mapping domains to lists of successful captures
        """
        results = {}
        
        for domain in self.target_domains:
            successful_captures = self.crawl_domain(domain)
            results[domain] = successful_captures
            
            # Pause between domains to avoid overloading the API
            self.logger.info(f"Completed crawl for {domain}, pausing before next domain...")
            time.sleep(10)
        
        return results
    
    def _datetime_to_timestamp(self, dt):
        """Convert datetime object to Wayback Machine timestamp format"""
        return dt.strftime("%Y%m%d%H%M%S")

# Example usage:
if __name__ == "__main__":
    # Example configuration
    target_domains = [
        'finance.yahoo.com',
        'cnbc.com',
        'marketwatch.com',
        'wsj.com/news/markets',
        'bloomberg.com/markets'
    ]
    
    # Search for content from 3 months ago to 2 months ago
    end_date = datetime.now() - timedelta(days=60)
    start_date = end_date - timedelta(days=30)
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    output_dir = "wayback_financial_news"
    
    crawler = WaybackFinancialNewsCrawler(
        target_domains=target_domains,
        start_date=start_date,
        end_date=end_date,
        user_agent=user_agent,
        output_dir=output_dir
    )
    
    results = crawler.crawl_all_domains()
    
    # Print summary
    for domain, captures in results.items():
        print(f"Domain: {domain}, Captures retrieved: {len(captures)}")
```

**Limitations and Considerations:**
- The API has rate limits that must be respected
- Not all pages or content may be archived
- Historical completeness varies by site and time period
- Content extraction from HTML requires additional processing

### 2.2 SEC EDGAR Filings Extractor

The SEC EDGAR database provides a wealth of structured financial information in the form of regulatory filings.

**Current Status:**
- The SEC provides APIs for accessing EDGAR data, with comprehensive documentation for developing applications.
- Multiple Python libraries exist to facilitate this access, with varying features and limitations.

**Recommended Implementation:**
- For free access, a combination of the official SEC API and Python libraries can be used.
- The "edgartools" library is described as "the world's easiest, most powerful edgar library" and offers a comprehensive feature set.
- The "sec-api" package allows searching "the entire SEC EDGAR filings corpus, providing access to petabytes of regulatory data", though it has usage limits in its free tier.

**Implementation Code Approach:**
```python
import os
import csv
import time
import logging
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import pandas as pd

class SECEdgarExtractor:
    """
    Class for extracting and processing SEC EDGAR filings
    """
    
    # SEC API endpoint URLs
    BASE_URL = "https://www.sec.gov/Archives/"
    EDGAR_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/"
    
    # Define filing types of interest
    FORM_TYPES = {
        '8-K': 'Current report for material events',
        '10-K': 'Annual report',
        '10-Q': 'Quarterly report',
        'DEF 14A': 'Proxy statement'
    }
    
    def __init__(self, output_dir, email, user_agent=None):
        """
        Initialize the SEC EDGAR extractor
        
        Parameters:
        - output_dir: Directory to save extracted filings
        - email: Email address for SEC API requests (required by SEC)
        - user_agent: User agent string for API requests
        """
        self.output_dir = output_dir
        self.email = email
        self.user_agent = user_agent or f"SECEdgarExtractor/1.0 ({email})"
        self.logger = self._setup_logger()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger("sec_edgar_extractor")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler("sec_edgar_extractor.log")
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def _make_request(self, url):
        """
        Make an HTTP request to the SEC website with proper headers
        
        Parameters:
        - url: URL to request
        
        Returns:
        - Response content if successful, None otherwise
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
            "From": self.email
        }
        
        try:
            response = requests.get(url, headers=headers)
            # SEC recommends waiting to avoid rate limiting
            time.sleep(0.1)
            
            if response.status_code == 200:
                return response.content
            else:
                self.logger.error(f"Failed to retrieve {url}, Status code: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error requesting {url}: {str(e)}")
            return None
    
    def get_company_cik(self, company_name_or_ticker):
        """
        Get the CIK (Central Index Key) for a company
        
        Parameters:
        - company_name_or_ticker: Company name or ticker symbol
        
        Returns:
        - CIK if found, None otherwise
        """
        # This is a simplified implementation - in practice, you might want to use a more robust CIK lookup
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={company_name_or_ticker}&owner=exclude&action=getcompany"
        content = self._make_request(url)
        
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            cik_match = re.search(r'CIK=(\d+)', str(soup))
            if cik_match:
                return cik_match.group(1).zfill(10)  # CIKs should be 10 digits with leading zeros
        
        self.logger.error(f"Could not find CIK for {company_name_or_ticker}")
        return None
    
    def get_quarterly_index_files(self, year, quarter):
        """
        Get the index files for a specific quarter
        
        Parameters:
        - year: Year to retrieve (e.g., 2023)
        - quarter: Quarter to retrieve (1-4)
        
        Returns:
        - Path to downloaded index file or None if failed
        """
        if not 1 <= quarter <= 4:
            self.logger.error(f"Invalid quarter: {quarter}. Must be 1-4.")
            return None
        
        # Create directory for index files
        index_dir = os.path.join(self.output_dir, "indices")
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
        
        # Download the company.idx file for the specified quarter
        url = f"{self.EDGAR_INDEX_URL}/{year}/QTR{quarter}/company.idx"
        content = self._make_request(url)
        
        if content:
            # Save the index file
            file_path = os.path.join(index_dir, f"{year}_QTR{quarter}_company.idx")
            with open(file_path, 'wb') as f:
                f.write(content)
            
            self.logger.info(f"Downloaded index file for {year} Q{quarter} to {file_path}")
            return file_path
        
        return None
    
    def parse_index_file(self, index_file_path, form_types=None):
        """
        Parse an index file to extract filing information
        
        Parameters:
        - index_file_path: Path to the index file
        - form_types: List of form types to extract, or None for all
        
        Returns:
        - List of dictionaries containing filing information
        """
        if form_types is None:
            form_types = list(self.FORM_TYPES.keys())
        
        filings = []
        
        try:
            with open(index_file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            
            # Skip the header - find the line with dashes
            header_end = content.find('\n---')
            if header_end > 0:
                data_start = content.find('\n', header_end + 1)
                if data_start > 0:
                    data_text = content[data_start+1:]
                    
                    # Process each line
                    for line in data_text.split('\n'):
                        if line.strip():
                            # Parse the fixed-width fields
                            # Format is typically: CIK|Company Name|Form Type|Filing Date|File Name
                            try:
                                company_name = line[0:62].strip()
                                form_type = line[62:74].strip()
                                date_filed = line[74:86].strip()
                                file_name = line[86:].strip()
                                
                                # Extract CIK from the file name
                                cik_match = re.search(r'/(\d+)/', file_name)
                                cik = cik_match.group(1) if cik_match else None
                                
                                if form_type in form_types:
                                    filings.append({
                                        'cik': cik,
                                        'company_name': company_name,
                                        'form_type': form_type,
                                        'date_filed': date_filed,
                                        'file_name': file_name,
                                        'url': f"{self.BASE_URL}{file_name}"
                                    })
                            except Exception as e:
                                self.logger.warning(f"Error parsing line in index file: {str(e)}")
                                continue
        
        except Exception as e:
            self.logger.error(f"Error parsing index file {index_file_path}: {str(e)}")
        
        self.logger.info(f"Parsed {len(filings)} filings of types {form_types} from {index_file_path}")
        return filings
    
    def download_filing(self, filing_info):
        """
        Download a specific filing
        
        Parameters:
        - filing_info: Dictionary containing filing information
        
        Returns:
        - Path to downloaded filing or None if failed
        """
        # Create directory for the filing type
        form_dir = os.path.join(self.output_dir, filing_info['form_type'])
        if not os.path.exists(form_dir):
            os.makedirs(form_dir)
        
        # Create a subdirectory for the CIK
        cik_dir = os.path.join(form_dir, filing_info['cik'])
        if not os.path.exists(cik_dir):
            os.makedirs(cik_dir)
        
        # Extract filing date from the filing_info
        filing_date = filing_info.get('date_filed', 'unknown_date')
        
        # Create a filename with CIK, form type and date
        filename = f"{filing_info['cik']}_{filing_info['form_type'].replace('/', '_')}_{filing_date}.html"
        file_path = os.path.join(cik_dir, filename)
        
        # Download the filing
        content = self._make_request(filing_info['url'])
        
        if content:
            with open(file_path, 'wb') as f:
                f.write(content)
            
            self.logger.info(f"Downloaded filing {filing_info['form_type']} for {filing_info['company_name']} to {file_path}")
            return file_path
        
        return None
    
    def extract_text_from_filing(self, filing_path):
        """
        Extract text content from an HTML filing
        
        Parameters:
        - filing_path: Path to the filing HTML file
        
        Returns:
        - Dictionary with extracted text sections
        """
        try:
            with open(filing_path, 'rb') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'head']):
                tag.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Attempt to identify sections
            sections = {
                'full_text': text
            }
            
            # Find the Management's Discussion and Analysis section in 10-K/10-Q
            mda_patterns = [
                r'(?i)Item\s*[7]\s*[:.]\s*Management.{0,50}Discussion and Analysis',
                r'(?i)Management.{0,10}s Discussion and Analysis'
            ]
            
            for pattern in mda_patterns:
                mda_match = re.search(pattern, text)
                if mda_match:
                    mda_start = mda_match.start()
                    # Try to find the end of the MD&A section (next Item or another major section)
                    next_item_match = re.search(r'(?i)Item\s*[8]', text[mda_start:])
                    if next_item_match:
                        mda_end = mda_start + next_item_match.start()
                        sections['mda_section'] = text[mda_start:mda_end].strip()
                    break
            
            # For 8-K, try to extract the event information (Item 1.01, etc.)
            if os.path.basename(filing_path).find('8-K') >= 0:
                event_items = {}
                item_matches = re.finditer(r'(?i)Item\s+(\d+\.\d+)[:\.]?\s+([^\n]+)', text)
                
                for match in item_matches:
                    item_num = match.group(1)
                    item_title = match.group(2).strip()
                    
                    # Find the content of this item (until the next item or end of file)
                    item_start = match.end()
                    next_match = re.search(r'(?i)Item\s+\d+\.\d+', text[item_start:])
                    
                    if next_match:
                        item_content = text[item_start:item_start + next_match.start()].strip()
                    else:
                        # If no next match, take everything until a signature section or the end
                        sig_match = re.search(r'(?i)SIGNATURE|PURSUANT TO|In accordance with', text[item_start:])
                        if sig_match:
                            item_content = text[item_start:item_start + sig_match.start()].strip()
                        else:
                            item_content = text[item_start:].strip()
                    
                    event_items[f"item_{item_num}"] = {
                        'title': item_title,
                        'content': item_content
                    }
                
                if event_items:
                    sections['event_items'] = event_items
            
            return sections
        
        except Exception as e:
            self.logger.error(f"Error extracting text from {filing_path}: {str(e)}")
            return {'full_text': '', 'error': str(e)}
    
    def batch_download_filings(self, filings_info, max_filings=None):
        """
        Download multiple filings
        
        Parameters:
        - filings_info: List of filing information dictionaries
        - max_filings: Maximum number of filings to download, or None for all
        
        Returns:
        - Dictionary mapping filing info to file paths and extracted text
        """
        results = {}
        
        for i, filing_info in enumerate(filings_info):
            if max_filings is not None and i >= max_filings:
                break
            
            try:
                # Download the filing
                file_path = self.download_filing(filing_info)
                
                if file_path:
                    # Extract text
                    extracted_text = self.extract_text_from_filing(file_path)
                    
                    results[f"{filing_info['cik']}_{filing_info['form_type']}_{filing_info['date_filed']}"] = {
                        'filing_info': filing_info,
                        'file_path': file_path,
                        'extracted_text': extracted_text
                    }
                
                # Add a delay to respect SEC's rate limits
                time.sleep(0.5)
            
            except Exception as e:
                self.logger.error(f"Error processing filing {filing_info}: {str(e)}")
        
        return results
    
    def get_company_filings_by_date_range(self, cik, start_date, end_date, form_types=None):
        """
        Get filings for a specific company within a date range
        
        Parameters:
        - cik: Company CIK
        - start_date: Start date (datetime object)
        - end_date: End date (datetime object)
        - form_types: List of form types to retrieve, or None for defaults
        
        Returns:
        - List of filing information dictionaries
        """
        if form_types is None:
            form_types = list(self.FORM_TYPES.keys())
        
        # Ensure CIK is properly formatted
        if not cik.startswith('CIK'):
            cik = 'CIK' + cik.zfill(10)
        
        # Format dates for SEC API
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={','.join(form_types)}&dateb={end_str}&datea={start_str}&owner=exclude&count=100"
        content = self._make_request(url)
        
        if not content:
            return []
        
        filings = []
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find filing entries
        filing_entries = soup.find_all('tr', attrs={'id': lambda x: x and x.startswith('documentsbutton')})
        
        for entry in filing_entries:
            try:
                # Get cells
                cells = entry.find_all('td')
                if len(cells) >= 4:
                    form_type = cells[0].text.strip()
                    filing_desc = cells[1].text.strip()
                    filing_date = cells[2].text.strip()
                    
                    # Get the filing link
                    filing_link = None
                    documents_button = entry.find('a', id=lambda x: x and x.startswith('documentsbutton'))
                    if documents_button:
                        documents_url = "https://www.sec.gov" + documents_button['href']
                        documents_content = self._make_request(documents_url)
                        
                        if documents_content:
                            documents_soup = BeautifulSoup(documents_content, 'html.parser')
                            document_anchor = documents_soup.find('a', attrs={'href': lambda x: x and x.endswith('.htm')})
                            
                            if document_anchor:
                                filing_link = "https://www.sec.gov" + document_anchor['href']
                    
                    filings.append({
                        'cik': cik,
                        'form_type': form_type,
                        'description': filing_desc,
                        'date_filed': filing_date,
                        'url': filing_link
                    })
            
            except Exception as e:
                self.logger.warning(f"Error parsing filing entry: {str(e)}")
        
        self.logger.info(f"Found {len(filings)} filings for CIK {cik} from {start_date} to {end_date}")
        return filings
    
    def extract_8k_items(self, filings):
        """
        Extract specific items from 8-K filings
        
        Parameters:
        - filings: Dictionary mapping filing keys to filing data (from batch_download_filings)
        
        Returns:
        - Pandas DataFrame with extracted items
        """
        results = []
        
        for key, filing_data in filings.items():
            if filing_data['filing_info']['form_type'] == '8-K':
                extracted_text = filing_data.get('extracted_text', {})
                event_items = extracted_text.get('event_items', {})
                
                for item_key, item_data in event_items.items():
                    results.append({
                        'cik': filing_data['filing_info']['cik'],
                        'company_name': filing_data['filing_info'].get('company_name', ''),
                        'date_filed': filing_data['filing_info']['date_filed'],
                        'item_number': item_key.replace('item_', ''),
                        'item_title': item_data['title'],
                        'item_content': item_data['content'][:1000]  # Truncate for readability
                    })
        
        return pd.DataFrame(results)
    
    def extract_mda_sections(self, filings):
        """
        Extract MD&A sections from 10-K and 10-Q filings
        
        Parameters:
        - filings: Dictionary mapping filing keys to filing data (from batch_download_filings)
        
        Returns:
        - Pandas DataFrame with extracted MD&A sections
        """
        results = []
        
        for key, filing_data in filings.items():
            if filing_data['filing_info']['form_type'] in ['10-K', '10-Q']:
                extracted_text = filing_data.get('extracted_text', {})
                mda_section = extracted_text.get('mda_section', '')
                
                if mda_section:
                    results.append({
                        'cik': filing_data['filing_info']['cik'],
                        'company_name': filing_data['filing_info'].get('company_name', ''),
                        'form_type': filing_data['filing_info']['form_type'],
                        'date_filed': filing_data['filing_info']['date_filed'],
                        'mda_section': mda_section[:1000]  # Truncate for readability
                    })
        
        return pd.DataFrame(results)

# Example usage:
if __name__ == "__main__":
    # Example configuration
    output_dir = "sec_edgar_data"
    email = "your.email@example.com"  # SEC requires this
    
    extractor = SECEdgarExtractor(output_dir, email)
    
    # Get CIK for a company
    cik = extractor.get_company_cik("AAPL")
    
    if cik:
        # Get filings for the last quarter
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        filings_info = extractor.get_company_filings_by_date_range(
            cik, start_date, end_date, ['8-K', '10-Q']
        )
        
        if filings_info:
            # Download the filings
            downloaded_filings = extractor.batch_download_filings(filings_info, max_filings=5)
            
            # Extract 8-K items
            items_df = extractor.extract_8k_items(downloaded_filings)
            if not items_df.empty:
                items_df.to_csv(os.path.join(output_dir, f"{cik}_8k_items.csv"), index=False)
                print(f"Saved 8-K items to {cik}_8k_items.csv")
            
            # Extract MD&A sections
            mda_df = extractor.extract_mda_sections(downloaded_filings)
            if not mda_df.empty:
                mda_df.to_csv(os.path.join(output_dir, f"{cik}_mda_sections.csv"), index=False)
                print(f"Saved MD&A sections to {cik}_mda_sections.csv")
```

**Limitations and Considerations:**
- SEC's API has rate limiting requirements (10 requests per second per IP)
- An email address must be provided in the request headers
- Filings structure can vary significantly, especially for older documents
- Text extraction from HTML/XML filings requires robust parsing

### 2.3 Reddit Financial Data Collector

The Pushshift API was traditionally the go-to option for collecting historical Reddit data. However, based on recent research, its status has changed significantly.

**Current Status:**
- Reddit is now partnering with Pushshift to grant access to moderation tools, but access is limited to verified Reddit moderators.
- This represents a major shift from the previously open Pushshift API access model.

**Recommended Implementation:**
- The official Reddit API (PRAW) is now the primary method, though it has limitations for historical data.
- For research purposes, PSAW (PushShift API Wrapper) can be used to access data, but it's dependent on the restricted Pushshift API.

**Implementation Code Approach:**
```python
import praw
import pandas as pd
import datetime
import time
import logging
import os
import csv
import re
from prawcore.exceptions import PrawcoreException

class RedditFinancialDataCollector:
    """
    Class for collecting financial data from Reddit using the official Reddit API (PRAW)
    """
    
    # Financial subreddits of interest
    FINANCIAL_SUBREDDITS = [
        'investing',
        'stocks',
        'wallstreetbets',
        'finance',
        'SecurityAnalysis',
        'StockMarket',
        'options',
        'dividends',
        'personalfinance'
    ]
    
    def __init__(self, client_id, client_secret, user_agent, output_dir):
        """
        Initialize the Reddit Financial Data Collector
        
        Parameters:
        - client_id: Reddit API client ID
        - client_secret: Reddit API client secret
        - user_agent: User agent string for API requests
        - output_dir: Directory to save collected data
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.output_dir = output_dir
        self.reddit = self._initialize_reddit_client()
        self.logger = self._setup_logger()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _initialize_reddit_client(self):
        """Initialize the Reddit API client"""
        return praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent
        )
    
    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger("reddit_data_collector")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler("reddit_data_collector.log")
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def collect_posts(self, subreddit_name, limit=100, time_filter='month', search_query=None):
        """
        Collect posts from a specific subreddit
        
        Parameters:
        - subreddit_name: Name of the subreddit
        - limit: Maximum number of posts to collect
        - time_filter: Time filter ('day', 'week', 'month', 'year', 'all')
        - search_query: Optional search query to filter posts
        
        Returns:
        - List of post dictionaries
        """
        self.logger.info(f"Collecting posts from r/{subreddit_name} with time_filter={time_filter}, limit={limit}")
        
        subreddit = self.reddit.subreddit(subreddit_name)
        posts = []
        
        try:
            # If search query is provided, search for posts
            if search_query:
                submissions = subreddit.search(search_query, time_filter=time_filter, limit=limit)
            else:
                # Otherwise, get top posts for the specified time period
                submissions = subreddit.top(time_filter=time_filter, limit=limit)
            
            for submission in submissions:
                try:
                    # Extract post data
                    post_data = {
                        'id': submission.id,
                        'title': submission.title,
                        'score': submission.score,
                        'upvote_ratio': submission.upvote_ratio,
                        'created_utc': datetime.datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                        'num_comments': submission.num_comments,
                        'permalink': submission.permalink,
                        'url': submission.url,
                        'is_self': submission.is_self
                    }
                    
                    # Add selftext if it's a text post
                    if submission.is_self:
                        post_data['selftext'] = submission.selftext
                    
                    # Add author if available
                    try:
                        post_data['author'] = submission.author.name if submission.author else '[deleted]'
                    except:
                        post_data['author'] = '[error]'
                    
                    # Get post flair
                    post_data['link_flair_text'] = submission.link_flair_text
                    
                    posts.append(post_data)
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.1)
                
                except Exception as e:
                    self.logger.warning(f"Error processing submission {submission.id}: {str(e)}")
            
            self.logger.info(f"Collected {len(posts)} posts from r/{subreddit_name}")
        
        except PrawcoreException as e:
            self.logger.error(f"PRAW Core error with r/{subreddit_name}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error collecting posts from r/{subreddit_name}: {str(e)}")
        
        return posts
    
    def collect_comments(self, post_id, limit=None):
        """
        Collect comments for a specific Reddit post
        
        Parameters:
        - post_id: ID of the post
        - limit: Maximum number of comments to collect, or None for all
        
        Returns:
        - List of comment dictionaries
        """
        self.logger.info(f"Collecting comments for post {post_id}")
        
        submission = self.reddit.submission(id=post_id)
        comments = []
        
        try:
            # Replace MoreComments objects with actual comments (up to a limit)
            if limit:
                submission.comments.replace_more(limit=limit)
            else:
                submission.comments.replace_more(limit=None)
            
            # Flatten the comment forest
            for comment in submission.comments.list():
                try:
                    # Extract comment data
                    comment_data = {
                        'id': comment.id,
                        'post_id': post_id,
                        'body': comment.body,
                        'score': comment.score,
                        'created_utc': datetime.datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                        'permalink': comment.permalink,
                        'parent_id': comment.parent_id,
                        'depth': comment.depth
                    }
                    
                    # Add author if available
                    try:
                        comment_data['author'] = comment.author.name if comment.author else '[deleted]'
                    except:
                        comment_data['author'] = '[error]'
                    
                    comments.append(comment_data)
                
                except Exception as e:
                    self.logger.warning(f"Error processing comment {comment.id}: {str(e)}")
            
            self.logger.info(f"Collected {len(comments)} comments for post {post_id}")
        
        except PrawcoreException as e:
            self.logger.error(f"PRAW Core error with post {post_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error collecting comments for post {post_id}: {str(e)}")
        
        return comments
    
    def search_by_ticker(self, ticker, subreddits=None, time_filter='month', limit=100):
        """
        Search for posts mentioning a specific stock ticker
        
        Parameters:
        - ticker: Stock ticker symbol
        - subreddits: List of subreddits to search, or None for all financial subreddits
        - time_filter: Time filter for the search
        - limit: Maximum number of posts per subreddit
        
        Returns:
        - Dictionary mapping subreddit names to lists of posts
        """
        if subreddits is None:
            subreddits = self.FINANCIAL_SUBREDDITS
        
        # Normalize ticker format
        ticker = ticker.upper().strip()
        search_query = f'${ticker} OR {ticker}'
        
        results = {}
        
        for subreddit_name in subreddits:
            try:
                posts = self.collect_posts(
                    subreddit_name,
                    limit=limit,
                    time_filter=time_filter,
                    search_query=search_query
                )
                
                results[subreddit_name] = posts
                
                # Add a delay between subreddit searches
                time.sleep(2)
            
            except Exception as e:
                self.logger.error(f"Error searching for {ticker} in r/{subreddit_name}: {str(e)}")
        
        # Count total posts found
        total_posts = sum(len(posts) for posts in results.values())
        self.logger.info(f"Found a total of {total_posts} posts about {ticker} across {len(results)} subreddits")
        
        return results
    
    def save_posts_to_csv(self, posts, filename):
        """
        Save collected posts to a CSV file
        
        Parameters:
        - posts: List of post dictionaries
        - filename: Output filename
        
        Returns:
        - Path to the saved file
        """
        if not posts:
            self.logger.warning(f"No posts to save to {filename}")
            return None
        
        file_path = os.path.join(self.output_dir, filename)
        
        try:
            # Get all possible keys to use as CSV columns
            all_keys = set()
            for post in posts:
                all_keys.update(post.keys())
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(posts)
            
            self.logger.info(f"Saved {len(posts)} posts to {file_path}")
            return file_path
        
        except Exception as e:
            self.logger.error(f"Error saving posts to {file_path}: {str(e)}")
            return None
    
    def save_comments_to_csv(self, comments, filename):
        """
        Save collected comments to a CSV file
        
        Parameters:
        - comments: List of comment dictionaries
        - filename: Output filename
        
        Returns:
        - Path to the saved file
        """
        if not comments:
            self.logger.warning(f"No comments to save to {filename}")
            return None
        
        file_path = os.path.join(self.output_dir, filename)
        
        try:
            # Get all possible keys to use as CSV columns
            all_keys = set()
            for comment in comments:
                all_keys.update(comment.keys())
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(comments)
            
            self.logger.info(f"Saved {len(comments)} comments to {file_path}")
            return file_path
        
        except Exception as e:
            self.logger.error(f"Error saving comments to {file_path}: {str(e)}")
            return None
    
    def collect_subreddit_data(self, subreddit_name, time_filters=None, limits=None, include_comments=False, comment_limit=10):
        """
        Collect comprehensive data from a subreddit
        
        Parameters:
        - subreddit_name: Name of the subreddit
        - time_filters: List of time filters to use, or None for default ['day', 'week', 'month']
        - limits: Dictionary mapping time filters to post limits, or None for default (100 each)
        - include_comments: Whether to collect comments for each post
        - comment_limit: Maximum number of MoreComments to expand
        
        Returns:
        - Dictionary with collected data
        """
        if time_filters is None:
            time_filters = ['day', 'week', 'month']
        
        if limits is None:
            limits = {tf: 100 for tf in time_filters}
        
        results = {}
        
        for time_filter in time_filters:
            limit = limits.get(time_filter, 100)
            
            try:
                posts = self.collect_posts(
                    subreddit_name,
                    limit=limit,
                    time_filter=time_filter
                )
                
                results[time_filter] = {
                    'posts': posts,
                    'comments': {}
                }
                
                # Save posts to CSV
                self.save_posts_to_csv(
                    posts,
                    f"{subreddit_name}_{time_filter}_posts.csv"
                )
                
                # Collect comments if requested
                if include_comments and posts:
                    for post in posts:
                        post_id = post['id']
                        comments = self.collect_comments(post_id, limit=comment_limit)
                        
                        results[time_filter]['comments'][post_id] = comments
                        
                        # Save comments to CSV
                        self.save_comments_to_csv(
                            comments,
                            f"{subreddit_name}_{time_filter}_post_{post_id}_comments.csv"
                        )
                        
                        # Add a delay to avoid rate limiting
                        time.sleep(1)
            
            except Exception as e:
                self.logger.error(f"Error collecting data for r/{subreddit_name} with time_filter={time_filter}: {str(e)}")
        
        return results
    
    def find_sentiment_keywords(self, text, positive_keywords=None, negative_keywords=None):
        """
        Simple keyword-based sentiment analysis
        
        Parameters:
        - text: Text to analyze
        - positive_keywords: List of positive sentiment keywords, or None for defaults
        - negative_keywords: List of negative sentiment keywords, or None for defaults
        
        Returns:
        - Dictionary with sentiment scores
        """
        if not text:
            return {'positive_score': 0, 'negative_score': 0, 'sentiment': 'neutral'}
        
        if positive_keywords is None:
            positive_keywords = [
                'bullish', 'buy', 'long', 'calls', 'growth', 'up', 'gain', 'profitable',
                'profit', 'good', 'great', 'excellent', 'increase', 'upside', 'higher',
                'positive', 'optimistic', 'outperform', 'beat', 'exceeds', 'strong'
            ]
        
        if negative_keywords is None:
            negative_keywords = [
                'bearish', 'sell', 'short', 'puts', 'recession', 'down', 'loss', 'crash',
                'bubble', 'bad', 'terrible', 'poor', 'decrease', 'downside', 'lower',
                'negative', 'pessimistic', 'underperform', 'miss', 'disappoints', 'weak'
            ]
        
        # Normalize text
        text_lower = text.lower()
        
        # Count occurrences of positive and negative keywords
        positive_count = sum(1 for keyword in positive_keywords if re.search(fr'\b{keyword}\b', text_lower))
        negative_count = sum(1 for keyword in negative_keywords if re.search(fr'\b{keyword}\b', text_lower))
        
        # Determine sentiment
        if positive_count > negative_count:
            sentiment = 'positive'
        elif negative_count > positive_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'positive_score': positive_count,
            'negative_score': negative_count,
            'sentiment': sentiment
        }
    
    def analyze_sentiment(self, posts_csv_path):
        """
        Analyze sentiment in posts from a CSV file
        
        Parameters:
        - posts_csv_path: Path to the CSV file containing posts
        
        Returns:
        - Pandas DataFrame with sentiment analysis
        """
        try:
            # Read posts from CSV
            posts_df = pd.read_csv(posts_csv_path)
            
            # Extract text from posts
            if 'selftext' in posts_df.columns:
                posts_df['text_for_analysis'] = posts_df['title'] + ' ' + posts_df['selftext'].fillna('')
            else:
                posts_df['text_for_analysis'] = posts_df['title']
            
            # Apply sentiment analysis
            sentiment_results = []
            
            for _, row in posts_df.iterrows():
                sentiment = self.find_sentiment_keywords(row['text_for_analysis'])
                sentiment_results.append(sentiment)
            
            # Convert results to DataFrame
            sentiment_df = pd.DataFrame(sentiment_results)
            
            # Combine with original data
            result_df = pd.concat([posts_df, sentiment_df], axis=1)
            
            # Save results to a new CSV
            output_path = posts_csv_path.replace('.csv', '_sentiment.csv')
            result_df.to_csv(output_path, index=False)
            
            self.logger.info(f"Sentiment analysis completed and saved to {output_path}")
            
            return result_df
        
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment in {posts_csv_path}: {str(e)}")
            return None
    
    def collect_financial_data(self, days=30, include_comments=False):
        """
        Collect financial data from all financial subreddits
        
        Parameters:
        - days: Number of days of data to collect
        - include_comments: Whether to collect comments
        
        Returns:
        - Summary of collected data
        """
        summary = {}
        
        # Collection timestamp
        collection_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        for subreddit_name in self.FINANCIAL_SUBREDDITS:
            try:
                self.logger.info(f"Collecting data from r/{subreddit_name}")
                
                # Determine time filters based on days
                time_filters = []
                if days <= 1:
                    time_filters = ['day']
                elif days <= 7:
                    time_filters = ['day', 'week']
                elif days <= 30:
                    time_filters = ['day', 'week', 'month']
                else:
                    time_filters = ['day', 'week', 'month', 'year']
                
                # Collect data
                subreddit_data = self.collect_subreddit_data(
                    subreddit_name,
                    time_filters=time_filters,
                    include_comments=include_comments
                )
                
                # Create a unified dataframe for all posts
                all_posts = []
                for time_filter, data in subreddit_data.items():
                    for post in data['posts']:
                        post['time_filter'] = time_filter
                        post['subreddit'] = subreddit_name
                        all_posts.append(post)
                
                # Save unified posts
                unified_csv_path = os.path.join(
                    self.output_dir,
                    f"{subreddit_name}_all_posts_{collection_time}.csv"
                )
                
                if all_posts:
                    all_posts_df = pd.DataFrame(all_posts)
                    all_posts_df.to_csv(unified_csv_path, index=False)
                    
                    # Analyze sentiment
                    sentiment_df = self.analyze_sentiment(unified_csv_path)
                    
                    # Add to summary
                    summary[subreddit_name] = {
                        'post_count': len(all_posts),
                        'time_filters': time_filters,
                        'sentiment_counts': sentiment_df['sentiment'].value_counts().to_dict() if sentiment_df is not None else {}
                    }
                else:
                    summary[subreddit_name] = {
                        'post_count': 0,
                        'time_filters': time_filters,
                        'sentiment_counts': {}
                    }
                
                # Add a delay between subreddits
                time.sleep(5)
            
            except Exception as e:
                self.logger.error(f"Error collecting data from r/{subreddit_name}: {str(e)}")
                summary[subreddit_name] = {
                    'error': str(e)
                }
        
        # Save summary
        summary_path = os.path.join(self.output_dir, f"financial_data_summary_{collection_time}.csv")
        
        summary_rows = []
        for subreddit, data in summary.items():
            row = {'subreddit': subreddit}
            row.update(data)
            summary_rows.append(row)
        
        pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
        
        return summary

# Example usage:
if __name__ == "__main__":
    # Example configuration
    client_id = 'YOUR_CLIENT_ID'
    client_secret = 'YOUR_CLIENT_SECRET'
    user_agent = 'Financial Data Collector v1.0 by YOUR_USERNAME'
    output_dir = "reddit_financial_data"
    
    collector = RedditFinancialDataCollector(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        output_dir=output_dir
    )
    
    # Option 1: Collect data for specific tickers
    ticker_results = collector.search_by_ticker('AAPL', time_filter='month', limit=50)
    
    for subreddit, posts in ticker_results.items():
        collector.save_posts_to_csv(posts, f"AAPL_{subreddit}_posts.csv")
    
    # Option 2: Collect data from all financial subreddits
    summary = collector.collect_financial_data(days=7, include_comments=False)
    print("Data collection summary:", summary)
```

**Limitations and Considerations:**
- The official Reddit API (PRAW) has rate limits (60 requests per minute)
- Historical data access is limited, especially for older content
- Free API usage requires registration with Reddit's developer program
- Access to all posts in a subreddit is limited; search functionality helps
- Pushshift is no longer a reliable option for bulk historical data

## 3. Exploration & Feasibility Analysis

### 3.1 Financial News RSS Feeds

RSS feeds remain a viable option for near-real-time financial news collection without cost.

**Current Status:**
- Python offers simple methods for RSS parsing, with the feedparser library making extraction easy.
- Feedparser can extract structured information from RSS feeds in the form of Python lists and dictionaries.

**Recommended Implementation:**
- Use the `feedparser` library to parse RSS feeds from financial news sources
- The "FinNews" package specifically gathers financial news from various RSS feeds, supporting multiple financial sources.

**Implementation Code Approach:**
```python
import feedparser
import pandas as pd
import datetime
import time
import logging
import os
import json
import hashlib
from urllib.parse import urlparse
import re

class FinancialNewsRSSCollector:
    """
    Class for collecting financial news from various RSS feeds
    """
    
    # Default list of financial news RSS feeds
    DEFAULT_FEEDS = {
        'yahoo_finance': {
            'name': 'Yahoo Finance',
            'url': 'https://finance.yahoo.com/news/rssindex',
            'category': 'general'
        },
        'reuters_business': {
            'name': 'Reuters Business',
            'url': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
            'category': 'business'
        },
        'cnbc_finance': {
            'name': 'CNBC Finance',
            'url': 'https://www.cnbc.com/id/10000664/device/rss/rss.html',
            'category': 'finance'
        },
        'wsj_markets': {
            'name': 'Wall Street Journal Markets',
            'url': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
            'category': 'markets'
        },
        'seeking_alpha': {
            'name': 'Seeking Alpha',
            'url': 'https://seekingalpha.com/feed.xml',
            'category': 'analysis'
        },
        'marketwatch': {
            'name': 'MarketWatch',
            'url': 'https://www.marketwatch.com/rss/topstories',
            'category': 'markets'
        },
        'bloomberg_markets': {
            'name': 'Bloomberg Markets',
            'url': 'https://feeds.bloomberg.com/markets/news.rss',
            'category': 'markets'
        }
    }
    
    def __init__(self, output_dir, feeds=None, user_agent=None):
        """
        Initialize the Financial News RSS Collector
        
        Parameters:
        - output_dir: Directory to save collected news
        - feeds: Dictionary of feed configurations or None to use defaults
        - user_agent: User agent string for feed requests
        """
        self.output_dir = output_dir
        self.feeds = feeds or self.DEFAULT_FEEDS
        self.user_agent = user_agent or 'Financial News Collector/1.0'
        self.logger = self._setup_logger()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger("financial_news_rss")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler("financial_news_rss.log")
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def add_feed(self, feed_id, name, url, category='general'):
        """
        Add a new feed to the collector
        
        Parameters:
        - feed_id: Unique identifier for the feed
        - name: Display name for the feed
        - url: RSS feed URL
        - category: Category for the feed (e.g., 'finance', 'markets')
        """
        self.feeds[feed_id] = {
            'name': name,
            'url': url,
            'category': category
        }
        self.logger.info(f"Added feed: {name} ({url})")
    
    def remove_feed(self, feed_id):
        """
        Remove a feed from the collector
        
        Parameters:
        - feed_id: Identifier of the feed to remove
        
        Returns:
        - True if the feed was removed, False otherwise
        """
        if feed_id in self.feeds:
            feed_info = self.feeds[feed_id]
            del self.feeds[feed_id]
            self.logger.info(f"Removed feed: {feed_info['name']} ({feed_info['url']})")
            return True
        
        self.logger.warning(f"Feed {feed_id} not found, nothing removed")
        return False
    
    def _parse_feed(self, feed_id, feed_info):
        """
        Parse a single RSS feed
        
        Parameters:
        - feed_id: Identifier of the feed
        - feed_info: Feed configuration dictionary
        
        Returns:
        - List of news item dictionaries
        """
        self.logger.info(f"Parsing feed: {feed_info['name']} ({feed_info['url']})")
        
        try:
            # Parse the RSS feed
            feed = feedparser.parse(feed_info['url'], agent=self.user_agent)
            
            if hasattr(feed, 'bozo_exception'):
                self.logger.warning(f"Feed parsing issue for {feed_info['name']}: {feed.bozo_exception}")
            
            articles = []
            
            for entry in feed.entries:
                try:
                    # Create an article dictionary with common fields
                    article = {
                        'feed_id': feed_id,
                        'feed_name': feed_info['name'],
                        'feed_category': feed_info['category'],
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'collection_date': datetime.datetime.now().isoformat()
                    }
                    
                    # Get publication date if available
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime.datetime(*entry.published_parsed[:6])
                        article['published_date'] = pub_date.isoformat()
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime.datetime(*entry.updated_parsed[:6])
                        article['published_date'] = pub_date.isoformat()
                    else:
                        article['published_date'] = None
                    
                    # Get article summary/description if available
                    if hasattr(entry, 'summary'):
                        article['summary'] = entry.summary
                    elif hasattr(entry, 'description'):
                        article['summary'] = entry.description
                    else:
                        article['summary'] = ''
                    
                    # Extract domain from the link
                    try:
                        article['domain'] = urlparse(entry.link).netloc
                    except:
                        article['domain'] = None
                    
                    # Extract authors if available
                    if hasattr(entry, 'authors'):
                        authors = [author.get('name', '') for author in entry.authors if 'name' in author]
                        article['authors'] = authors if authors else None
                    elif hasattr(entry, 'author'):
                        article['authors'] = [entry.author]
                    else:
                        article['authors'] = None
                    
                    # Generate a unique ID for the article
                    article['id'] = hashlib.md5(f"{article['link']}".encode()).hexdigest()
                    
                    # Add content if available
                    if hasattr(entry, 'content'):
                        article['content'] = entry.content[0].value if entry.content else None
                    else:
                        article['content'] = None
                    
                    # Add tags/categories if available
                    if hasattr(entry, 'tags'):
                        article['tags'] = [tag.get('term', '') for tag in entry.tags if 'term' in tag]
                    else:
                        article['tags'] = None
                    
                    articles.append(article)
                
                except Exception as e:
                    self.logger.warning(f"Error processing entry in {feed_info['name']}: {str(e)}")
            
            self.logger.info(f"Processed {len(articles)} articles from {feed_info['name']}")
            return articles
        
        except Exception as e:
            self.logger.error(f"Error parsing feed {feed_info['name']}: {str(e)}")
            return []
    
    def collect_all_feeds(self):
        """
        Collect articles from all configured feeds
        
        Returns:
        - Dictionary mapping feed IDs to lists of articles
        """
        results = {}
        all_articles = []
        
        for feed_id, feed_info in self.feeds.items():
            try:
                articles = self._parse_feed(feed_id, feed_info)
                results[feed_id] = articles
                all_articles.extend(articles)
                
                # Add a delay between feeds to avoid hammering servers
                time.sleep(2)
            
            except Exception as e:
                self.logger.error(f"Error collecting feed {feed_id}: {str(e)}")
                results[feed_id] = []
        
        # Save all collected articles
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(self.output_dir, f"financial_news_{timestamp}.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(all_articles)} articles to {output_path}")
        
        # Also save as CSV for easier analysis
        csv_path = os.path.join(self.output_dir, f"financial_news_{timestamp}.csv")
        pd.DataFrame(all_articles).to_csv(csv_path, index=False)
        
        self.logger.info(f"Saved articles to CSV: {csv_path}")
        
        return results
    
    def collect_by_category(self, category):
        """
        Collect articles from feeds in a specific category
        
        Parameters:
        - category: Category to filter feeds by
        
        Returns:
        - List of collected articles
        """
        articles = []
        
        # Filter feeds by category
        category_feeds = {
            feed_id: feed_info for feed_id, feed_info in self.feeds.items()
            if feed_info['category'].lower() == category.lower()
        }
        
        if not category_feeds:
            self.logger.warning(f"No feeds found for category: {category}")
            return []
        
        # Collect from each feed in the category
        for feed_id, feed_info in category_feeds.items():
            try:
                feed_articles = self._parse_feed(feed_id, feed_info)
                articles.extend(feed_articles)
                
                # Add a delay between feeds
                time.sleep(2)
            
            except Exception as e:
                self.logger.error(f"Error collecting feed {feed_id}: {str(e)}")
        
        # Save collected articles
        if articles:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f"financial_news_{category}_{timestamp}.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Saved {len(articles)} articles from category {category} to {output_path}")
            
            # Also save as CSV
            csv_path = os.path.join(self.output_dir, f"financial_news_{category}_{timestamp}.csv")
            pd.DataFrame(articles).to_csv(csv_path, index=False)
        
        return articles
    
    def filter_articles_by_keywords(self, articles, keywords, field='title'):
        """
        Filter articles by keywords
        
        Parameters:
        - articles: List of article dictionaries
        - keywords: List of keywords to search for
        - field: Field to search in ('title', 'summary', or 'content')
        
        Returns:
        - List of filtered articles
        """
        if not keywords:
            return articles
        
        filtered = []
        
        # Compile regex patterns for each keyword
        patterns = [re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE) for keyword in keywords]
        
        for article in articles:
            text = article.get(field, '')
            if text:
                # Check if any pattern matches
                if any(pattern.search(text) for pattern in patterns):
                    filtered.append(article)
        
        return filtered
    
    def search_articles(self, keywords, categories=None, start_date=None, end_date=None):
        """
        Search for articles matching criteria
        
        Parameters:
        - keywords: List of keywords to search for
        - categories: List of categories to include, or None for all
        - start_date: Start date for filtering (ISO format string or datetime)
        - end_date: End date for filtering (ISO format string or datetime)
        
        Returns:
        - List of matching articles
        """
        # Collect from all feeds or specific categories
        if categories:
            all_articles = []
            for category in categories:
                category_articles = self.collect_by_category(category)
                all_articles.extend(category_articles)
        else:
            all_articles = []
            results = self.collect_all_feeds()
            for articles in results.values():
                all_articles.extend(articles)
        
        # Convert date strings to datetime objects if needed
        if start_date and isinstance(start_date, str):
            start_date = datetime.datetime.fromisoformat(start_date)
        
        if end_date and isinstance(end_date, str):
            end_date = datetime.datetime.fromisoformat(end_date)
        
        # Filter by date if specified
        if start_date or end_date:
            filtered_by_date = []
            
            for article in all_articles:
                pub_date_str = article.get('published_date')
                
                if pub_date_str:
                    try:
                        pub_date = datetime.datetime.fromisoformat(pub_date_str)
                        
                        # Check date range
                        if (not start_date or pub_date >= start_date) and (not end_date or pub_date <= end_date):
                            filtered_by_date.append(article)
                    except:
                        # If date parsing fails, skip date filtering for this article
                        pass
                else:
                    # If no date available, include by default
                    filtered_by_date.append(article)
            
            articles_to_search = filtered_by_date
        else:
            articles_to_search = all_articles
        
        # Filter by keywords
        if keywords:
            # Search in title
            title_matches = self.filter_articles_by_keywords(articles_to_search, keywords, 'title')
            
            # Search in summary
            summary_matches = self.filter_articles_by_keywords(articles_to_search, keywords, 'summary')
            
            # Combine results (using dictionary to remove duplicates)
            combined = {article['id']: article for article in title_matches + summary_matches}
            result = list(combined.values())
        else:
            result = articles_to_search
        
        # Save search results
        if result:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            keywords_str = '_'.join(keywords) if keywords else 'all'
            output_path = os.path.join(self.output_dir, f"search_results_{keywords_str}_{timestamp}.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Saved {len(result)} search results to {output_path}")
            
            # Also save as CSV
            csv_path = os.path.join(self.output_dir, f"search_results_{keywords_str}_{timestamp}.csv")
            pd.DataFrame(result).to_csv(csv_path, index=False)
        
        return result
    
    def set_up_continuous_collection(self, interval_minutes=30, run_time_hours=None):
        """
        Set up continuous collection of news at regular intervals
        
        Parameters:
        - interval_minutes: Interval between collections in minutes
        - run_time_hours: Total run time in hours, or None to run indefinitely
        
        Note: This function blocks execution until complete
        """
        self.logger.info(f"Starting continuous collection at {interval_minutes} minute intervals")
        
        start_time = datetime.datetime.now()
        collection_count = 0
        
        try:
            while True:
                # Collect from all feeds
                self.logger.info(f"Collection #{collection_count + 1} started")
                self.collect_all_feeds()
                collection_count += 1
                self.logger.info(f"Collection #{collection_count} completed")
                
                # Check if run time limit reached
                if run_time_hours:
                    elapsed = (datetime.datetime.now() - start_time).total_seconds() / 3600
                    if elapsed >= run_time_hours:
                        self.logger.info(f"Run time limit of {run_time_hours} hours reached. Stopping.")
                        break
                
                # Wait for the next interval
                self.logger.info(f"Waiting {interval_minutes} minutes until next collection")
                time.sleep(interval_minutes * 60)
        
        except KeyboardInterrupt:
            self.logger.info("Continuous collection stopped by user")
        except Exception as e:
            self.logger.error(f"Error in continuous collection: {str(e)}")
        
        self.logger.info(f"Continuous collection ended after {collection_count} collections")

# Example usage:
if __name__ == "__main__":
    # Example configuration
    output_dir = "financial_news_rss"
    
    collector = FinancialNewsRSSCollector(output_dir)
    
    # Add custom feeds if needed
    collector.add_feed(
        feed_id='ft_markets',
        name='Financial Times Markets',
        url='https://www.ft.com/markets?format=rss',
        category='markets'
    )
    
    # Option 1: Collect from all feeds once
    results = collector.collect_all_feeds()
    
    # Option 2: Search for specific keywords
    search_results = collector.search_articles(
        keywords=['inflation', 'interest rates', 'federal reserve'],
        categories=['markets', 'finance'],
        start_date=datetime.datetime.now() - datetime.timedelta(days=7)
    )
    
    # Option 3: Set up continuous collection (commented out)
    # collector.set_up_continuous_collection(interval_minutes=60, run_time_hours=24)
```

**Limitations and Considerations:**
- RSS feeds typically only include recent articles, not historical content
- Article content may be partial, requiring additional retrieval for full text
- Feeds may update at different frequencies; some may only update a few times daily
- Many financial news sites have moved away from full content in RSS feeds

### 3.2 Free API Tiers

Several financial data services offer free API tiers that can be leveraged for financial sentiment analysis.

**Current Status:**
- Alpha Vantage stands out with its free tier that provides "500 API calls per day with access to almost every API endpoint" across various data types.
- Alpha Vantage actually limits free users to "25 requests per day" according to their official support page.
- Finnhub offers free endpoints for financial data, though the free tier is limited in scope.

**Recommended Implementation:**
- Alpha Vantage for basic financial news API access
- Finnhub as an alternative source for certain financial data points
- Multiple API key rotation for overcoming daily limits

**Implementation Code Approach:**
```python
import os
import requests
import json
import pandas as pd
import time
import logging
import datetime
import random
from typing import List, Dict, Any, Optional

class FinancialNewsAPI:
    """
    Class to interact with financial news APIs with free tiers
    Supports Alpha Vantage and NewsAPI
    """
    
    def __init__(self, output_dir: str, api_keys: Dict[str, List[str]] = None):
        """
        Initialize the Financial News API handler
        
        Parameters:
        - output_dir: Directory to save collected data
        - api_keys: Dictionary mapping API services to lists of API keys
                    e.g., {'alpha_vantage': ['key1', 'key2'], 'newsapi': ['key1']}
        """
        self.output_dir = output_dir
        self.api_keys = api_keys or {}
        self.logger = self._setup_logger()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Initialize API key usage counters
        self.key_usage = {
            service: {key: 0 for key in keys}
            for service, keys in self.api_keys.items()
        }
    
    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger("financial_news_api")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler("financial_news_api.log")
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def add_api_key(self, service: str, key: str):
        """
        Add an API key for a service
        
        Parameters:
        - service: Service name (e.g., 'alpha_vantage', 'newsapi')
        - key: API key to add
        """
        if service not in self.api_keys:
            self.api_keys[service] = []
            self.key_usage[service] = {}
        
        if key not in self.api_keys[service]:
            self.api_keys[service].append(key)
            self.key_usage[service][key] = 0
            self.logger.info(f"Added API key for {service}")
    
    def _get_next_key(self, service: str) -> Optional[str]:
        """
        Get the next available API key for a service using round-robin
        
        Parameters:
        - service: Service name
        
        Returns:
        - API key to use or None if no keys available
        """
        if service not in self.api_keys or not self.api_keys[service]:
            self.logger.warning(f"No API keys available for {service}")
            return None
        
        # Sort keys by usage count
        keys = sorted(self.api_keys[service], key=lambda k: self.key_usage[service][k])
        
        # Return the least used key
        key = keys[0]
        self.key_usage[service][key] += 1
        return key
    
    def get_alpha_vantage_news(self, tickers: List[str] = None, topics: List[str] = None, time_from: str = None, time_to: str = None) -> List[Dict[str, Any]]:
        """
        Get financial news from Alpha Vantage NEWS_SENTIMENT endpoint
        
        Parameters:
        - tickers: List of stock tickers to filter news by, or None for general news
        - topics: List of topics to filter news by, or None for all topics
                  Valid topics: ['blockchain', 'earnings', 'ipo', 'mergers_and_acquisitions', 
                                'financial_markets', 'economy_fiscal', 'economy_monetary', 
                                'economy_macro', 'energy_transportation', 'finance', 
                                'life_sciences', 'manufacturing', 'real_estate', 
                                'retail_wholesale', 'technology']
        - time_from: Start time in format YYYYMMDDTHHMM, or None for default
        - time_to: End time in format YYYYMMDDTHHMM, or None for default
        
        Returns:
        - List of news articles
        """
        api_key = self._get_next_key('alpha_vantage')
        if not api_key:
            self.logger.error("No Alpha Vantage API key available")
            return []
        
        # Construct the API request URL
        base_url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'NEWS_SENTIMENT',
            'apikey': api_key
        }
        
        # Add optional parameters
        if tickers:
            params['tickers'] = ','.join(tickers)
        
        if topics:
            params['topics'] = ','.join(topics)
        
        if time_from:
            params['time_from'] = time_from
        
        if time_to:
            params['time_to'] = time_to
        
        try:
            self.logger.info(f"Requesting news from Alpha Vantage with parameters: {params}")
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API error messages
                if 'Error Message' in data:
                    self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                    return []
                
                if 'Information' in data and 'Note' in data:
                    self.logger.warning(f"Alpha Vantage API note: {data['Information']} - {data['Note']}")
                
                # Extract feed entries
                if 'feed' in data:
                    articles = data['feed']
                    self.logger.info(f"Retrieved {len(articles)} articles from Alpha Vantage")
                    
                    # Save the raw response
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_file = os.path.join(self.output_dir, f"alpha_vantage_news_{timestamp}.json")
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"Saved raw Alpha Vantage response to {output_file}")
                    
                    # Also save as CSV
                    df = pd.DataFrame(articles)
                    csv_file = os.path.join(self.output_dir, f"alpha_vantage_news_{timestamp}.csv")
                    df.to_csv(csv_file, index=False)
                    
                    self.logger.info(f"Saved Alpha Vantage news to {csv_file}")
                    
                    return articles
                else:
                    self.logger.warning("No 'feed' found in Alpha Vantage response")
                    return []
            else:
                self.logger.error(f"Alpha Vantage API request failed with status code: {response.status_code}")
                return []
        
        except Exception as e:
            self.logger.error(f"Error retrieving news from Alpha Vantage: {str(e)}")
            return []
    
    def get_newsapi_articles(self, q: str = None, sources: List[str] = None, domains: List[str] = None, language: str = 'en', sort_by: str = 'publishedAt') -> List[Dict[str, Any]]:
        """
        Get news articles from NewsAPI.org
        
        Parameters:
        - q: Search query (e.g., 'tesla OR apple')
        - sources: List of news sources (e.g., ['bloomberg', 'financial-times'])
        - domains: List of domains (e.g., ['wsj.com', 'finance.yahoo.com'])
        - language: Language of articles (default: 'en')
        - sort_by: Sort order ('publishedAt', 'relevancy', 'popularity')
        
        Returns:
        - List of news articles
        """
        api_key = self._get_next_key('newsapi')
        if not api_key:
            self.logger.error("No NewsAPI key available")
            return []
        
        # Construct the API request URL
        base_url = 'https://newsapi.org/v2/everything'
        params = {
            'apiKey': api_key,
            'language': language,
            'sortBy': sort_by,
            'pageSize': 100  # Maximum for free tier
        }
        
        # Add optional parameters
        if q:
            params['q'] = q
        elif not sources and not domains:
            # NewsAPI requires at least one search parameter
            params['q'] = 'finance OR business OR stock OR market'
        
        if sources:
            params['sources'] = ','.join(sources)
        
        if domains:
            params['domains'] = ','.join(domains)
        
        try:
            self.logger.info(f"Requesting news from NewsAPI with parameters: {params}")
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['status'] == 'ok':
                    articles = data['articles']
                    self.logger.info(f"Retrieved {len(articles)} articles from NewsAPI")
                    
                    # Save the raw response
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    query_desc = q.replace(' ', '_')[:50] if q else 'general'
                    output_file = os.path.join(self.output_dir, f"newsapi_{query_desc}_{timestamp}.json")
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"Saved raw NewsAPI response to {output_file}")
                    
                    # Also save as CSV
                    df = pd.DataFrame(articles)
                    csv_file = os.path.join(self.output_dir, f"newsapi_{query_desc}_{timestamp}.csv")
                    df.to_csv(csv_file, index=False)
                    
                    self.logger.info(f"Saved NewsAPI articles to {csv_file}")
                    
                    return articles
                else:
                    self.logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                    return []
            else:
                self.logger.error(f"NewsAPI request failed with status code: {response.status_code}")
                return []
        
        except Exception as e:
            self.logger.error(f"Error retrieving articles from NewsAPI: {str(e)}")
            return []
    
    def get_finnhub_company_news(self, symbol: str, _from: str, to: str) -> List[Dict[str, Any]]:
        """
        Get company news from Finnhub
        
        Parameters:
        - symbol: Stock symbol (e.g., 'AAPL')
        - _from: From date in YYYY-MM-DD format
        - to: To date in YYYY-MM-DD format
        
        Returns:
        - List of news articles
        """
        api_key = self._get_next_key('finnhub')
        if not api_key:
            self.logger.error("No Finnhub API key available")
            return []
        
        # Construct the API request URL
        base_url = 'https://finnhub.io/api/v1/company-news'
        params = {
            'symbol': symbol,
            'from': _from,
            'to': to,
            'token': api_key
        }
        
        try:
            self.logger.info(f"Requesting company news from Finnhub for {symbol} from {_from} to {to}")
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    articles = data
                    self.logger.info(f"Retrieved {len(articles)} company news articles from Finnhub")
                    
                    # Save the raw response
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_file = os.path.join(self.output_dir, f"finnhub_{symbol}_news_{timestamp}.json")
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"Saved raw Finnhub response to {output_file}")
                    
                    # Also save as CSV
                    df = pd.DataFrame(articles)
                    csv_file = os.path.join(self.output_dir, f"finnhub_{symbol}_news_{timestamp}.csv")
                    df.to_csv(csv_file, index=False)
                    
                    self.logger.info(f"Saved Finnhub news to {csv_file}")
                    
                    return articles
                else:
                    self.logger.warning("Unexpected response format from Finnhub")
                    return []
            else:
                self.logger.error(f"Finnhub API request failed with status code: {response.status_code}")
                return []
        
        except Exception as e:
            self.logger.error(f"Error retrieving news from Finnhub: {str(e)}")
            return []
    
    def get_news_sentiment(self, tickers: List[str], sources: List[str] = None) -> Dict[str, Any]:
        """
        Get news sentiment for multiple sources and combine results
        
        Parameters:
        - tickers: List of stock tickers
        - sources: List of sources to use ('alpha_vantage', 'newsapi', 'finnhub')
                   or None for all available
        
        Returns:
        - Dictionary with combined results
        """
        combined_results = {
            'tickers': tickers,
            'collection_date': datetime.datetime.now().isoformat(),
            'articles': []
        }
        
        # Define available sources if not specified
        if sources is None:
            sources = []
            if 'alpha_vantage' in self.api_keys and self.api_keys['alpha_vantage']:
                sources.append('alpha_vantage')
            if 'newsapi' in self.api_keys and self.api_keys['newsapi']:
                sources.append('newsapi')
            if 'finnhub' in self.api_keys and self.api_keys['finnhub']:
                sources.append('finnhub')
        
        # Set dates for APIs
        today = datetime.date.today()
        one_month_ago = today - datetime.timedelta(days=30)
        
        # Format dates for different APIs
        alpha_vantage_time_from = one_month_ago.strftime('%Y%m%dT0000')
        alpha_vantage_time_to = today.strftime('%Y%m%dT2359')
        
        finnhub_from = one_month_ago.strftime('%Y-%m-%d')
        finnhub_to = today.strftime('%Y-%m-%d')
        
        newsapi_query = ' OR '.join(tickers)
        
        # Collect from all specified sources
        try:
            if 'alpha_vantage' in sources:
                self.logger.info("Collecting news from Alpha Vantage")
                alpha_vantage_articles = self.get_alpha_vantage_news(
                    tickers=tickers,
                    time_from=alpha_vantage_time_from,
                    time_to=alpha_vantage_time_to
                )
                
                for article in alpha_vantage_articles:
                    article['source'] = 'alpha_vantage'
                    combined_results['articles'].append(article)
            
            if 'newsapi' in sources:
                self.logger.info("Collecting news from NewsAPI")
                newsapi_articles = self.get_newsapi_articles(
                    q=newsapi_query
                )
                
                for article in newsapi_articles:
                    article['source'] = 'newsapi'
                    combined_results['articles'].append(article)
            
            if 'finnhub' in sources and tickers:
                self.logger.info("Collecting news from Finnhub")
                
                # Finnhub requires separate API calls for each ticker
                for ticker in tickers:
                    finnhub_articles = self.get_finnhub_company_news(
                        symbol=ticker,
                        _from=finnhub_from,
                        to=finnhub_to
                    )
                    
                    for article in finnhub_articles:
                        article['source'] = 'finnhub'
                        article['ticker'] = ticker
                        combined_results['articles'].append(article)
                    
                    # Add a delay between API calls
                    time.sleep(1)
            
            # Save combined results
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            tickers_str = '_'.join(tickers) if len(tickers) <= 3 else f"{len(tickers)}_tickers"
            output_file = os.path.join(self.output_dir, f"combined_news_{tickers_str}_{timestamp}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(combined_results, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Saved combined results with {len(combined_results['articles'])} articles to {output_file}")
            
            # Create a simplified CSV with standardized columns
            simplified = []
            
            for article in combined_results['articles']:
                # Extract common fields with appropriate fallbacks based on source
                if article['source'] == 'alpha_vantage':
                    simplified.append({
                        'source': 'alpha_vantage',
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'published_date': article.get('time_published', ''),
                        'summary': article.get('summary', ''),
                        'sentiment': article.get('overall_sentiment_score', None),
                        'tickers': ','.join([t.get('ticker', '') for t in article.get('ticker_sentiment', [])]),
                        'source_name': article.get('source', '')
                    })
                elif article['source'] == 'newsapi':
                    simplified.append({
                        'source': 'newsapi',
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'published_date': article.get('publishedAt', ''),
                        'summary': article.get('description', ''),
                        'sentiment': None,  # NewsAPI doesn't provide sentiment
                        'tickers': newsapi_query,  # Use the search query as proxy
                        'source_name': article.get('source', {}).get('name', '')
                    })
                elif article['source'] == 'finnhub':
                    simplified.append({
                        'source': 'finnhub',
                        'title': article.get('headline', ''),
                        'url': article.get('url', ''),
                        'published_date': datetime.datetime.fromtimestamp(article.get('datetime', 0)).isoformat(),
                        'summary': article.get('summary', ''),
                        'sentiment': article.get('sentiment', None),
                        'tickers': article.get('ticker', ''),
                        'source_name': article.get('source', '')
                    })
            
            # Save simplified CSV
            csv_file = os.path.join(self.output_dir, f"combined_news_{tickers_str}_{timestamp}.csv")
            pd.DataFrame(simplified).to_csv(csv_file, index=False)
            
            self.logger.info(f"Saved simplified CSV to {csv_file}")
            
            return combined_results
        
        except Exception as e:
            self.logger.error(f"Error in get_news_sentiment: {str(e)}")
            return combined_results
    
    def key_rotation_demo(self, service: str, num_requests: int = 100, delay: float = 0.5):
        """
        Demonstrate API key rotation by making multiple requests
        
        Parameters:
        - service: Service to demonstrate ('alpha_vantage', 'newsapi', 'finnhub')
        - num_requests: Number of simulated requests
        - delay: Delay between requests in seconds
        
        Returns:
        - Dictionary with key usage statistics
        """
        if service not in self.api_keys or not self.api_keys[service]:
            self.logger.error(f"No API keys available for {service}")
            return {}
        
        self.logger.info(f"Starting key rotation demo for {service} with {len(self.api_keys[service])} keys")
        self.logger.info(f"Will simulate {num_requests} requests with {delay}s delay between requests")
        
        # Reset key usage for this demo
        self.key_usage[service] = {key: 0 for key in self.api_keys[service]}
        
        for i in range(num_requests):
            key = self._get_next_key(service)
            self.logger.info(f"Request {i+1}/{num_requests}: Using key '{key[:5]}...'")
            
            # Simulate an API request
            time.sleep(delay)
        
        # Report usage statistics
        stats = {
            'service': service,
            'total_requests': num_requests,
            'num_keys': len(self.api_keys[service]),
            'key_usage': self.key_usage[service],
            'average_per_key': num_requests / len(self.api_keys[service]) if self.api_keys[service] else 0
        }
        
        self.logger.info(f"Key rotation demo completed for {service}")
        self.logger.info(f"Usage statistics: {stats}")
        
        return stats

# Example usage:
if __name__ == "__main__":
    # Example configuration
    output_dir = "financial_news_api"
    
    # API keys (replace with your own)
    api_keys = {
        'alpha_vantage': ['YOUR_ALPHA_VANTAGE_KEY_1', 'YOUR_ALPHA_VANTAGE_KEY_2'],
        'newsapi': ['YOUR_NEWSAPI_KEY'],
        'finnhub': ['YOUR_FINNHUB_KEY']
    }
    
    news_api = FinancialNewsAPI(output_dir, api_keys)
    
    # Option 1: Get news from Alpha Vantage
    alpha_vantage_news = news_api.get_alpha_vantage_news(
        tickers=['AAPL', 'MSFT', 'GOOGL'],
        topics=['earnings', 'technology']
    )
    
    # Option 2: Get news from NewsAPI
    newsapi_articles = news_api.get_newsapi_articles(
        q='(AAPL OR Apple) AND earnings',
        domains=['wsj.com', 'bloomberg.com', 'finance.yahoo.com']
    )
    
    # Option 3: Get news from Finnhub
    today = datetime.date.today()
    one_month_ago = today - datetime.timedelta(days=30)
    
    finnhub_news = news_api.get_finnhub_company_news(
        symbol='AAPL',
        _from=one_month_ago.strftime('%Y-%m-%d'),
        to=today.strftime('%Y-%m-%d')
    )
    
    # Option 4: Get combined news sentiment
    combined_results = news_api.get_news_sentiment(
        tickers=['AAPL', 'MSFT', 'GOOGL'],
        sources=['alpha_vantage', 'newsapi', 'finnhub']
    )
    
    # Option 5: Demonstrate API key rotation
    # news_api.key_rotation_demo('alpha_vantage', num_requests=50, delay=0.1)
```

**Limitations and Considerations:**
- Free tier limitations vary significantly by provider
- Daily API call limits restrict the amount of data that can be collected
- Content quality and completeness may vary between providers
- Real-time data is often reserved for paid tiers

### 3.3 Academic & Public Datasets

Several academic and public datasets are available for financial sentiment analysis research.

**Current Status:**
- Kaggle offers datasets specifically for financial sentiment analysis, including "Sentiment Analysis for Financial News" with sentiment labels for news headlines.
- Financial sentiment analysis datasets help users "make more informed decisions" by understanding the sentiment behind financial news.

**Recommended Implementation:**
- Kaggle financial sentiment datasets for training models
- Academic repositories (arXiv, university sites) for established benchmark datasets
- Public financial forums dataset collections

**Implementation Code Approach:**
```python
import os
import pandas as pd
import requests
import zipfile
import io
import logging
import json
import datetime
import re
from typing import List, Dict, Any, Optional

class FinancialSentimentDatasets:
    """
    Class for downloading, processing, and combining financial sentiment datasets
    """
    
    # URLs to known public financial sentiment datasets
    DATASET_SOURCES = {
        'kaggle_financial_news': {
            'name': 'Sentiment Analysis for Financial News',
            'url': 'https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news/download',
            'description': 'Dataset contains sentiment and news headline columns for financial news',
            'requires_auth': True,
            'format': 'csv'
        },
        'financial_phrasebank': {
            'name': 'Financial PhraseBank',
            'url': 'https://www.researchgate.net/profile/Pekka_Malo/publication/251231364_FinancialPhraseBank-v10/data/0c96051eee4fb1d56e000000/FinancialPhraseBank-v10.zip',
            'description': 'Sentences from financial news categorized by sentiment',
            'requires_auth': False,
            'format': 'zip'
        },
        'financial_sentiment_analysis': {
            'name': 'Financial Sentiment Analysis',
            'url': 'https://www.kaggle.com/datasets/sbhatti/financial-sentiment-analysis/download',
            'description': 'Financial sentences with sentiment labels',
            'requires_auth': True,
            'format': 'csv'
        }
    }
    
    def __init__(self, output_dir: str, kaggle_config: Dict[str, str] = None):
        """
        Initialize the Financial Sentiment Datasets handler
        
        Parameters:
        - output_dir: Directory to save downloaded datasets
        - kaggle_config: Kaggle API credentials {'username': '...', 'key': '...'}
                         or None to use environment variables KAGGLE_USERNAME and KAGGLE_KEY
        """
        self.output_dir = output_dir
        self.kaggle_config = kaggle_config
        self.logger = self._setup_logger()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Set up Kaggle API credentials if provided
        if kaggle_config:
            os.environ['KAGGLE_USERNAME'] = kaggle_config.get('username', '')
            os.environ['KAGGLE_KEY'] = kaggle_config.get('key', '')
    
    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger("financial_sentiment_datasets")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        fh = logging.FileHandler("financial_sentiment_datasets.log")
        fh.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def list_available_datasets(self) -> Dict[str, Dict[str, Any]]:
        """
        List available datasets
        
        Returns:
        - Dictionary of dataset information
        """
        return self.DATASET_SOURCES
    
    def download_dataset(self, dataset_id: str, use_kaggle_api: bool = True) -> Optional[str]:
        """
        Download a dataset
        
        Parameters:
        - dataset_id: ID of the dataset to download
        - use_kaggle_api: Whether to use the Kaggle API for Kaggle datasets
        
        Returns:
        - Path to the downloaded dataset or None if failed
        """
        if dataset_id not in self.DATASET_SOURCES:
            self.logger.error(f"Dataset {dataset_id} not found in available datasets")
            return None
        
        dataset_info = self.DATASET_SOURCES[dataset_id]
        self.logger.info(f"Downloading dataset: {dataset_info['name']}")
        
        # Create subdirectory for this dataset
        dataset_dir = os.path.join(self.output_dir, dataset_id)
        if not os.path.exists(dataset_dir):
            os.makedirs(dataset_dir)
        
        # For Kaggle datasets, try to use the Kaggle API if requested
        if 'kaggle' in dataset_id and use_kaggle_api:
            try:
                from kaggle.api.kaggle_api_extended import KaggleApi
                
                api = KaggleApi()
                api.authenticate()
                
                # Extract dataset name from URL
                # URL format: https://www.kaggle.com/datasets/[username]/[dataset-name]/download
                url_parts = dataset_info['url'].replace('https://www.kaggle.com/datasets/', '').split('/')
                if len(url_parts) >= 2:
                    dataset_name = f"{url_parts[0]}/{url_parts[1]}"
                    
                    self.logger.info(f"Downloading Kaggle dataset: {dataset_name}")
                    api.dataset_download_files(dataset_name, path=dataset_dir, unzip=True)
                    
                    # Check what files were downloaded
                    downloaded_files = os.listdir(dataset_dir)
                    self.logger.info(f"Downloaded files: {downloaded_files}")
                    
                    return dataset_dir
                else:
                    self.logger.warning(f"Could not parse Kaggle dataset name from URL: {dataset_info['url']}")
            except ImportError:
                self.logger.warning("Kaggle API not installed. Run 'pip install kaggle' to use this feature.")
            except Exception as e:
                self.logger.warning(f"Error using Kaggle API: {str(e)}")
                self.logger.warning("Falling back to direct download method")
        
        # Direct download method
        try:
            output_file = os.path.join(dataset_dir, f"{dataset_id}.{dataset_info['format']}")
            
            # Make the request
            self.logger.info(f"Downloading from URL: {dataset_info['url']}")
            response = requests.get(dataset_info['url'], stream=True)
            
            if response.status_code == 200:
                # Save the downloaded file
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.logger.info(f"Downloaded dataset to {output_file}")
                
                # Extract if it's a zip file
                if dataset_info['format'] == 'zip':
                    self.logger.info("Extracting ZIP archive")
                    with zipfile.ZipFile(output_file, 'r') as zip_ref:
                        zip_ref.extractall(dataset_dir)
                    self.logger.info(f"Extracted ZIP contents to {dataset_dir}")
                
                return dataset_dir
            else:
                self.logger.error(f"Failed to download dataset: HTTP status code {response.status_code}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error downloading dataset {dataset_id}: {str(e)}")
            return None
    
    def load_financial_phrasebank(self, dir_path: str, agreement_threshold: float = 0.75) -> pd.DataFrame:
        """
        Load the Financial PhraseBank dataset
        
        Parameters:
        - dir_path: Path to the extracted dataset directory
        - agreement_threshold: Minimum proportion of annotators that must agree (0.5-1.0)
        
        Returns:
        - Pandas DataFrame with the dataset
        """
        self.logger.info(f"Loading Financial PhraseBank from {dir_path}")
        
        # Map agreement levels to filenames
        agreement_files = {
            0.5: 'Sentences_50Agree.txt',
            0.6: 'Sentences_60Agree.txt',
            0.67: 'Sentences_66Agree.txt',
            0.75: 'Sentences_75Agree.txt',
            1.0: 'Sentences_AllAgree.txt'
        }
        
        # Find the closest agreement threshold
        thresholds = sorted(agreement_files.keys())
        selected_threshold = min(thresholds, key=lambda x: abs(x - agreement_threshold))
        
        filename = agreement_files[selected_threshold]
        file_path = None
        
        # Look for the file in the directory
        for root, _, files in os.walk(dir_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                break
        
        if not file_path:
            self.logger.error(f"Could not find {filename} in {dir_path}")
            return pd.DataFrame()
        
        # Load the data
        try:
            data = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # Format is: sentence@sentiment
                        parts = line.split('@')
                        if len(parts) == 2:
                            sentence = parts[0].strip()
                            sentiment = parts[1].strip()
                            
                            data.append({
                                'sentence': sentence,
                                'sentiment': sentiment
                            })
            
            df = pd.DataFrame(data)
            self.logger.info(f"Loaded {len(df)} sentences from Financial PhraseBank with {selected_threshold} agreement")
            
            # Map numeric sentiment to categories
            sentiment_map = {'0': 'negative', '1': 'neutral', '2': 'positive'}
            df['sentiment_label'] = df['sentiment'].map(sentiment_map)
            
            return df
        
        except Exception as e:
            self.logger.error(f"Error loading Financial PhraseBank: {str(e)}")
            return pd.DataFrame()
    
    def load_kaggle_financial_news(self, dir_path: str) -> pd.DataFrame:
        """
        Load the Kaggle Financial News Sentiment dataset
        
        Parameters:
        - dir_path: Path to the downloaded dataset directory
        
        Returns:
        - Pandas DataFrame with the dataset
        """
        self.logger.info(f"Loading Kaggle Financial News Sentiment from {dir_path}")
        
        # Try to find the CSV file
        csv_files = [f for f in os.listdir(dir_path) if f.endswith('.csv')]
        
        if not csv_files:
            self.logger.error(f"No CSV files found in {dir_path}")
            return pd.DataFrame()
        
        # Try to load each CSV file until one works
        for csv_file in csv_files:
            try:
                file_path = os.path.join(dir_path, csv_file)
                df = pd.read_csv(file_path)
                
                # Check if it has the expected columns
                if 'Sentiment' in df.columns and ('News Headline' in df.columns or 'text' in df.columns):
                    # Standardize column names
                    if 'News Headline' in df.columns:
                        df.rename(columns={'News Headline': 'text', 'Sentiment': 'sentiment'}, inplace=True)
                    
                    self.logger.info(f"Loaded {len(df)} rows from {csv_file}")
                    return df
            
            except Exception as e:
                self.logger.warning(f"Error loading {csv_file}: {str(e)}")
        
        self.logger.error("Could not load any valid CSV file")
        return pd.DataFrame()
    
    def load_financial_sentiment_analysis(self, dir_path: str) -> pd.DataFrame:
        """
        Load the Financial Sentiment Analysis dataset
        
        Parameters:
        - dir_path: Path to the downloaded dataset directory
        
        Returns:
        - Pandas DataFrame with the dataset
        """
        self.logger.info(f"Loading Financial Sentiment Analysis from {dir_path}")
        
        # Try to find the data file
        data_files = [f for f in os.listdir(dir_path) if f.endswith(('.csv', '.txt', '.json'))]
        
        if not data_files:
            self.logger.error(f"No data files found in {dir_path}")
            return pd.DataFrame()
        
        # Try to load each file until one works
        for data_file in data_files:
            try:
                file_path = os.path.join(dir_path, data_file)
                
                if data_file.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif data_file.endswith('.json'):
                    df = pd.read_json(file_path)
                elif data_file.endswith('.txt'):
                    # Assuming tab-separated or similar format
                    df = pd.read_csv(file_path, sep='\t')
                else:
                    continue
                
                # Check if it has the expected sentiment column
                sentiment_columns = [col for col in df.columns if 'sentiment' in col.lower()]
                text_columns = [col for col in df.columns if col.lower() in ['text', 'sentence', 'content', 'headline']]
                
                if sentiment_columns and text_columns:
                    # Standardize column names
                    df.rename(columns={sentiment_columns[0]: 'sentiment', text_columns[0]: 'text'}, inplace=True)
                    
                    self.logger.info(f"Loaded {len(df)} rows from {data_file}")
                    return df
            
            except Exception as e:
                self.logger.warning(f"Error loading {data_file}: {str(e)}")
        
        self.logger.error("Could not load any valid data file")
        return pd.DataFrame()
    
    def standardize_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize a dataset to have consistent column names and value formats
        
        Parameters:
        - df: Input DataFrame
        
        Returns:
        - Standardized DataFrame
        """
        if df.empty:
            return df
        
        # Create a copy to avoid modifying the original
        standardized = df.copy()
        
        # Rename columns to standard format if needed
        column_mapping = {}
        
        for col in standardized.columns:
            col_lower = col.lower()
            if 'text' in col_lower or 'headline' in col_lower or 'sentence' in col_lower:
                column_mapping[col] = 'text'
            elif 'sentiment' in col_lower or 'label' in col_lower:
                column_mapping[col] = 'sentiment'
        
        standardized.rename(columns=column_mapping, inplace=True)
        
        # Ensure required columns exist
        required_cols = ['text', 'sentiment']
        missing = [col for col in required_cols if col not in standardized.columns]
        
        if missing:
            self.logger.warning(f"Standardized dataset is missing required columns: {missing}")
            for col in missing:
                standardized[col] = None
        
        # Standardize sentiment values
        if 'sentiment' in standardized.columns:
            # Map various sentiment formats to a standard format
            sentiment_map = {}
            
            # Check the unique values
            unique_sentiments = standardized['sentiment'].unique()
            
            # If sentiments are numeric or string representations of numbers
            if all(str(s).isdigit() for s in unique_sentiments if pd.notna(s)):
                sentiment_map = {
                    '0': 'negative',
                    0: 'negative',
                    '1': 'neutral',
                    1: 'neutral',
                    '2': 'positive',
                    2: 'positive'
                }
            # If sentiments are already string labels
            else:
                for s in unique_sentiments:
                    if pd.isna(s):
                        continue
                    s_lower = str(s).lower()
                    if 'neg' in s_lower or 'bear' in s_lower:
                        sentiment_map[s] = 'negative'
                    elif 'neu' in s_lower:
                        sentiment_map[s] = 'neutral'
                    elif 'pos' in s_lower or 'bull' in s_lower:
                        sentiment_map[s] = 'positive'
            
            # Apply the mapping where possible
            if sentiment_map:
                standardized['sentiment_mapped'] = standardized['sentiment'].map(
                    sentiment_map).fillna(standardized['sentiment'])
                standardized['sentiment'] = standardized['sentiment_mapped']
                standardized.drop(columns=['sentiment_mapped'], inplace=True)
        
        # Add metadata
        standardized['standardized_date'] = datetime.datetime.now().isoformat()
        
        return standardized
    
    def combine_datasets(self, dataframes: List[pd.DataFrame], output_file: str = None) -> pd.DataFrame:
        """
        Combine multiple standardized datasets
        
        Parameters:
        - dataframes: List of standardized DataFrames
        - output_file: Path to save the combined dataset, or None to skip saving
        
        Returns:
        - Combined DataFrame
        """
        if not dataframes:
            self.logger.warning("No datasets provided to combine")
            return pd.DataFrame()
        
        # Filter out empty dataframes
        valid_dfs = [df for df in dataframes if not df.empty]
        
        if not valid_dfs:
            self.logger.warning("All provided datasets are empty")
            return pd.DataFrame()
        
        # Ensure all dataframes have the same columns
        required_cols = ['text', 'sentiment']
        for i, df in enumerate(valid_dfs):
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                self.logger.warning(f"Dataset {i} is missing required columns: {missing}")
                for col in missing:
                    df[col] = None
        
        # Add source column to track origin
        for i, df in enumerate(valid_dfs):
            df['source_dataset'] = f"dataset_{i}"
        
        # Combine all dataframes
        combined = pd.concat(valid_dfs, ignore_index=True)
        
        self.logger.info(f"Combined {len(valid_dfs)} datasets with {len(combined)} total rows")
        
        # Save to file if requested
        if output_file:
            output_path = os.path.join(self.output_dir, output_file)
            combined.to_csv(output_path, index=False)
            self.logger.info(f"Saved combined dataset to {output_path}")
        
        return combined
    
    def analyze_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a sentiment dataset to provide statistics
        
        Parameters:
        - df: Dataset DataFrame
        
        Returns:
        - Dictionary with analysis results
        """
        if df.empty:
            return {'error': 'Empty dataset'}
        
        analysis = {
            'row_count': len(df),
            'columns': list(df.columns),
            'sentiment_distribution': {},
            'text_length_stats': {},
            'missing_values': {},
            'sample_rows': []
        }
        
        # Sentiment distribution
        if 'sentiment' in df.columns:
            sentiment_counts = df['sentiment'].value_counts().to_dict()
            total = sum(sentiment_counts.values())
            
            analysis['sentiment_distribution'] = {
                'counts': sentiment_counts,
                'percentages': {k: round(v / total * 100, 2) for k, v in sentiment_counts.items()}
            }
        
        # Text length statistics
        if 'text' in df.columns:
            # Calculate text lengths
            text_lengths = df['text'].str.len()
            
            analysis['text_length_stats'] = {
                'min': text_lengths.min(),
                'max': text_lengths.max(),
                'mean': round(text_lengths.mean(), 2),
                'median': text_lengths.median(),
                # Group by length ranges
                'length_distribution': {
                    '1-50 chars': len(df[text_lengths <= 50]),
                    '51-100 chars': len(df[(text_lengths > 50) & (text_lengths <= 100)]),
                    '101-250 chars': len(df[(text_lengths > 100) & (text_lengths <= 250)]),
                    '251-500 chars': len(df[(text_lengths > 250) & (text_lengths <= 500)]),
                    '500+ chars': len(df[text_lengths > 500])
                }
            }
        
        # Missing values
        for col in df.columns:
            missing = df[col].isna().sum()
            if missing > 0:
                analysis['missing_values'][col] = {
                    'count': int(missing),
                    'percentage': round(missing / len(df) * 100, 2)
                }
        
        # Sample rows
        if len(df) > 5:
            analysis['sample_rows'] = df.sample(5).to_dict('records')
        else:
            analysis['sample_rows'] = df.to_dict('records')
        
        return analysis
    
    def create_training_validation_sets(self, df: pd.DataFrame, validation_size: float = 0.2, 
                                        stratify: bool = True, output_prefix: str = None) -> Dict[str, pd.DataFrame]:
        """
        Split a dataset into training and validation sets
        
        Parameters:
        - df: Input DataFrame
        - validation_size: Proportion to use for validation (0.0-1.0)
        - strat
        I'll continue with the implementation code for the `create_training_validation_sets` method and complete the remaining sections of the report:

```python
    def create_training_validation_sets(self, df: pd.DataFrame, validation_size: float = 0.2, 
                                        stratify: bool = True, output_prefix: str = None) -> Dict[str, pd.DataFrame]:
        """
        Split a dataset into training and validation sets
        
        Parameters:
        - df: Input DataFrame
        - validation_size: Proportion to use for validation (0.0-1.0)
        - stratify: Whether to maintain class distribution in splits
        - output_prefix: Prefix for output files, or None to skip saving
        
        Returns:
        - Dictionary with 'train' and 'validation' DataFrames
        """
        if df.empty:
            self.logger.warning("Cannot split an empty dataset")
            return {'train': pd.DataFrame(), 'validation': pd.DataFrame()}
        
        try:
            from sklearn.model_selection import train_test_split
            
            # Check if stratification is possible
            stratify_col = None
            if stratify and 'sentiment' in df.columns:
                # Check if there are enough samples in each class
                class_counts = df['sentiment'].value_counts()
                if len(class_counts) > 1 and all(count >= 2 for count in class_counts):
                    stratify_col = df['sentiment']
                else:
                    self.logger.warning("Not enough samples in each class for stratification")
            
            # Split the dataset
            train_df, val_df = train_test_split(
                df, 
                test_size=validation_size,
                random_state=42,
                stratify=stratify_col
            )
            
            self.logger.info(f"Split dataset: {len(train_df)} training samples, {len(val_df)} validation samples")
            
            # Save to files if requested
            if output_prefix:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                train_path = os.path.join(self.output_dir, f"{output_prefix}_train_{timestamp}.csv")
                val_path = os.path.join(self.output_dir, f"{output_prefix}_validation_{timestamp}.csv")
                
                train_df.to_csv(train_path, index=False)
                val_df.to_csv(val_path, index=False)
                
                self.logger.info(f"Saved training set to {train_path}")
                self.logger.info(f"Saved validation set to {val_path}")
            
            return {'train': train_df, 'validation': val_df}
        
        except ImportError:
            self.logger.warning("scikit-learn not installed. Install with 'pip install scikit-learn'")
            
            # Fallback to manual split
            n = len(df)
            val_size = int(n * validation_size)
            
            # Shuffle the DataFrame
            shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)
            
            # Split
            train_df = shuffled.iloc[val_size:]
            val_df = shuffled.iloc[:val_size]
            
            self.logger.info(f"Split dataset (manual): {len(train_df)} training samples, {len(val_df)} validation samples")
            
            # Save to files if requested
            if output_prefix:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                train_path = os.path.join(self.output_dir, f"{output_prefix}_train_{timestamp}.csv")
                val_path = os.path.join(self.output_dir, f"{output_prefix}_validation_{timestamp}.csv")
                
                train_df.to_csv(train_path, index=False)
                val_df.to_csv(val_path, index=False)
                
                self.logger.info(f"Saved training set to {train_path}")
                self.logger.info(f"Saved validation set to {val_path}")
            
            return {'train': train_df, 'validation': val_df}
    
    def download_and_prepare_all(self) -> Dict[str, pd.DataFrame]:
        """
        Download, load, and standardize all available datasets
        
        Returns:
        - Dictionary mapping dataset IDs to standardized DataFrames
        """
        results = {}
        
        for dataset_id in self.DATASET_SOURCES:
            try:
                self.logger.info(f"Processing dataset: {dataset_id}")
                
                # Download the dataset
                dataset_dir = self.download_dataset(dataset_id)
                
                if not dataset_dir:
                    self.logger.warning(f"Failed to download {dataset_id}, skipping")
                    continue
                
                # Load the dataset based on its type
                if dataset_id == 'financial_phrasebank':
                    df = self.load_financial_phrasebank(dataset_dir)
                elif dataset_id == 'kaggle_financial_news':
                    df = self.load_kaggle_financial_news(dataset_dir)
                elif dataset_id == 'financial_sentiment_analysis':
                    df = self.load_financial_sentiment_analysis(dataset_dir)
                else:
                    self.logger.warning(f"No specific loader for {dataset_id}, skipping")
                    continue
                
                if df.empty:
                    self.logger.warning(f"Failed to load {dataset_id}, skipping")
                    continue
                
                # Standardize the dataset
                standardized = self.standardize_dataset(df)
                
                # Save the standardized dataset
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                std_path = os.path.join(self.output_dir, f"{dataset_id}_standardized_{timestamp}.csv")
                standardized.to_csv(std_path, index=False)
                
                self.logger.info(f"Saved standardized {dataset_id} to {std_path}")
                
                # Add to results
                results[dataset_id] = standardized
                
                # Generate and save dataset analysis
                analysis = self.analyze_dataset(standardized)
                analysis_path = os.path.join(self.output_dir, f"{dataset_id}_analysis_{timestamp}.json")
                
                with open(analysis_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"Saved {dataset_id} analysis to {analysis_path}")
            
            except Exception as e:
                self.logger.error(f"Error processing {dataset_id}: {str(e)}")
        
        # Create a combined dataset if we have multiple successfully processed datasets
        if len(results) > 1:
            self.logger.info("Creating combined dataset")
            combined = self.combine_datasets(list(results.values()), output_file="combined_financial_sentiment.csv")
            results['combined'] = combined
        
        return results

# Example usage:
if __name__ == "__main__":
    # Example configuration
    output_dir = "financial_sentiment_datasets"
    
    # Optional: Kaggle credentials for authenticated downloads
    # kaggle_config = {
    #     'username': 'YOUR_KAGGLE_USERNAME',
    #     'key': 'YOUR_KAGGLE_API_KEY'
    # }
    
    # Initialize without Kaggle credentials
    datasets = FinancialSentimentDatasets(output_dir)
    
    # List available datasets
    available = datasets.list_available_datasets()
    print("Available datasets:")
    for dataset_id, info in available.items():
        print(f"  - {info['name']}: {info['description']}")
    
    # Option 1: Download and process a single dataset
    dataset_dir = datasets.download_dataset('financial_phrasebank')
    if dataset_dir:
        df = datasets.load_financial_phrasebank(dataset_dir)
        standardized = datasets.standardize_dataset(df)
        analysis = datasets.analyze_dataset(standardized)
        print("Dataset analysis:", analysis)
        
        # Split into training and validation sets
        splits = datasets.create_training_validation_sets(
            standardized, 
            validation_size=0.2,
            output_prefix='financial_phrasebank'
        )
        
        print(f"Training set: {len(splits['train'])} samples")
        print(f"Validation set: {len(splits['validation'])} samples")
    
    # Option 2: Process all datasets and create a combined dataset
    # all_datasets = datasets.download_and_prepare_all()
    # print(f"Processed {len(all_datasets)} datasets")
    # 
    # if 'combined' in all_datasets:
    #     combined = all_datasets['combined']
    #     print(f"Combined dataset: {len(combined)} samples")
```

## 3.4 Social Media (Beyond Reddit)

While Reddit has been a valuable source of financial sentiment data, there are other social media platforms that can provide insights. However, access to these platforms comes with varying degrees of restrictions and limitations, especially for free data collection.

**Current Status:**
- **Twitter (X)**: Access to the API has become significantly restricted and requires a paid tier for meaningful data collection.
- **StockTwits**: Offers a more finance-specific alternative, but comprehensive historical data requires a paid API plan.
- **LinkedIn**: Limited API access for non-partners, primarily focused on profile information rather than content.
- **Facebook**: Public data access is restricted, with focus on Pages API for business-related content only.

**Ethical and Legal Considerations:**
- Public sentiment data collection must respect platform Terms of Service
- Scraping is generally against ToS and may result in IP banning
- Personal identifiable information should be anonymized
- Rate limits must be strictly observed

## 4. Recommendations & Conclusions

### 4.1 Recommended Methods Summary

Based on the research and implementation work, here are the recommended free methods for financial sentiment data collection:

#### For Bulk Historical Data:
1. **SEC EDGAR Database**: Most reliable source for regulatory financial information with official API
   - **Pros**: Structured data, comprehensive coverage, legal compliance
   - **Cons**: Technical text, requires parsing expertise, limited sentiment expression

2. **Wayback Machine**: Valuable for historical news articles from financial websites
   - **Pros**: Captures deleted/archived content, extensive history
   - **Cons**: Incomplete archive coverage, rate limits, HTML processing overhead

3. **Kaggle Financial Datasets**: Pre-labeled sentiment datasets for model training
   - **Pros**: Ready-to-use, professionally labeled, diverse sources
   - **Cons**: Limited to available datasets, potential biases in labeling

#### For Near-Real-Time Feeds:
1. **RSS Feeds from Financial News Sources**: Most accessible approach for current news
   - **Pros**: Simple implementation, diverse sources, continuous updates
   - **Cons**: Limited historical depth, inconsistent structure across sources

2. **Alpha Vantage News API**: Best free API option with sentiment scores
   - **Pros**: Includes machine learning-based sentiment scores, structured data
   - **Cons**: Limited to 25 requests/day in free tier, requires key rotation for scale

3. **Reddit API (PRAW)**: For community sentiment despite limited historical access
   - **Pros**: Direct access to retail investor sentiment, active communities
   - **Cons**: Limited historical data, rate limits, potential sampling bias

### 4.2 Implementation Strategy

For optimal results with free tools, I recommend this implementation approach:

1. **Build a Modular Pipeline**:
   - Start with RSS feed collection as the backbone for current news
   - Augment with Alpha Vantage API calls for pre-scored sentiment
   - Use SEC EDGAR for company-specific events and disclosures
   - Incorporate public datasets for model training and benchmarking

2. **Key Rotation System for APIs**:
   - Implement the key rotation pattern from the API code examples
   - Manage multiple free tier keys to maximize daily quota
   - Schedule regular but spaced collection to avoid rate limit issues

3. **Storage and Processing Strategy**:
   - Maintain a local database of collected text for historical analysis
   - Use standardized format across sources (with source tracking)
   - Implement incremental collection to build depth over time

### 4.3 Limitations of Free Data Sources

Users should be aware of these inherent limitations:

- **Coverage Gaps**: Free sources often exclude premium content and real-time data
- **Limited Historical Depth**: Many free sources provide only recent information
- **Inconsistent Quality**: Varying reliability, completeness, and accuracy
- **Technical Challenges**: Parsing, normalization, and API changes require maintenance
- **Scale Constraints**: Free tiers restrict the volume and frequency of data collection

### 4.4 Conclusion

This project has demonstrated that while comprehensive financial sentiment analysis using exclusively free resources has limitations, a strategic combination of the methods described can yield a viable dataset for research and analysis. By leveraging multiple free data sources and implementing robust, modular collection code, it's possible to build a sentiment analysis system that provides valuable insights without incurring API costs.

The most successful approach combines RSS feeds for near-real-time data, SEC EDGAR for official company disclosures, public datasets for model training, and free API tiers with key rotation for additional structured content. This diversified approach mitigates the limitations of any single free source while providing a breadth of perspectives for sentiment analysis.

For production applications requiring more reliable, higher-volume data collection, graduated movement to paid tiers may eventually become necessary. However, the free methods detailed in this report provide an excellent starting point and may be sufficient for many research applications and smaller-scale analyses.

**TL;DR –** While free financial data sources have limitations in volume and history, combining Wayback Machine for archives, SEC EDGAR for filings, RSS feeds for real-time news, and public datasets provides a viable foundation for financial sentiment analysis without paid API subscriptions.