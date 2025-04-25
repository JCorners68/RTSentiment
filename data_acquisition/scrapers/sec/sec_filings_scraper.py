"""
SEC filings scraper for the data acquisition pipeline.
"""
import logging
import asyncio
import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from data_acquisition.scrapers.base import BaseScraper
from data_acquisition.utils.weight_calculator import calculate_weight

logger = logging.getLogger(__name__)

class SECFilingsScraper(BaseScraper):
    """Scraper for SEC filings."""
    
    def __init__(self, producer, config):
        """
        Initialize the SEC filings scraper with event producer and configuration.
        
        Args:
            producer: Event producer for publishing events
            config: Configuration dictionary
        """
        super().__init__(producer, config)
        
        # Extract SEC filings specific configuration
        sec_config = config.get("sec_filings_scraper", {})
        self.sec_url = sec_config.get("sec_url", "https://www.sec.gov/")
        self.filing_types = sec_config.get("filing_types", ["10-K", "10-Q", "8-K"])
        self.companies = sec_config.get("companies", [])
        self.lookup_by_cik = sec_config.get("lookup_by_cik", True)
        self.max_filings_per_company = sec_config.get("max_filings_per_company", 5)
        self.interval = sec_config.get("polling_interval", 3600)  # Default 1 hour
        
        # Setup headers for SEC API requests (SEC requires a proper User-Agent)
        self.headers = {
            "User-Agent": "FinancialSentimentTracker/1.0 (support@example.com)"
        }
        
        # Setup cache for filing URLs to avoid duplicates
        self.cache_dir = os.path.join(os.getcwd(), "data", "cache", "deduplication")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "sec_filing_hashes.json")
        self.filing_cache = self._load_filing_cache()
        
        logger.info(f"Initialized {self.name} with {len(self.filing_types)} filing types and {len(self.companies)} companies")
    
    def _load_filing_cache(self) -> Dict[str, str]:
        """
        Load filing cache from file to avoid duplicates.
        
        Returns:
            Dictionary of filing URLs and their timestamp
        """
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading filing cache: {e}")
            return {}
    
    def _save_filing_cache(self):
        """Save filing cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.filing_cache, f)
        except Exception as e:
            logger.error(f"Error saving filing cache: {e}")
    
    async def _get_company_filings(self, session, ticker, cik=None) -> List[Dict[str, Any]]:
        """
        Get SEC filings for a specific company.
        
        Args:
            session: aiohttp client session
            ticker: Company ticker symbol
            cik: Company CIK number (optional)
            
        Returns:
            List of filing data dictionaries
        """
        filings = []
        
        try:
            # If no CIK provided, try to get it from ticker
            if not cik and self.lookup_by_cik:
                cik = await self._get_cik_from_ticker(session, ticker)
                
                if not cik:
                    logger.error(f"Could not find CIK for ticker {ticker}")
                    return filings
            
            # EDGAR API endpoint for company filings
            if cik:
                # CIK must be 10 digits with leading zeros
                cik_padded = cik.zfill(10) if isinstance(cik, str) else f"{cik:010d}"
                filings_url = f"{self.sec_url}Archives/edgar/data/{cik}/index.json"
            else:
                # Fallback to company search by ticker
                filings_url = f"{self.sec_url}cgi-bin/browse-edgar?CIK={ticker}&owner=exclude&action=getcompany&output=atom"
            
            async with session.get(filings_url, headers=self.headers) as response:
                if response.status == 200:
                    if cik:
                        # Parse JSON response for CIK-based query
                        data = await response.json()
                        filing_entries = data.get("directory", {}).get("item", [])
                        
                        for entry in filing_entries[:self.max_filings_per_company]:
                            filing_name = entry.get("name", "")
                            filing_url = f"{self.sec_url}Archives/edgar/data/{cik}/{filing_name}"
                            
                            # Skip if we've already processed this filing
                            if filing_url in self.filing_cache:
                                continue
                            
                            # Get filing details
                            filing_data = await self._get_filing_details(session, filing_url, ticker)
                            if filing_data:
                                filings.append(filing_data)
                                self.filing_cache[filing_url] = datetime.now(timezone.utc).isoformat()
                    else:
                        # Parse XML response for ticker-based query
                        xml_text = await response.text()
                        soup = BeautifulSoup(xml_text, "lxml-xml")
                        
                        # Find filing entries
                        entries = soup.find_all("entry")
                        
                        for entry in entries[:self.max_filings_per_company]:
                            # Get filing category
                            category = entry.find("category")
                            if not category:
                                continue
                                
                            filing_type = category.get("term", "")
                            
                            # Check if this is a filing type we're interested in
                            if not any(ft in filing_type for ft in self.filing_types):
                                continue
                            
                            # Get filing link
                            link = entry.find("link")
                            if not link:
                                continue
                                
                            filing_url = link.get("href", "")
                            
                            # Skip if we've already processed this filing
                            if filing_url in self.filing_cache:
                                continue
                            
                            # Get filing details
                            filing_data = await self._get_filing_details(session, filing_url, ticker)
                            if filing_data:
                                filings.append(filing_data)
                                self.filing_cache[filing_url] = datetime.now(timezone.utc).isoformat()
                else:
                    logger.error(f"SEC API error for company {ticker}: {response.status}")
        except Exception as e:
            logger.error(f"Error getting SEC filings for company {ticker}: {e}")
        
        return filings
    
    async def _get_cik_from_ticker(self, session, ticker) -> Optional[str]:
        """
        Get CIK number for a ticker symbol.
        
        Args:
            session: aiohttp client session
            ticker: Company ticker symbol
            
        Returns:
            CIK number as string, or None if not found
        """
        try:
            # SEC provides a ticker to CIK lookup file
            lookup_url = "https://www.sec.gov/include/ticker.txt"
            
            async with session.get(lookup_url, headers=self.headers) as response:
                if response.status == 200:
                    lookup_text = await response.text()
                    
                    # Search for ticker in the lookup file
                    for line in lookup_text.splitlines():
                        parts = line.strip().split('\t')
                        if len(parts) == 2 and parts[0].lower() == ticker.lower():
                            return parts[1]
                            
                    # If not found, try the full company lookup
                    lookup_url = f"{self.sec_url}cgi-bin/browse-edgar?CIK={ticker}&owner=exclude&action=getcompany&output=atom"
                    
                    async with session.get(lookup_url, headers=self.headers) as lookup_response:
                        if lookup_response.status == 200:
                            xml_text = await lookup_response.text()
                            soup = BeautifulSoup(xml_text, "lxml-xml")
                            
                            # Look for CIK in the XML
                            company_info = soup.find("company-info")
                            if company_info:
                                cik_tag = company_info.find("cik")
                                if cik_tag:
                                    return cik_tag.text
                    
                    logger.warning(f"CIK not found for ticker {ticker}")
                    return None
                else:
                    logger.error(f"SEC API error for ticker lookup: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting CIK for ticker {ticker}: {e}")
            return None
    
    async def _get_filing_details(self, session, filing_url, ticker) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific SEC filing.
        
        Args:
            session: aiohttp client session
            filing_url: URL to the filing
            ticker: Company ticker symbol
            
        Returns:
            Filing data dictionary, or None if error
        """
        try:
            async with session.get(filing_url, headers=self.headers) as response:
                if response.status == 200:
                    html_text = await response.text()
                    soup = BeautifulSoup(html_text, "html.parser")
                    
                    # Extract filing type
                    filing_type = None
                    form_type_tag = soup.find("div", text=re.compile(r"Form Type:"))
                    if form_type_tag:
                        form_type_match = re.search(r"Form Type:\s*(\S+)", form_type_tag.text)
                        if form_type_match:
                            filing_type = form_type_match.group(1)
                    
                    # Check if this is a filing type we're interested in
                    if not filing_type or not any(ft in filing_type for ft in self.filing_types):
                        return None
                    
                    # Extract filing date
                    filing_date = None
                    filing_date_tag = soup.find("div", text=re.compile(r"Filing Date:"))
                    if filing_date_tag:
                        date_match = re.search(r"Filing Date:\s*(\d{2}/\d{2}/\d{4})", filing_date_tag.text)
                        if date_match:
                            filing_date = date_match.group(1)
                            # Convert to ISO format
                            try:
                                parsed_date = datetime.strptime(filing_date, "%m/%d/%Y")
                                filing_date = parsed_date.isoformat()
                            except ValueError:
                                filing_date = datetime.now(timezone.utc).isoformat()
                    
                    if not filing_date:
                        filing_date = datetime.now(timezone.utc).isoformat()
                    
                    # Extract company name
                    company_name = ticker
                    company_name_tag = soup.find("span", {"class": "companyName"})
                    if company_name_tag:
                        company_name_match = re.search(r"^(.*?)\s*\(", company_name_tag.text)
                        if company_name_match:
                            company_name = company_name_match.group(1).strip()
                    
                    # Extract filing content
                    content = ""
                    # Try to find the filing document
                    doc_link = None
                    doc_table = soup.find("table", {"summary": "Document Format Files"})
                    if doc_table:
                        rows = doc_table.find_all("tr")
                        for row in rows:
                            cells = row.find_all("td")
                            if len(cells) >= 3:
                                if cells[0].text.strip() == filing_type or cells[2].text.strip().endswith(".htm"):
                                    a_tag = cells[2].find("a")
                                    if a_tag and a_tag.get("href"):
                                        doc_link = a_tag.get("href")
                                        break
                    
                    # If we found a document link, fetch and extract the content
                    if doc_link:
                        if not doc_link.startswith("http"):
                            # Handle relative URLs
                            base_url = "/".join(filing_url.split("/")[:-1])
                            doc_link = f"{base_url}/{doc_link}"
                        
                        async with session.get(doc_link, headers=self.headers) as doc_response:
                            if doc_response.status == 200:
                                doc_html = await doc_response.text()
                                doc_soup = BeautifulSoup(doc_html, "html.parser")
                                
                                # Extract text content
                                for tag in doc_soup(["script", "style"]):
                                    tag.extract()
                                
                                content = doc_soup.get_text(separator=" ", strip=True)
                                
                                # Truncate very long content
                                if len(content) > 50000:
                                    content = content[:50000] + "..."
                    
                    # Extract tickers mentioned in the filing
                    tickers = self._extract_tickers(content, ticker)
                    
                    # Prepare filing data
                    filing_data = {
                        "id": filing_url.split("/")[-1],
                        "title": f"{company_name} {filing_type}",
                        "content": content,
                        "tickers": tickers,
                        "source": "SEC",
                        "source_name": f"SEC {filing_type} Filing",
                        "url": filing_url,
                        "timestamp": filing_date,
                        "filing_type": filing_type,
                        "company_name": company_name,
                        "weight": calculate_weight(
                            text=content,
                            source="SEC",
                            document_type=filing_type
                        )
                    }
                    
                    return filing_data
                else:
                    logger.error(f"SEC API error for filing URL {filing_url}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting filing details for URL {filing_url}: {e}")
            return None
    
    def _extract_tickers(self, text, primary_ticker) -> List[str]:
        """
        Extract stock tickers from filing text.
        
        Args:
            text: Filing text content
            primary_ticker: Primary company ticker
            
        Returns:
            List of stock ticker symbols
        """
        import re
        
        # Always include the primary ticker
        tickers = [primary_ticker.upper()]
        
        # Regular expression to find stock symbols (1-5 capital letters)
        # This is a simple heuristic and may need refinement
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        
        # Common words to exclude that might match the pattern
        exclude_words = {
            "A", "I", "AM", "PM", "CEO", "CFO", "COO", "CTO", "US", "USA", "USD", "NYSE", "NASDAQ",
            "SEC", "GAAP", "Q", "K", "THE", "AND", "FOR", "TO", "IN", "OF", "ON", "BY", "WITH"
        }
        
        # Find all matches
        matches = re.findall(ticker_pattern, text)
        
        # Filter and deduplicate
        for match in matches:
            if match not in exclude_words and match not in tickers:
                tickers.append(match)
        
        return tickers
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape SEC filings for financial content.
        
        Returns:
            List of filing data dictionaries
        """
        filings = []
        
        async with aiohttp.ClientSession() as session:
            # Respect SEC's fair access policy with delays between requests
            for company in self.companies:
                logger.info(f"Getting SEC filings for company: {company.get('ticker', company)}")
                
                ticker = company.get("ticker")
                cik = company.get("cik")
                
                if ticker:
                    company_filings = await self._get_company_filings(session, ticker, cik)
                    filings.extend(company_filings)
                    logger.info(f"Found {len(company_filings)} filings for company {ticker}")
                
                # Respect SEC's rate limits (10 requests per second)
                await asyncio.sleep(0.1)
        
        # Save updated filing cache
        self._save_filing_cache()
        
        logger.info(f"Scraped {len(filings)} SEC filings")
        return filings
    
    async def process_data(self, data: List[Dict[str, Any]]):
        """
        Process scraped SEC filings data, save to Parquet, and send to event producer.
        
        Args:
            data: List of dictionaries containing scraped data
        """
        await super().process_data(data)