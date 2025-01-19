from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re

def scroll_and_scrape(url, driver=None,scroll_pause_time=4):
    """
    Opens a URL, smoothly scrolls to the bottom, and saves the page source to a file.
    
    Args:
        url (str): The URL to scrape
        output_file (str): Path to save the HTML content
        scroll_pause_time (float): Time to pause between scrolls in seconds
    """
    if not driver:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (optional)
        
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        try:
            # Navigate to the URL
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get initial scroll height
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            while True:
                # Scroll down smoothly in smaller increments
                for i in range(10):
                    current_scroll = last_height * (i + 1) / 10
                    driver.execute_script(f"window.scrollTo(0, {current_scroll});")
                    time.sleep(scroll_pause_time / 10)
                
                # Wait for new content to load
                time.sleep(scroll_pause_time)
                
                # Calculate new scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # Check if the footer is rendered by looking for the footer's presence in the DOM
                try:
                    footer = driver.find_element(By.TAG_NAME, "footer")
                    footer_position = footer.location['y']
                    current_position = driver.execute_script("return window.pageYOffset + window.innerHeight")
                    
                    # Stop scrolling when we are just before the footer
                    if current_position + 100 >= footer_position:  # Adjust the '100' as needed
                        break
                except:
                    # If footer not found, continue scrolling
                    pass
                
                # Continue scrolling until we are near the footer
                last_height = new_height
            
            # Get the final page source
            page_source = driver.page_source
            print("Successfully extracted page source")
            return page_source
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        
        finally:
            driver.quit()
    else:
        try:
            driver.execute_script("window.scrollTo(0, 0);")
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get initial scroll height
            last_height = driver.execute_script("return document.body.scrollHeight")
        
            while True:
                # Scroll down smoothly in smaller increments
                for i in range(10):
                    current_scroll = last_height * (i + 1) / 10
                    driver.execute_script(f"window.scrollTo(0, {current_scroll});")
                    time.sleep(scroll_pause_time / 10)
                
                # Wait for new content to load
                time.sleep(scroll_pause_time)
                
                try:
                    popup = driver.find_element(By.XPATH, "//div[@role='dialog'][contains(@aria-label, 'POPUP Form')]")
                    close_button = popup.find_element(By.XPATH, ".//button[@aria-label='Close dialog']")  # Assuming the button has aria-label 'Close'
                    close_button.click()
                    time.sleep(1)  # Wait for the popup to close
                except Exception as e:
                    print(f"No popup found or error while closing: {e}")
                
                # Calculate new scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # Check if the footer is rendered by looking for the footer's presence in the DOM
                try:
                    footer = driver.find_element(By.TAG_NAME, "footer")
                    footer_position = footer.location['y']
                    current_position = driver.execute_script("return window.pageYOffset + window.innerHeight")
                    
                    # Stop scrolling when we are just before the footer
                    if current_position + 100 >= footer_position:  # Adjust the '100' as needed
                        break
                except:
                    # If footer not found, continue scrolling
                    pass
                
                # Continue scrolling until we are near the footer
                last_height = new_height
            
            # Get the final page source
            page_source = driver.page_source
            print("Successfully extracted page source")
            return page_source
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None
        


def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    #Remove all images and related elements
    for element in soup.find_all(["script", "footer","style", "meta", "link", "header","img", "picture", "svg", "figure", "iframe"]):
        element.decompose()
        
    #Remove elements with "overlay" in class name
    for element in soup.find_all(True):
        if element.attrs and 'class' in element.attrs:  # Check if attrs is not None and contains 'class'
            class_names = element.attrs['class']
            if any("overlay" in cls.lower() for cls in class_names):
                element.decompose()
        
    unnecessary_attrs = [
        'style',
        'onclick',
        'onload',  # accessibility attributes if not needed  # data attributes
        'src',     # since we removed images
        'href'    # remove links,      # usually not needed for extraction
        'alt',
        'tabindex',
        'target',
        'rel',
        'width',
        'height',
        'data-type'
    ]
    
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if any(attr.startswith(x.replace('*', '')) for x in unnecessary_attrs):
                del tag[attr]
    
    #Remove empty elements
    for element in soup.find_all():
        if len(element.get_text(strip=True)) == 0 and not element.find_all():
            element.decompose()
    
    #Remove uneccessary classname containing the following substrings 
    tooltip_patterns = [
        'tooltip', 
        'popover', 
        'hover-content',
        'tippy',
        'hint',
        'bubble',
        'popup-text',
        'helptext',
        'help-text',
        'title-tip',
        'slider',
        'flex',
        'media',
        'image',
        'margin',
        'dropup',
        'dropdown',
        'dropupdown',
        'padding',
        'align'
        'inline'
    ]
    
    for element in soup.find_all(True):
        try:
            if hasattr(element, 'attrs') and element.attrs is not None:
                # Remove all attributes that contain 'tooltip' in their name
                attrs_to_remove = [
                    attr for attr in element.attrs.keys()
                    if 'tooltip' in attr.lower()
                ]
                for attr in attrs_to_remove:
                    del element[attr]
                
                # Handle regular tooltip attributes
                for attr in ['data-tooltip']:
                    if attr in element.attrs:
                        del element[attr]
                
                # Handle r-tooltip and related attributes
                r_tooltip_attrs = [
                    attr for attr in element.attrs.keys()
                    if attr.startswith('r-tooltip')
                ]
                for attr in r_tooltip_attrs:
                    del element[attr]
                
                # Handle multiple class names
                if 'class' in element.attrs and element.attrs['class']:
                    classes = element.attrs['class']
                    cleaned_classes = [
                        cls for cls in classes 
                        if not any(tip in cls.lower() for tip in tooltip_patterns)
                    ]
                    
                    if cleaned_classes:
                        element.attrs['class'] = cleaned_classes
                    else:
                        del element.attrs['class']
                        
                # Check for tooltip-related IDs
                if 'id' in element.attrs and element.attrs['id']:
                    id_str = element.attrs['id'].lower()
                    if any(tip in id_str for tip in tooltip_patterns):
                        del element.attrs['id']
                        
        except (AttributeError, TypeError):
            continue
    
    
    html = str(soup)
    html = re.sub(r'\n\s*\n', '\n', html)
    html = re.sub(r'\s+', ' ', html)
    
    return html.strip()

def extract_reviews_section(html_content):
    """
    Extract HTML from the reviews section to the bottom of the page using dynamic heuristics.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Look for review-related containers (divs, articles, etc.)
    review_identifiers = ['Customer Reviews', 'Reviews', 'Product Reviews', 'Ratings & Reviews', 'product-reviews', 'customer-reviews', 'ratings', 'reviews-summary']
    review_section = None

    total_content_length = len(str(soup))

    # Define a minimum percentage of content that should be considered as the review section (e.g., 1% of total content length)
    min_content_percentage = 0.01
    min_content_length = total_content_length * min_content_percentage

    for identifier in review_identifiers:
        # Find elements with class names or IDs related to reviews
        sections_by_class = soup.find_all(attrs={'class': re.compile(identifier, re.IGNORECASE)})
        sections_by_id = soup.find_all(attrs={'id': re.compile(identifier, re.IGNORECASE)})
        sections = sections_by_class + sections_by_id
        if sections:
            print("Entered if sections")
            for section in sections:
                section_html = str(section)
                # Only consider sections that are larger than the minimum content length
                seclen=len(section_html)
                if len(section_html) > min_content_length:
                    if not review_section:
                        review_section = section
                    else:
                        if seclen>=len(review_section):
                            review_section = section
        if review_section:
            break

    if not review_section:
        print("Entered if not review_section")
        # If no review section is found using class names, try finding the review summary (e.g., stars, rating count)
        reviews_summary = soup.find(attrs={'class': re.compile(r'rating|reviews-summary', re.IGNORECASE)})
        if reviews_summary:
            # Capture content starting from the reviews summary section
            review_section = reviews_summary.find_parent()

    if review_section:
        # Capture all content from the review section and ignore anything after it
        result = ""
        current = review_section
        while current:
            result += str(current)
            next_sibling = current.find_next_sibling()
            if next_sibling:
                # Stop if we reach a section unrelated to reviews
                if 'footer' in str(next_sibling).lower() or 'related' in str(next_sibling).lower():
                    break
            current = next_sibling

        return result
    else:
        return None
    



def get_ancestors(element, levels=4):
    """
    Get the specified number of ancestor elements for a given element.
    Returns all available ancestors if there are fewer than requested levels.
    """
    ancestors = []
    current = element
    for _ in range(levels - 1):  # -1 because we want to include the element itself
        parent = current.parent
        if parent is None:
            break
        ancestors.append(parent)
        current = parent
    return ancestors[::-1]

def has_text_content(element):
    """
    Check if an element has any non-whitespace text content.
    """
    return bool(element.string and element.string.strip())
    
def filter_reviews(html_content, levels=4):
    """
    Extracts the innermost four levels (or fewer if not available) of DOM elements 
    that contain text and returns them as a formatted HTML string.
    Only includes elements that have actual text content.
    
    Args:
        html_content (str): HTML content to parse
        levels (int): Number of levels to extract (default: 4)
        
    Returns:
        str: Formatted HTML string containing the extracted elements
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # Find all elements that contain direct text
    text_containing_elements = []
    for elem in soup.find_all():
        # Check if the element has direct text content
        if has_text_content(elem):
            # Check if any child elements also have text content
            child_with_text = any(has_text_content(child) for child in elem.find_all())
            # Only include if this is the innermost text-containing element
            if not child_with_text:
                text_containing_elements.append(elem)
    
    for elem in text_containing_elements:
        # Get ancestors up to specified levels
        ancestors = get_ancestors(elem, levels)
        
        if ancestors:
            # Create new soup object for the output
            new_soup = BeautifulSoup(features='html.parser')
            
            # Start with the outermost ancestor we want to keep
            current_new = new_soup.new_tag(
                ancestors[0].name,
                attrs=ancestors[0].attrs
            )
            root = current_new
            
            # Rebuild the nested structure
            for ancestor in ancestors[1:]:
                new_tag = new_soup.new_tag(
                    ancestor.name,
                    attrs=ancestor.attrs
                )
                current_new.append(new_tag)
                current_new = new_tag
            
            # Add the text-containing element itself
            new_elem = new_soup.new_tag(
                elem.name,
                attrs=elem.attrs
            )
            new_elem.string = elem.string.strip()
            current_new.append(new_elem)
            
            results.append(str(root))
        else:
            # If no ancestors (single level), just add the element itself
            new_soup = BeautifulSoup(features='html.parser')
            new_elem = new_soup.new_tag(
                elem.name,
                attrs=elem.attrs
            )
            new_elem.string = elem.string.strip()
            results.append(str(new_elem))
    
    # Join results with newlines
    formatted_html = ""
    for result in results:
        lines = result.split('\n')
        for line in lines:
            formatted_html += line.strip() + '\n'
    
    return formatted_html.strip()

# Example usage(testing purposes)
# if __name__ == "__main__":
#     # url = "https://2717recovery.com/products/recovery-cream"  # Replace with your target URL
#     # url="https://bhumi.com.au/products/singlet-top"
#     # url = "https://lyfefuel.com/products/essentials-nutrition-shake"
#     html_source=scroll_and_scrape(url)
#     html_cleaned=clean_html(html_source)
#     print(len(html_cleaned))
#     reviews=extract_reviews_section(html_cleaned)
#     print(len(reviews))
#     # reviews=filter_reviews(reviews, levels=1)
#     output_file="reviews.html"
#     # clickable_elements=get_clickable_elements(reviews)
#     with open(output_file, 'w', encoding='utf-8') as f:
#         f.write(str(reviews))    
#         print(f"Successfully saved cleaned page source to {output_file}")