import base64
import requests
import json
import os
import csv
import re
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
import mimetypes

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

# Initialize the target wordpress URL and authentication information.
wp_url = "https://wanderlusttstg.wpengine.com//wp-json/wp/v2"
wp_post_url = wp_url + "/news"
wp_theme_rul = wp_url + "/theme"
wp_media_url = wp_url + "/media"
user_id = "mihailo"
user_app_password = "bWOV MTvf MEB3 hWts DVKd zGpu"

credentials = user_id + ':' + user_app_password
token = base64.b64encode(credentials.encode())
header = {
        # 'Content-Type': 'application/json',
        'Authorization': 'Basic ' + token.decode('utf-8')
    }

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

# Function to post the article on Wordpress
def post_news(article_title, article_body, post_status="draft", featured_media_id=0, excerpt=""):
    post_data = {
        'title': article_title,
        "content": article_body,
        "comment_status": "closed",
        "categories": [1],
        "status": post_status,
        "featured_media": featured_media_id,
        "excerpt": excerpt,
    }
    try:
        response = requests.post(wp_post_url, headers=header, json=post_data)
        if response.status_code == 201:
            print(f'  - Article posted "{article_title}" successfully!')
        else:
            print(f'Error creating custom post. Status code: {response.status_code}')
    except:
        print (f"Error while posting the article! '{article_title}'")
        response = ""
    
# Function to post the file on Wordpress Media library
def post_file(file_path):
    try:        
        media = {'file': open(file_path,"rb")}
        response = requests.post(wp_media_url, headers = header, files = media)
        response = response.json()
        image_id = response.get('id')
        print(f'  - posted image file {file_path}')
    except:
        print('  - Error while uploading the image')
        response = ""
        return 0
    return image_id

# json data for space block
space_template = {
    "name":"wak/spacer", 
    "data":{ 
        "wak_block_visibility":"all",
        "mobile_space":"90",
        "tablet_space":"90",
        "desktop_space":"110",
        "theme":"0",
        },
    "mode":"edit"
}

# spacer content for gutenberg style
wp_spaceer_content = '<!-- wp:wak/spacer ' + json.dumps(space_template) +' /-->'
    
# Read URLs from the CSV file and validate them
try:
    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        total_urls = sum(1 for row in csv_reader)  # Count the total number of URLs
        file.seek(0)  # Reset the file position to the beginning
        next(csv_reader)  # Skip the header row

        for index, row in enumerate(csv_reader, start=1):
            url = row.get('URL')
            
            if url:
                try:
                    news_content = ''
                    print(f"# Start Scraping ({index}/{total_urls}): {url}")
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

                    # Find the meta tag with name="description"
                    meta_description = soup.find('meta', attrs={'name': 'description'})

                    # Get the content attribute
                    meta_description_content = meta_description['content']

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
                        image_response = requests.get(image_url, timeout=10)
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

                    # Make content images array
                    content_images = []
                    for media in media_data:
                        content_images.append(media['Image Name'])

                    # Make content captions array
                    content_captions = []
                    for media in media_data:
                        content_captions.append(media['Image Caption'])

                    # Append the extracted data to the list
                    extracted_data.append({
                        'URL': url,
                        'Author': author,
                        'Date': date,
                        'Title': title,
                        'Standfirst': standfirst,
                        'Meta': meta_description_content,
                        'Header Image': ', '.join(header_image_names),
                        'Content Images': ', '.join([media['Image Name'] for media in media_data]),
                        'Content Captions': ', '.join([media['Image Caption'] for media in media_data]),
                        'Text Sections': '\n\n'.join(text_section_data),
                        'YouTube Iframes': '\n\n'.join(youtube_iframes),
                    })

                    print(f"  - Scraped ({index}/{total_urls}): {url}")
                    
                    try:
                        # upload hero image file to media on WP as featured image.                        
                        new_hero_image_id = post_file(os.path.join(header_image_directory, header_image_names[0]))

                        # json data for news article hero
                        wp_article_hero_content = {
                            "name":"wak/news-article-hero",
                            "data":{
                                "wak_block_visibility": "all",
                                "title": title,
                                "subtitle": standfirst,
                                "use_featured": 1 ,
                                "image": new_hero_image_id,
                                },
                            "mode":"edit"
                        }
                        news_content +=  '<!-- wp:wak/news-article-hero ' + json.dumps(wp_article_hero_content) + ' /-->' + wp_spaceer_content 
                        
                        # Iteration of text secion and image block
                        
                        for index, text_section in enumerate(text_section_data):
                            
                            if len(text_section_data) > 1 and ('umb://document' in text_section) and (index == len(text_section_data) -1 ): # no need More news section
                                pass
                            else: 
                                # replace all /content/ to /news/
                                text_section = text_section.replace('/content/', '/news/')

                                # get h2 tag in the content
                                h2_text = ''
                                h2_soup = BeautifulSoup(text_section, 'html.parser')
                                h2_obj = h2_soup.find('h2')

                                if h2_obj != None:
                                    h2_text = h2_obj.text
                                
                                # remove h2 tag from the text section
                                if h2_text != '':
                                    first_h2_tag = h2_soup.find('h2')
                                    if first_h2_tag:
                                        first_h2_tag.extract()

                                    text_section = str(h2_soup)
                                    
                                # Checking the text secion is empty or not

                                spacer_flag = True
                                if text_section == '<div class="textSection">\n\n</div>' or text_section == '<div class="textSection">\n\n<p>\xa0</p>\n</div>':
                                    spacer_flag = False

                                # josn data for text section.
                                wp_text_section_advert = {
                                    "name":"wak/news-copy-image-advert",
                                    "data":{
                                        "wak_block_visibility":"all",
                                        "title": h2_text,
                                        "_title": "field_652d542d71c0f",
                                        "copy": text_section,
                                        "_copy":'field_652d547571c11',
                                        "advert":"0"
                                    },
                                    "mode":"edit"
                                }
                                news_content += '<!-- wp:wak/news-copy-image-advert ' + json.dumps(wp_text_section_advert) + ' /-->'
                                if spacer_flag:
                                    news_content +=  wp_spaceer_content
                            
                            if index < len(content_images):
                                # upload content image file to media on WP
                                new_content_img_id = post_file(os.path.join(content_image_directory, content_images[index]))

                                # json data for news image
                                wp_image_advert = {
                                    "name":"wak/news-copy-image-advert",
                                    "data":{
                                        "wak_block_visibility":"all",
                                        "title":"",
                                        "introduction_copy":"",
                                        "copy":"",
                                        "image":new_content_img_id,
                                        "_image":"field_652d549971c12",
                                        "caption": content_captions[index],
                                        "_caption":"field_652ea0fac8e2a",
                                        "advert":"0",
                                        },
                                    "mode":"edit"
                                } 

                                news_content += '<!-- wp:wak/news-copy-image-advert ' + json.dumps(wp_image_advert) + ' /-->' + wp_spaceer_content
                        
                        # put the youtube iframes into the content
                        if len(youtube_iframes):
                            #json data for iframes section
                            for iframe in youtube_iframes:
                                wp_iframe_section_advert = {
                                        "name":"wak/news-copy-image-advert",
                                        "data":{
                                            "wak_block_visibility":"all",
                                            "title":'Watch the video below',
                                            "_title": 'field_652d542d71c0f',
                                            "copy": iframe,
                                            "_copy":'field_652d547571c11',
                                            "advert":"0"
                                        },
                                        "mode":"edit"
                                    }
                                news_content += '<!-- wp:wak/news-copy-image-advert ' + json.dumps(wp_iframe_section_advert) + ' /-->' + wp_spaceer_content
                        
                        # post the author section
                        if author != "":
                            wp_author_advert = {
                                "name": "wak/news-author-footer",
                                "data":{
                                    "wak_block_visibility":"all",
                                    "author_name": author,
                                    "_author_name":"field_652eae9b6169c"
                                },
                                "mode":"edit"
                            }
                            news_content += '<!-- wp:wak/news-author-footer ' + json.dumps(wp_author_advert) + ' /-->' + wp_spaceer_content

                        #adding more news section on the block
                        wp_more_news = {
                            "name": "wak/more-news",
                            "data":{
                                "wak_block_visibility":"all",
                                "title": "Explore more",
                                "_title": "field_652d542d71c0f",
                            }
                        }
                        news_content += '<!-- wp:wak/more-news ' + json.dumps(wp_more_news) + ' /-->' + wp_spaceer_content
                        
                        # get post title from original title url
                        post_title = url.split('/content/')[1]
                        post_title = post_title.replace('-', ' ')
                        
                        # Post the news with all scrapped content
                        post_news(post_title, news_content, 'publish', new_hero_image_id, meta_description_content)
                          
                    except Exception as e:
                        print(f"   Error while posting the contents on WP: {e}")

                except Exception as e:
                    print(f"  Error analyzing {url} ({index}/{total_urls}): {e}")

except FileNotFoundError:
    print(f"CSV file '{csv_file}' not found.")


