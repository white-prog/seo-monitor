import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import logging
from concurrent.futures import ThreadPoolExecutor
import json
import schedule

# Configure logging
logging.basicConfig(
    filename='seo_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SEOMonitor:
    def __init__(self, config_file='config.json'):
        """Initialize SEO monitoring system with configuration."""
        self.load_config(config_file)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.results_df = pd.DataFrame()

    def load_config(self, config_file):
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.websites = config['websites']
                self.keywords = config['keywords']
                self.check_interval = config.get('check_interval', 3600)  # Default 1 hour
        except FileNotFoundError:
            logging.error(f"Configuration file {config_file} not found")
            raise

    def check_keyword_ranking(self, website, keyword):
        """Check keyword ranking for a specific website."""
        try:
            search_url = f"https://www.google.com/search?q={keyword}"
            response = requests.get(search_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = soup.find_all('div', class_='g')
            
            for position, result in enumerate(search_results, 1):
                if website in str(result):
                    return {
                        'website': website,
                        'keyword': keyword,
                        'position': position,
                        'timestamp': datetime.now()
                    }
            
            return {
                'website': website,
                'keyword': keyword,
                'position': None,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logging.error(f"Error checking ranking for {website} - {keyword}: {str(e)}")
            return None

    def analyze_meta_tags(self, url):
        """Analyze meta tags and SEO elements of a webpage."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                'title': soup.title.string if soup.title else None,
                'meta_description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else None,
                'h1_count': len(soup.find_all('h1')),
                'h2_count': len(soup.find_all('h2')),
                'img_alt_missing': len([img for img in soup.find_all('img') if not img.get('alt')]),
                'url': url,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logging.error(f"Error analyzing meta tags for {url}: {str(e)}")
            return None

    def check_site_performance(self, url):
        """Check basic site performance metrics."""
        try:
            start_time = time.time()
            response = requests.get(url, headers=self.headers)
            load_time = time.time() - start_time
            
            return {
                'url': url,
                'status_code': response.status_code,
                'response_time': load_time,
                'content_length': len(response.content),
                'timestamp': datetime.now()
            }

        except Exception as e:
            logging.error(f"Error checking performance for {url}: {str(e)}")
            return None

    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle for all websites and keywords."""
        logging.info("Starting monitoring cycle")
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Check keyword rankings
            for website in self.websites:
                for keyword in self.keywords:
                    future = executor.submit(self.check_keyword_ranking, website, keyword)
                    result = future.result()
                    if result:
                        results.append(result)

            # Analyze meta tags and performance
            for website in self.websites:
                meta_future = executor.submit(self.analyze_meta_tags, website)
                perf_future = executor.submit(self.check_site_performance, website)
                
                meta_result = meta_future.result()
                perf_result = perf_future.result()
                
                if meta_result:
                    results.append(meta_result)
                if perf_result:
                    results.append(perf_result)

        # Save results
        self.save_results(results)
        logging.info("Monitoring cycle completed")

    def save_results(self, results):
        """Save monitoring results to CSV and generate report."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save raw data
        df = pd.DataFrame(results)
        df.to_csv(f'seo_results_{timestamp}.csv', index=False)
        
        # Generate summary report
        with open(f'seo_report_{timestamp}.txt', 'w') as f:
            f.write("SEO Monitoring Summary Report\n")
            f.write(f"Generated at: {timestamp}\n\n")
            
            # Keyword rankings summary
            f.write("Keyword Rankings:\n")
            rankings = df[df['position'].notna()]
            for website in self.websites:
                f.write(f"\n{website}:\n")
                site_rankings = rankings[rankings['website'] == website]
                for _, row in site_rankings.iterrows():
                    f.write(f"- {row['keyword']}: Position {row['position']}\n")
            
            # Performance summary
            f.write("\nPerformance Metrics:\n")
            perf_data = df[df['response_time'].notna()]
            for _, row in perf_data.iterrows():
                f.write(f"\n{row['url']}:\n")
                f.write(f"- Response Time: {row['response_time']:.2f} seconds\n")
                f.write(f"- Status Code: {row['status_code']}\n")
            
            # Meta tags summary
            f.write("\nMeta Tags Analysis:\n")
            meta_data = df[df['h1_count'].notna()]
            for _, row in meta_data.iterrows():
                f.write(f"\n{row['url']}:\n")
                f.write(f"- Title: {row['title']}\n")
                f.write(f"- H1 Tags: {row['h1_count']}\n")
                f.write(f"- Missing Alt Tags: {row['img_alt_missing']}\n")

def main():
    """Main function to run the SEO monitoring system."""
    monitor = SEOMonitor()
    
    # Schedule regular monitoring
    schedule.every(monitor.check_interval).seconds.do(monitor.run_monitoring_cycle)
    
    # Run initial monitoring cycle
    monitor.run_monitoring_cycle()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
