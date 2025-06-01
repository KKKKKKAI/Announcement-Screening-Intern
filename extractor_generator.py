"""
Extractor Generator
========================
Example script showing how to generate extractors for multiple companies.
"""

from extractor_generator import ExtractorGenerator
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('batch_generator')

def generate_extractors_for_companies(companies, model="llama3.2", test=True):
    """
    Generate extractors for multiple companies.
    
    Args:
        companies (list): List of dicts with 'name' and 'url' keys
        model (str): Ollama model to use
        test (bool): Whether to test generated extractors
    """
    generator = ExtractorGenerator(model=model)
    results = []
    
    for company in companies:
        logger.info(f"\nProcessing {company['name']}...")
        
        # Generate extractor
        success, code_or_error = generator.generate_extractor_code(company['url'])
        
        if success:
            # Save the extractor
            filepath = generator.save_extractor(code_or_error, company['url'])
            
            result = {
                'company': company['name'],
                'url': company['url'],
                'extractor_path': filepath,
                'status': 'generated'
            }
            
            # Test if requested
            if test:
                test_success, test_results = generator.test_extractor(filepath, company['url'])
                if test_success:
                    result['status'] = 'tested'
                    result['press_releases_found'] = len(test_results)
                    result['sample_titles'] = [r['title'] for r in test_results[:3]]
                else:
                    result['status'] = 'test_failed'
                    result['error'] = test_results
            
            results.append(result)
        else:
            results.append({
                'company': company['name'],
                'url': company['url'],
                'status': 'failed',
                'error': code_or_error
            })
    
    return results


def main():
    # Example company list
    companies = [
        {
            "name": "Thames Water",
            "url": "https://www.thameswater.co.uk/news/thames-water-seeks-tunnelling-contractors"
        },
        {
            "name": "Example Corp",
            "url": "https://example.com/press-releases"
        },
        # Add more companies here
    ]
    
    # Generate extractors
    results = generate_extractors_for_companies(companies)
    
    # Save results report
    with open('extractor_generation_report.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\nExtractor Generation Summary")
    print("=" * 50)
    
    for result in results:
        print(f"\n{result['company']}:")
        print(f"  Status: {result['status']}")
        
        if result['status'] == 'tested':
            print(f"  Press releases found: {result['press_releases_found']}")
            print(f"  Extractor saved to: {result['extractor_path']}")
            if result.get('sample_titles'):
                print("  Sample titles:")
                for title in result['sample_titles']:
                    print(f"    - {title[:60]}...")
        elif result['status'] == 'failed':
            print(f"  Error: {result['error']}")
    
    # Generate config for press_release_monitor.py
    monitor_config = []
    for result in results:
        if result['status'] in ['generated', 'tested']:
            monitor_config.append({
                "name": result['company'],
                "url": result['url'],
                "extractor": result['extractor_path']
            })
    
    with open('monitor_config.json', 'w') as f:
        json.dump(monitor_config, f, indent=2)
    
    print(f"\n✓ Monitor configuration saved to monitor_config.json")
    print(f"  Use with: python press_release_monitor.py --config monitor_config.json")


if __name__ == "__main__":
    main()