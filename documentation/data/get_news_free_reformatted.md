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

#### Current Status:
- The Wayback CDX Server API allows programmatic access to the Internet Archive's historical web captures through a standalone HTTP servlet that serves the index the Wayback Machine uses for lookups.
- Python clients can interact with both the CDX API and Memento API, with libraries implementing methods for these standards.

#### Recommended Implementation:
- **Library Choice**: The `waybackpy` library appears most suitable as it interfaces with the Internet Archive's Wayback Machine APIs, allowing for archiving pages and retrieving archived pages.
- **Alternative**: For more advanced requirements, the `wayback` package offers a Python client that can speak both CDX API and Memento API standards.

#### Implementation Code Approach:
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

#### Limitations and Considerations:
- The API has rate limits that must be respected
- Not all pages or content may be archived
- Historical completeness varies by site and time period
- Content extraction from HTML requires additional processing

### 2.2 SEC EDGAR Filings Extractor

The SEC EDGAR database provides a wealth of structured financial information in the form of regulatory filings.

#### Current Status:
- The SEC provides APIs for accessing EDGAR data, with comprehensive documentation for developing applications.
- Multiple Python libraries exist to facilitate this access, with varying features and limitations.

#### Recommended Implementation:
- For free access, a combination of the official SEC API and Python libraries can be used.
- The "edgartools" library is described as "the world's easiest, most powerful edgar library" and offers a comprehensive feature set.
- The "sec-api" package allows searching "the entire SEC EDGAR filings corpus, providing access to petabytes of regulatory data", though it has usage limits in its free tier.

#### Implementation Code Approach:
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

#### Limitations and Considerations:
- SEC's API has rate limiting requirements (10 requests per second per IP)
- An email address must be provided in the request headers
- Filings structure can vary significantly, especially for older documents
- Text extraction from HTML/XML filings requires robust parsing

### 2.3 Reddit Financial Data Collector

The Pushshift API was traditionally the go-to option for collecting historical Reddit data. However, based on recent research, its status has changed significantly.

#### Current Status:
- Reddit is now partnering with Pushshift to grant access to moderation tools, but access is limited to verified Reddit moderators.
- This represents a major shift from the previously open Pushshift API access model.

#### Recommended Implementation:
- The official Reddit API (PRAW) is now the primary method, though it has limitations for historical data.
- For research purposes, PSAW (PushShift API Wrapper) can be used to access data, but it's dependent on the restricted Pushshift API.

#### Implementation Code Approach:
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
        try:
            reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                # Optional: Add username/password for user context if needed,
                # but script auth is usually sufficient for reading public data.
                # username="YOUR_REDDIT_USERNAME",
                # password="YOUR_REDDIT_PASSWORD",
                read_only=True # Set to False if you need to perform actions
            )
            # Test connection
            self.logger.info(f"Reddit API ReadOnly Mode: {reddit.read_only}")
            # Accessing user requires read_only=False and credentials
            # self.logger.info(f"Authenticated as: {reddit.user.me()}")
            return reddit
        except Exception as e:
            self.logger.error(f"Failed to initialize PRAW client: {e}")
            raise # Reraise exception to prevent proceeding without a client
    
    def _setup_logger(self):
        """Configure logging"""
        logger = logging.getLogger("reddit_data_collector")
        logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers if called multiple times
        if not logger.handlers:
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
    
    def _handle_rate_limit(self, exception):
        """Handles PRAW rate limit exceptions"""
        if isinstance(exception, PrawcoreException):
            self.logger.warning(f"Rate limit potentially hit: {exception}. Sleeping...")
            # Extract sleep time if available (PRAW might provide this)
            sleep_time = 10 # Default sleep
            if hasattr(exception, 'response') and 'x-ratelimit-reset' in exception.response.headers:
                 reset_time = int(exception.response.headers['x-ratelimit-reset'])
                 current_time = int(time.time())
                 sleep_time = max(1, reset_time - current_time) + 5 # Add buffer
            elif "seconds" in str(exception):
                match = re.search(r'(\d+)\s+seconds', str(exception))
                if match:
                    sleep_time = int(match.group(1)) + 5 # Add buffer
            
            self.logger.warning(f"Sleeping for {sleep_time} seconds due to rate limit.")
            time.sleep(sleep_time)
            return True # Indicate handled
        return False # Not handled
    
    def collect_posts(self, subreddit_name, mode='hot', limit=100, time_filter='month', search_query=None):
        """
        Collect posts from a specific subreddit using various modes.
        
        Parameters:
        - subreddit_name: Name of the subreddit (e.g., 'investing')
        - mode: Collection mode ('hot', 'new', 'top', 'controversial', 'search')
        - limit: Maximum number of posts to attempt to fetch (API limits apply)
        - time_filter: Time filter for 'top' and 'controversial' modes ('day', 'week', 'month', 'year', 'all')
        - search_query: Query string if mode is 'search'
        
        Returns:
        - List of post dictionaries, or None if subreddit access fails.
        """
        self.logger.info(f"Attempting to collect posts from r/{subreddit_name} (mode={mode}, limit={limit}, time_filter={time_filter})")
        posts = []
        retries = 3
        current_retry = 0
        
        while current_retry < retries:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                # Check if subreddit exists and is accessible
                subreddit.load() # Forces a request to check existence/access
                
                submissions_gen = None
                if mode == 'search' and search_query:
                    self.logger.info(f"Searching r/{subreddit_name} for query: '{search_query}'")
                    submissions_gen = subreddit.search(search_query, sort='new', time_filter=time_filter, limit=limit)
                elif mode == 'top':
                    submissions_gen = subreddit.top(time_filter=time_filter, limit=limit)
                elif mode == 'hot':
                    submissions_gen = subreddit.hot(limit=limit)
                elif mode == 'new':
                    submissions_gen = subreddit.new(limit=limit)
                elif mode == 'controversial':
                    submissions_gen = subreddit.controversial(time_filter=time_filter, limit=limit)
                else:
                    self.logger.error(f"Invalid mode: {mode}")
                    return None
                
                # Process submissions
                for submission in submissions_gen:
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
                            'is_self': submission.is_self,
                            'subreddit': subreddit_name
                        }
                        
                        # Add selftext if it's a text post
                        if submission.is_self:
                            post_data['selftext'] = submission.selftext
                        
                        # Get author if available
                        try:
                            post_data['author'] = submission.author.name if submission.author else '[deleted]'
                        except:
                            post_data['author'] = '[error]'
                        
                        # Get flair if available
                        post_data['link_flair_text'] = submission.link_flair_text
                        
                        posts.append(post_data)
                        
                        # Add a small delay between requests to avoid hitting rate limits
                        time.sleep(0.25)
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing submission {submission.id}: {str(e)}")
                        continue
                
                # If we got here, we succeeded
                break
                
            except Exception as e:
                # Check if it's a rate limit issue
                if self._handle_rate_limit(e):
                    current_retry += 1
                    continue
                
                self.logger.error(f"Error collecting posts from r/{subreddit_name}: {str(e)}")
                current_retry += 1
                time.sleep(2)  # Brief pause before retry
        
        self.logger.info(f"Collected {len(posts)} posts from r/{subreddit_name}")
        return posts
    
    def collect_comments(self, submission_id, limit=None):
        """
        Collect comments from a specific submission
        
        Parameters:
        - submission_id: Reddit submission ID
        - limit: Maximum number of comments to collect, or None for all
        
        Returns:
        - List of comment dictionaries
        """
        self.logger.info(f"Collecting comments for submission {submission_id}")
        comments = []
        
        try:
            submission = self.reddit.submission(id=submission_id)
            
            # Replace MoreComments objects with actual comments
            # This will make additional API requests
            if limit is None:
                submission.comments.replace_more(limit=None)  # Get all comments
            else:
                submission.comments.replace_more(limit=min(10, limit // 10))  # Get a reasonable number of MoreComments objects
            
            # Process comments
            for comment in submission.comments.list():
                try:
                    # Extract comment data
                    comment_data = {
                        'id': comment.id,
                        'submission_id': submission_id,
                        'body': comment.body,
                        'score': comment.score,
                        'created_utc': datetime.datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                        'permalink': comment.permalink,
                        'parent_id': comment.parent_id
                    }
                    
                    # Get author if available
                    try:
                        comment_data['author'] = comment.author.name if comment.author else '[deleted]'
                    except:
                        comment_data['author'] = '[error]'
                    
                    comments.append(comment_data)
                    
                    # Apply limit if specified
                    if limit is not None and len(comments) >= limit:
                        break
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.1)
                
                except Exception as e:
                    self.logger.warning(f"Error processing comment {comment.id}: {str(e)}")
            
            self.logger.info(f"Collected {len(comments)} comments for submission {submission_id}")
        
        except Exception as e:
            self.logger.error(f"Error collecting comments for submission {submission_id}: {str(e)}")
        
        return comments
    
    def save_posts_to_csv(self, posts, subreddit_name, mode, timestamp=None):
        """
        Save collected posts to a CSV file
        
        Parameters:
        - posts: List of post dictionaries
        - subreddit_name: Name of the subreddit
        - mode: Collection mode ('hot', 'top', etc.)
        - timestamp: Optional timestamp for the filename
        
        Returns:
        - Path to the saved CSV file
        """
        if not posts:
            self.logger.warning(f"No posts to save for r/{subreddit_name}")
            return None
        
        # Create subdirectory for the subreddit
        subreddit_dir = os.path.join(self.output_dir, subreddit_name)
        if not os.path.exists(subreddit_dir):
            os.makedirs(subreddit_dir)
        
        # Generate filename with timestamp
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        file_path = os.path.join(subreddit_dir, f"{subreddit_name}_{mode}_{timestamp}.csv")
        
        # Get all possible fields from the posts
        fieldnames = set()
        for post in posts:
            fieldnames.update(post.keys())
        
        # Write to CSV
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
            writer.writeheader()
            for post in posts:
                writer.writerow(post)
        
        self.logger.info(f"Saved {len(posts)} posts to {file_path}")
        return file_path
    
    def save_comments_to_csv(self, comments, submission_id, timestamp=None):
        """
        Save collected comments to a CSV file
        
        Parameters:
        - comments: List of comment dictionaries
        - submission_id: Reddit submission ID
        - timestamp: Optional timestamp for the filename
        
        Returns:
        - Path to the saved CSV file
        """
        if not comments:
            self.logger.warning(f"No comments to save for submission {submission_id}")
            return None
        
        # Create subdirectory for comments
        comments_dir = os.path.join(self.output_dir, 'comments')
        if not os.path.exists(comments_dir):
            os.makedirs(comments_dir)
        
        # Generate filename with timestamp
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        file_path = os.path.join(comments_dir, f"comments_{submission_id}_{timestamp}.csv")
        
        # Get all possible fields from the comments
        fieldnames = set()
        for comment in comments:
            fieldnames.update(comment.keys())
        
        # Write to CSV
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
            writer.writeheader()
            for comment in comments:
                writer.writerow(comment)
        
        self.logger.info(f"Saved {len(comments)} comments to {file_path}")
        return file_path
    
    def collect_financial_term_mentions(self, subreddits=None, terms=None, days_back=7, limit=500):
        """
        Collect posts that mention specific financial terms
        
        Parameters:
        - subreddits: List of subreddits to search, or None for defaults
        - terms: List of financial terms to search for, or None for defaults
        - days_back: Number of days to search back
        - limit: Maximum number of posts to collect per subreddit
        
        Returns:
        - Dictionary mapping terms to lists of posts
        """
        if subreddits is None:
            subreddits = self.FINANCIAL_SUBREDDITS
        
        if terms is None:
            terms = [
                'stock', 'market', 'invest', 'portfolio', 'dividend',
                'ETF', 'bond', 'IPO', 'earnings', 'inflation',
                'recession', 'bull market', 'bear market', 'fed rate',
                'NASDAQ', 'NYSE', 'S&P 500', 'Dow Jones'
            ]
        
        self.logger.info(f"Collecting mentions of {len(terms)} financial terms from {len(subreddits)} subreddits")
        
        results = {term: [] for term in terms}
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for subreddit_name in subreddits:
            for term in terms:
                try:
                    self.logger.info(f"Searching for '{term}' in r/{subreddit_name}")
                    
                    # Search for the term
                    posts = self.collect_posts(
                        subreddit_name=subreddit_name,
                        mode='search',
                        search_query=term,
                        time_filter='week',  # Reddit's search time filters are limited
                        limit=limit
                    )
                    
                    if posts:
                        # Filter posts by date if needed (since Reddit's time filters are limited)
                        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
                        recent_posts = [
                            post for post in posts
                            if datetime.datetime.strptime(post['created_utc'], '%Y-%m-%d %H:%M:%S') >= cutoff_date
                        ]
                        
                        results[term].extend(recent_posts)
                        
                        # Save to CSV
                        self.save_posts_to_csv(
                            posts=recent_posts,
                            subreddit_name=subreddit_name,
                            mode=f"search_{term.replace(' ', '_')}",
                            timestamp=timestamp
                        )
                    
                    # Pause between searches to avoid rate limiting
                    time.sleep(2)
                
                except Exception as e:
                    self.logger.error(f"Error searching for '{term}' in r/{subreddit_name}: {str(e)}")
        
        return results
    
    def collect_ticker_mentions(self, subreddits=None, tickers=None, days_back=7, limit=100):
        """
        Collect posts that mention specific stock tickers
        
        Parameters:
        - subreddits: List of subreddits to search, or None for defaults
        - tickers: List of stock tickers to search for, or None for defaults
        - days_back: Number of days to search back
        - limit: Maximum number of posts to collect per subreddit and ticker
        
        Returns:
        - Dictionary mapping tickers to lists of posts
        """
        if subreddits is None:
            subreddits = [
                'investing', 'stocks', 'wallstreetbets', 'StockMarket',
                'options', 'SecurityAnalysis'
            ]
        
        if tickers is None:
            tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
                'TSLA', 'NVDA', 'JPM', 'V', 'JNJ',
                'WMT', 'PG', 'MA', 'UNH', 'HD',
                'BAC', 'XOM', 'PFE', 'ADBE', 'CRM'
            ]
        
        self.logger.info(f"Collecting mentions of {len(tickers)} stock tickers from {len(subreddits)} subreddits")
        
        results = {ticker: [] for ticker in tickers}
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for subreddit_name in subreddits:
            for ticker in tickers:
                try:
                    self.logger.info(f"Searching for '{ticker}' in r/{subreddit_name}")
                    
                    # Search for exact ticker matches using quotes
                    posts = self.collect_posts(
                        subreddit_name=subreddit_name,
                        mode='search',
                        search_query=f'"{ticker}"',  # Use quotes for exact match
                        time_filter='week',
                        limit=limit
                    )
                    
                    if posts:
                        # Filter posts by date if needed
                        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
                        recent_posts = [
                            post for post in posts
                            if datetime.datetime.strptime(post['created_utc'], '%Y-%m-%d %H:%M:%S') >= cutoff_date
                        ]
                        
                        results[ticker].extend(recent_posts)
                        
                        # Save to CSV
                        self.save_posts_to_csv(
                            posts=recent_posts,
                            subreddit_name=subreddit_name,
                            mode=f"ticker_{ticker}",
                            timestamp=timestamp
                        )
                    
                    # Pause between searches to avoid rate limiting
                    time.sleep(2)
                
                except Exception as e:
                    self.logger.error(f"Error searching for '{ticker}' in r/{subreddit_name}: {str(e)}")
        
        return results

# Example usage:
if __name__ == "__main__":
    # Example configuration
    client_id = "YOUR_CLIENT_ID"  # From Reddit Developer Application
    client_secret = "YOUR_CLIENT_SECRET"  # From Reddit Developer Application
    user_agent = "script:financial-data-collector:v1.0 (by /u/YourUsername)"
    output_dir = "reddit_financial_data"
    
    collector = RedditFinancialDataCollector(client_id, client_secret, user_agent, output_dir)
    
    # Collect recent posts from a financial subreddit
    posts = collector.collect_posts(subreddit_name="investing", mode="hot", limit=25)
    
    if posts:
        # Save posts to CSV
        csv_path = collector.save_posts_to_csv(posts, "investing", "hot")
        print(f"Saved posts to {csv_path}")
        
        # Collect comments from the most upvoted post
        most_upvoted = max(posts, key=lambda post: post['score'])
        comments = collector.collect_comments(most_upvoted['id'], limit=100)
        
        if comments:
            # Save comments to CSV
            comments_csv_path = collector.save_comments_to_csv(comments, most_upvoted['id'])
            print(f"Saved comments to {comments_csv_path}")
    
    # Collect ticker mentions
    ticker_results = collector.collect_ticker_mentions(
        subreddits=["wallstreetbets", "stocks"],
        tickers=["AAPL", "TSLA", "NVDA"],
        days_back=3,
        limit=50
    )
    
    for ticker, mentions in ticker_results.items():
        print(f"Found {len(mentions)} mentions of {ticker}")
```

#### Limitations and Considerations:
- The official Reddit API has strict rate limits (600 requests per 10 minutes)
- Historical data is limited compared to what Pushshift previously offered
- Search functionality is limited and may not catch all relevant posts
- Reddit credentials are required to access the API (create a Reddit Developer Application)
- API terms of service restrict certain types of data collection and usage