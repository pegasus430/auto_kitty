import csv
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET

# Define the directory to save downloaded images
image_directory = 'content/images'
header_image_directory = 'content/header_images'
content_image_directory = 'content/content_images'

# Create the image directories if they don't exist
os.makedirs(image_directory, exist_ok=True)
os.makedirs(header_image_directory, exist_ok=True)
os.makedirs(content_image_directory, exist_ok=True)

# Define the CSV file containing news article data
csv_file = 'news.csv'

# Initialize a list to store extracted data
extracted_data = []

# Function to extract images from CSS style
def extract_images_from_style(style):
    images = re.findall(r'url\((.*?)\)', style)
    return images

# Function to extract the image name from the URL and clean it up
def extract_image_name(image_url):
    # Extract the last part of the URL and remove query parameters
    image_name = os.path.basename(image_url).split('?')[0]
    # Remove any special characters or spaces from the image name
    clean_image_name = re.sub(r'[^a-zA-Z0-9.-]', '_', image_name)
    return clean_image_name

# Read URLs from the CSV file and validate them
try:
    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        total_urls = sum(1 for row in csv_reader)  # Count the total number of URLs
        file.seek(0)  # Reset the file position to the beginning
        next(csv_reader)  # Skip the header row

        for index, row in enumerate(csv_reader, start=1):
            url = row.get('URL')

            if url and index > 60:
                try:
                    # Validate the URL by sending a HEAD request
                    response = requests.head(url, timeout=10)
                    if response.status_code != 200:
                        print(f"Skipping invalid URL ({index}/{total_urls}): {url}")
                        continue

                    # Send a GET request to fetch the web page content
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()

                    # Parse the HTML content using BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extract data from the HTML structure
                    byline_element = soup.find('h4', class_='byline')
                    title = soup.find('h1').text.strip()
                    standfirst = soup.find('p', class_='standfirst').text.strip()

                    # Split the byline by '|' and extract Author and Date
                    byline_parts = byline_element.text.strip().split('|')
                    if len(byline_parts) == 2:
                        author, date = byline_parts[0].strip(), byline_parts[1].strip()
                    else:
                        author, date = byline_element.text.strip(), ''

                    # Find the header image in @media query with max-width: 2000px
                    header_images = []

                    # Check for @media queries
                    media_queries = soup.find_all('style')
                    for media_query in media_queries:
                        if '@media only screen and (max-width: 2000px)' in media_query.text:
                            media_query_images = extract_images_from_style(media_query.text)
                            if media_query_images:
                                header_images.append(media_query_images[0])  # Only add the first image
                                break  # Stop processing images after the first one is found

                    # Download the header images to the header image directory
                    header_image_names = []
                    for i, image_url in enumerate(header_images):
                        image_name = extract_image_name(image_url)
                        header_image_names.append(image_name)
                        
                        # Download the image
                        image_url = image_url.split('?')[0]
                        image_response = requests.get(image_url, timeout=20)
                        if image_response.status_code == 200:
                            with open(os.path.join(header_image_directory, image_name), 'wb') as image_file:
                                image_file.write(image_response.content)
                        else:
                            header_image_names.pop()  # Remove the image name if download fails

                    # Extract all .media elements while maintaining their HTML structure
                    media_sections = soup.select('.media')

                    # Extract image URLs and captions from .media elements
                    media_data = []
                    for media_section in media_sections:
                        img = media_section.find('img')
                        caption = media_section.find('p', class_='caption')
                        if img:
                            img_url = img.get('data-src') or img.get('src')
                            img_name = extract_image_name(img_url)
                            img_caption = caption.text.strip() if caption else ''
                            media_data.append({'Image URL': img_url, 'Image Name': img_name, 'Image Caption': img_caption})

                            # Download the image to the content image directory
                            img_response = requests.get(img_url, timeout=10)
                            if img_response.status_code == 200:
                                img_path = os.path.join(content_image_directory, img_name)
                                with open(img_path, 'wb') as img_file:
                                    img_file.write(img_response.content)

                    # Extract all .textSection elements while maintaining their HTML structure
                    text_sections = soup.select('.textSection')

                    # Extract HTML content from .textSection elements
                    text_section_data = []
                    for text_section in text_sections:
                        text_section_html = str(text_section)
                        text_section_data.append(text_section_html)

                    # Find and extract YouTube iframes
                    youtube_iframes = []
                    iframes = soup.find_all('iframe')
                    for iframe in iframes:

                        # Check if the iframe is a YouTube embed
                        if 'youtube.com' in iframe['src']:
                            youtube_iframes.append(str(iframe))

                    # Append the extracted data to the list
                    extracted_data.append({
                        'URL': url,
                        'Author': author,
                        'Date': date,
                        'Title': title,
                        'Standfirst': standfirst,
                        'Header Image': ', '.join(header_image_names),
                        'Content Images': ', '.join([media['Image Name'] for media in media_data]),
                        'Content Captions': ', '.join([media['Image Caption'] for media in media_data]),
                        'Text Sections': '\n\n'.join(text_section_data),
                        'YouTube Iframes': '\n\n'.join(youtube_iframes),
                    })

                    print(f"Scraped ({index}/{total_urls}): {url}")

                    

                except Exception as e:
                    print(f"Error analyzing {url} ({index}/{total_urls}): {e}")

except FileNotFoundError:
    print(f"CSV file '{csv_file}' not found.")

# Create the XML file for WordPress import
# namespaces = {
#     'xmlns:excerpt': "http://wordpress.org/export/1.2/excerpt/",
#     'xmlns:content': "http://purl.org/rss/1.0/modules/content/",
#     'xmlns:wfw': "http://wellformedweb.org/CommentAPI/",
#     'xmlns:dc': "http://purl.org/dc/elements/1.1/",
#     'xmlns:wp': "http://wordpress.org/export/1.2/",
# }

# rss = ET.Element("rss", version="2.0", **namespaces)
# channel = ET.SubElement(rss, "channel")

# # Add the wp:wxr_version element
# ET.SubElement(channel, "wp:wxr_version").text = "1.2"

# for item in extracted_data:
#     post = ET.SubElement(channel, "item")
#     ET.SubElement(post, "title").text = item['Title']
#     ET.SubElement(post, "link").text = item['URL']
#     ET.SubElement(post, "wp:post_name").text = item['URL'].split('/')[-1]
#     ET.SubElement(post, "wp:post_type").text = "news"
#     ET.SubElement(post, "wp:status").text = "publish"
#     ET.SubElement(post, "dc:creator").text = "craig-dodd"
    
#     # Format the date to RFC 2822 format
#     try:
#         original_date = item['Date']
#         formatted_date = datetime.strptime(original_date, '%d %B %Y').strftime('%a, %d %b %Y %H:%M:%S +0000')
#         ET.SubElement(post, "pubDate").text = formatted_date
#     except ValueError:
#         ET.SubElement(post, "pubDate").text = ""
    
#     # Add the Gutenberg block as a custom field
#     custom_fields = ET.SubElement(post, "wp:postmeta")
#     ET.SubElement(custom_fields, "wp:meta_key").text = "_block_editor_content"
#     ET.SubElement(custom_fields, "wp:meta_value").text = f'<!-- wp:wak/news-article-hero {{"name":"wak/news-article-hero","data":{{"field_650026fcbd7ef":"all","field_652e84ea40356":"{item["Title"]}","field_652e84ea403a6":"{item["Standfirst"]}","field_652e84ea404e7":"0","field_652e84ea40596":"","field_652e84ea40619":""}},"mode":"edit"}} /-->'

#     ET.SubElement(post, "content:encoded").text = item['Text Sections']

# # Create a CSV file for WordPress import
# wordpress_csv_file = 'wordpress_import.csv'
# with open(wordpress_csv_file, 'w', newline='', encoding='utf-8') as wordpress_output_file:
#     fieldnames = ['Title', 'Slug', 'Post Type', 'Status', 'Author', 'Date', 'Content']
#     writer = csv.DictWriter(wordpress_output_file, fieldnames=fieldnames)
#     writer.writeheader()
#     for item in extracted_data:
#         writer.writerow({
#             'Title': item['Title'],
#             'Slug': item['URL'].split('/')[-1],
#             'Post Type': 'news',
#             'Status': 'publish',
#             'Author': 'craig-dodd',
#             'Date': item['Date'],  # Keep the original date format
#             'Content': item['Text Sections'],
#         })

# print(f"CSV file '{wordpress_csv_file}' for WordPress import saved.")

# # Save the XML file for WordPress import
# xml_file = 'wordpress_import.xml'
# tree = ET.ElementTree(rss)
# tree.write(xml_file, encoding='utf-8', xml_declaration=True)

# print(f"XML file '{xml_file}' for WordPress import saved.")
