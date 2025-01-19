from html_extractor import scroll_and_scrape, clean_html, extract_reviews_section, filter_reviews
import time
from queue import Queue
import threading
from openai import OpenAI
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def llm_function(prompt):
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    messages = [
            {"role": "system", "content": "You are an assistant that performs tasks exactly as stated by the user."},
            {"role": "user", "content": f"{prompt}"}
        ]
    completion = client.chat.completions.create(
        model="local_model",
        messages=messages,
        temperature=0.0,  # Set to 0 for most deterministic output
        max_tokens=50,  # Limit response length since we only need the selector
        presence_penalty=0,
        frequency_penalty=0
    )
    return completion.choices[0].message.content.strip()

def get_pagination_class(url):
    html_source=scroll_and_scrape(url)
    cleaned_html=clean_html(html_source)
    reviews=extract_reviews_section(cleaned_html)
    reviews=filter_reviews(reviews, levels=2) 
    page_number="1"
    examples = [
        {
            "input": "HTML source code:\n<div class='pagination'>\n  <a class='jdgm-paginate__page jdgm-curt' data-page='1' aria-label='Page 1' tabindex='0' role='button'>1</a>\n  <a class='jdgm-paginate__page' data-page='2' aria-label='Page 2' tabindex='0' role='button'>2</a>\n</div>\n\nPage number: 1",
            "output": "Class name: jdgm-paginate__page"
        },
        {
            "input": "HTML source code:\n<nav>\n  <ul class='pagination'>\n    <li><a class='paginate-item' href='/reviews?page=1' role='button'>1</a></li>\n    <li><a class='paginate-item' href='/reviews?page=2' role='button'>2</a></li>\n  </ul>\n</nav>\n\nPage number: 2",
            "output": "Class name: paginate-active"
        },
        {
            "input": "HTML source code:\n<div class='R-PaginationControls__item' role='button' tabindex='0' data-type='link'><div class='R-TextHeading R-TextHeading--xxxs'>3</div></div>\n\nPage number: 3",
            "output": "Class name: R-PaginationControls__item"
        },
        {
            "input": "HTML source code:\n<div class='pagination-container'>\n  <button class='prev-page'>Previous</button>\n  <button class='next-page'>Next</button>\n  <span class='page-number'>1</span>\n  <span class='page-number'>2</span>\n</div>\n\nPage number: 2",
            "output": "Class name: page-number"
        },
        {
            "input": "HTML source code:\n<div class='pagination_wrapper'>\n  <a class='page-link' href='/page=1' data-page='1' aria-label='Page 1'>1</a>\n  <a class='page-link' href='/page=2' data-page='2' aria-label='Page 2'>2</a>\n  <a class='page-link' href='/page=3' data-page='3' aria-label='Page 3'>3</a>\n</div>\n\nPage number: 2",
            "output": "Class name: page-link"
        },
        {
            "input": "HTML source code:\n<div class='pagination_control'>\n  <a class='pagination_btn' data-page='1' href='#'>1</a>\n  <a class='pagination_btn' data-page='2' href='#'>2</a>\n  <a class='pagination_btn' data-page='3' href='#'>3</a>\n</div>\n\nPage number: 3",
            "output": "Class name: pagination_btn"
        },
        {
            "input": "HTML source code:\n<ul class='page-nav-list'>\n  <li><a href='/page/1' class='page-item'>1</a></li>\n  <li><a href='/page/2' class='page-item'>2</a></li>\n  <li><a href='/page/3' class='page-item'>3</a></li>\n</ul>\n\nPage number: 1",
            "output": "Class name: page-item"
        },
        {
            "input": "HTML source code:\n<div class='pagination_wrapper'>\n  <button class='page-btn' data-page='1' role='button'>1</button>\n  <button class='page-btn' data-page='2' role='button'>2</button>\n  <button class='page-btn' data-page='3' role='button'>3</button>\n</div>\n\nPage number: 2",
            "output": "Class name: page-btn"
        },
        {
            "input": "HTML source code:\n<div class='pagination__controls'>\n  <a href='/page=1' class='page-button' data-page='1'>1</a>\n  <a href='/page=2' class='page-button' data-page='2'>2</a>\n</div>\n\nPage number: 2",
            "output": "Class name: page-button"
        },
        {
            "input": "HTML source code:\n<div class='pagination'><a href='/page-1' class='pagination__link' data-page='1'>1</a><a href='/page-2' class='pagination__link' data-page='2'>2</a></div>\n\nPage number: 1",
            "output": "Class name: pagination__link"
        }
    ]
    
    # Define the prompt template
    template = FewShotPromptTemplate(
        examples=examples,
        example_prompt=PromptTemplate(
            input_variables=["input", "output"],
            template="{input}\n{output}"
        ),
        prefix=(
            "Your task is to extract the class name of the pagination element  which contains the page number in the atrributes or inner text (element which when clicked navigates to a new page or renders new content) from the provided HTML source "
            "for a given page number. The pagination element can often be identified by: "
            "1) the 'role' attribute (e.g., role='button'), "
            "2) attributes containing the substring 'paginate' or 'pagination',"
            "3) any other contextual indicators that match the concept of a pagination button.,"
            "4) Do not just copy the examples given analyze the html source code and return the output based on it"
            "Even if the exact attribute names differ from the examples, use logical reasoning to find the correct element. "
            "If the class name atrribute contains multiple names seperated by a blank space then return the first name"
            "Below are examples to guide you:"
        ),
        suffix="HTML source code:\n{reviews}\n\nPage number: {page_number}\n\nReturn only the class name DO NOT generate additional text:",
        input_variables=["reviews", "page_number"],
        example_separator="\n---\n"
    )
    formatted_prompt = template.format(reviews=reviews, page_number=page_number)
    response=llm_function(formatted_prompt)
    return response
 
class ReviewScraper:
    def __init__(self, url, pag_class, max_pages=None):
        self.url = url
        self.pag_class = pag_class
        self.max_pages = max_pages
        self.review_queue = Queue(maxsize=10)  # Buffer size of 10 pages
        self.is_scraping = True
        self.scraper_thread = None

    def _scrape_reviews(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(self.url)
        current_page = 1
        page_num = 2
        max_attempts = 3

        try:
            while self.is_scraping:
                if self.max_pages and current_page > self.max_pages:
                    break

                # Get current page content
                src_code = scroll_and_scrape(self.url, driver=driver, scroll_pause_time=2)
                cleaned_html = clean_html(src_code)
                review = extract_reviews_section(cleaned_html)
                # review=filter_reviews(review, levels=4)
                
                # Put the review in the queue
                self.review_queue.put((current_page, review))
                print(f"Extracted content from page {current_page}")

                if max_attempts <= 0:
                    break

                try:
                    # Pagination logic
                    pagination_found = False
                    
                    # Strategy 1: Direct class and number match
                    try:
                        elements = driver.find_elements(By.CLASS_NAME, self.pag_class)
                        for element in elements:
                            if element.text.strip() == str(page_num):
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                time.sleep(1)
                                element.click()
                                pagination_found = True
                                break
                    except Exception as e:
                        print(f"Strategy 1 failed: {e}")

                    # Strategy 2: Find elements containing the class
                    if not pagination_found:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, f"[class*='{self.pag_class}']")
                            for element in elements:
                                if element.text.strip() == str(page_num):
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", element)
                                    pagination_found = True
                                    break
                        except Exception as e:
                            print(f"Strategy 2 failed: {e}")

                    # Strategy 3: Look for any clickable element with the page number
                    if not pagination_found:
                        try:
                            xpath_query = f"//*[contains(@class, '{self.pag_class}')]|//*[contains(@class, '{self.pag_class}')]//*"
                            elements = driver.find_elements(By.XPATH, xpath_query)
                            for element in elements:
                                if element.text.strip() == str(page_num):
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", element)
                                    pagination_found = True
                                    break
                        except Exception as e:
                            print(f"Strategy 3 failed: {e}")

                    if not pagination_found:
                        raise Exception("No pagination element found")

                    time.sleep(1)
                    current_page += 1
                    page_num += 1
                    max_attempts = 3

                except Exception as e:
                    print(f"Error during pagination: {str(e)}")
                    max_attempts -= 1
                    if max_attempts <= 0:
                        break

        finally:
            driver.quit()
            self.review_queue.put(None)  # Signal completion

    def start_scraping(self):
        """Start the scraping process in a background thread"""
        self.scraper_thread = threading.Thread(target=self._scrape_reviews)
        self.scraper_thread.start()
        
    def get_review_queue(self):
        """Returns the review queue for external processing"""
        return self.review_queue

    def stop(self):
        """Stop the scraping process"""
        self.is_scraping = False
        if self.scraper_thread:
            self.scraper_thread.join()
            
# if __name__ == "__main__":
#     # response=get_pagination_class("https://lyfefuel.com/products/essentials-nutrition-shake")
#     response='jdgm-paginate__page'
#     reviews=get_all_html_reviews_source("https://2717recovery.com/products/recovery-cream", pag_class=response)
#     print(len(reviews))