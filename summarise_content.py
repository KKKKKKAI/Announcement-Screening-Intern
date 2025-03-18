import ollama
import os
import glob
from pathlib import Path

def summarize_articles(input_directory, output_directory, model_name="llama3.2"):
    """
    Summarize text articles from files in input_directory and save summaries to output_directory
    
    Args:
        input_directory: Directory containing articles to summarize
        output_directory: Directory where summaries will be saved
        model_name: Ollama model to use for summarization
    """
    # Initialize Ollama client
    client = ollama.Client()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    
    # Get all text files in the input directory
    article_files = glob.glob(os.path.join(input_directory, "*.txt"))
    
    print(f"Found {len(article_files)} articles to summarize.")
    
    # Process each article
    for article_path in article_files:
        article_filename = os.path.basename(article_path)
        summary_filename = f"summary_{article_filename}"
        summary_path = os.path.join(output_directory, summary_filename)
        
        print(f"Processing: {article_filename}")
        
        try:
            # Read the article content
            with open(article_path, 'r', encoding='utf-8') as file:
                article_content = file.read()
            
            # Create prompt for summarization
            prompt = f"Please summarize the following article concisely:\n\n{article_content}"
            
            # Generate summary using Ollama
            response = client.generate(model=model_name, prompt=prompt)
            summary = response.response
            
            # Save the summary to output directory
            with open(summary_path, 'w', encoding='utf-8') as file:
                file.write(summary)
            
            print(f"Summary saved to: {summary_path}")
            
        except Exception as e:
            print(f"Error processing {article_filename}: {str(e)}")
    
    print("Summarization complete!")

if __name__ == "__main__":
    # Configuration
    input_dir = "downloaded_pages"
    output_dir = "summaries"
    model = "llama3.2"  # Change this to your preferred model
    
    # Run the summarization
    summarize_articles(input_dir, output_dir, model)