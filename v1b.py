import os
import requests
import csv
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse, quote, urljoin

# Create a folder for storing downloaded images
base_image_folder = 'images'
os.makedirs(base_image_folder, exist_ok=True)

# Open the CSV file for reading URLs and writing data
with open('test.csv', 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    
    # Create a CSV file for output
    with open('output.csv', 'w', newline='') as output_csv:
        fieldnames = ['URL', 'Image', 'Question', 'Answer Options', 'Correct Answer', 'Date', 'Title', 'Quiz Intro Text', 'Featured Image']
        csv_writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        for row in reader:
            url = row['URL']
            # Get the slug name from the URL
            url_parts = urlparse(url)
            slug = quote(url_parts.path.strip('/')).replace('/', '_')
            image_folder = os.path.join(base_image_folder, slug)
            os.makedirs(image_folder, exist_ok=True)
            
            # Send an HTTP GET request to the URL
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the triviaQuizQuestionBlock
                trivia_block = soup.find('div', class_='triviaQuizQuestionBlock')
                
                if trivia_block:
                    # Find all quizItems within the triviaQuizQuestionBlock
                    quiz_items = trivia_block.find_all('div', class_='quizItem')
                    
                    for quiz_item in quiz_items:
                        # Initialize dictionaries to store data for each row
                        data_row = {
                            'URL': url,
                            'Image': '',
                            'Question': '',
                            'Answer Options': '',  # Updated column name
                            'Correct Answer': '',
                            'Date': '',  # New column for date
                            'Title': '',  # New column for title
                            'Quiz Intro Text': '',  # New column for intro text
                            'Featured Image': ''  # New column for featured image
                        }
                        
                        # Download images
                        image = quiz_item.find('img')
                        if image and 'src' in image.attrs:
                            image_url = image['src']
                            image_filename = os.path.basename(urlparse(image_url).path)
                            image_path = os.path.join(image_folder, image_filename)
                            data_row['Image'] = image_path
                            image['src'] = image_path  # Update the src attribute
                            
                            # Download image
                            response = requests.get(image_url)
                            if response.status_code == 200:
                                with open(image_path, 'wb') as img_file:
                                    img_file.write(response.content)
                        
                        # Get question text
                        question = quiz_item.find('div', class_='questionTextBlock')
                        if question:
                            question_text = question.find('h3').text
                            data_row['Question'] = question_text
                        
                        # Get answers and highlight correct answer
                        answer_blocks = quiz_item.find_all('div', class_='answerBlock')
                        answers = []
                        correct_answer = ''
                        for answer_block in answer_blocks:
                            answer_text = answer_block.find('p').text
                            answers.append(answer_text)
                            if 'data-correct' in answer_block.attrs and answer_block['data-correct'] == 'true':
                                correct_answer = answer_text
                        
                        # Concatenate answers if multiple
                        data_row['Answer Options'] = ', '.join(answers)  # Updated column name
                        data_row['Correct Answer'] = correct_answer
                        
                        # Get additional information
                        byline = soup.find('h4', class_='byline')
                        if byline:
                            data_row['Date'] = byline.text
                        
                        title = soup.find('h1')
                        if title:
                            data_row['Title'] = title.text
                        
                        intro_text = soup.find('div', class_='textSection')
                        if intro_text:
                            intro_paragraphs = intro_text.find_all('p')
                            intro_text_list = []
                            for paragraph in intro_paragraphs:
                                if not paragraph.find('em'):
                                    intro_text_list.append(paragraph.text)
                            data_row['Quiz Intro Text'] = ' '.join(intro_text_list)
                        
                        # Get featured image
                        featured_image = soup.find('picture', class_='w-100')
                        if featured_image:
                            featured_image_source = featured_image.find('img')
                            if featured_image_source and 'src' in featured_image_source.attrs:
                                featured_image_url = featured_image_source['src']
                                
                                # Combine the base URL with the featured_image_url
                                complete_featured_image_url = urljoin(url, featured_image_url)
                                
                                featured_image_filename = os.path.basename(urlparse(complete_featured_image_url).path)
                                featured_image_path = os.path.join(image_folder, featured_image_filename)
                                data_row['Featured Image'] = featured_image_path
                                featured_image_source['src'] = featured_image_path
                                
                                # Download featured image
                                response = requests.get(complete_featured_image_url)
                                if response.status_code == 200:
                                    with open(featured_image_path, 'wb') as img_file:
                                        img_file.write(response.content)

                        # Write data_row to the output CSV
                        csv_writer.writerow(data_row)
                    
                    print(f"Data for URL '{url}' has been scraped and saved.")
            else:
                print(f"Failed to fetch URL '{url}' (status code: {response.status_code})")
