from openai import OpenAI
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from page_scraper import ReviewScraper, get_pagination_class

class OutputGenerator:
    
    def __init__(self, url=None):
        self.url=url
        self.selector=None
        # Define the prompt template
        
        # Define the example HTML and output
        example_html = """
        <div class="ElementsWidget__list" role="alert"><!--v-if--><!--v-if--><div class="R-ContentList-container">
            <div class="R-ContentList">
                <div class="R-ContentList__item u-textLeft--all">
                    <div class="item__meta">
                        <div class="c-meta__authorDetails">
                            <div class="cssVar-authorName">David</div>
                        </div>
                    </div>
                    <div class="item__review">
                        <div class="R-TextHeading R-TextHeading--xxs u-textLeft--all">Essentials Nutrition Shake VANILLA</div>
                        <div class="R-TextBody R-TextBody--xs u-textLeft--all u-whiteSpace--prewrap">
                            Quality is good. My only issue is a bag should contain at least 30 level scoops to complete a month’s supply.
                        </div>
                    </div>
                    <div class="R-RatingStars"><span>5</span></div>
                </div>
            </div>
        </div>
        """

        example_output = """
        {{
            "title": "Essentials Nutrition Shake VANILLA",
            "body": "Quality is good. My only issue is a bag should contain at least 30 level scoops to complete a month’s supply.",
            "rating": 5,
            "reviewer": "David"
        }}
        """

        # Define the example prompt for formatting examples
        example_prompt = PromptTemplate(
            input_variables=["example_html", "example_output"],
            template="""
        HTML Input:
        {example_html}

        JSON Output:
        {example_output}
        """
        )

        # Define the prefix (before examples) and suffix (after examples)
        prefix = """
        You are an expert at extracting reviews from HTML scripts. Your task is to extract all reviews from the provided HTML input and return them in JSON format. 
        Make sure to extract the reviewer's full name (first name and last name). If the full name isn't available, return only the available name. The JSON output must include:

        - "title": The title of the review, if available.
        - "body": The full text of the review body.
        - "rating": The reviewer's rating as a number.
        - "reviewer": The reviewer's name.

        Please Note that there can be multiple reviews in a single html source code so return a list of reviews following the example template enclosed by []
        If any information is missing in the HTML input, leave the corresponding JSON field blank. Return only the required output. DO NOT generate additional text and return it only as string and DO NOT enclose it within ```json ```.

        ### Examples
        """

        suffix = """
        ---

        Here is the actual HTML input:

        HTML Input:
        {html_script}

        JSON Output:
        """
        # Instantiate the few-shot prompt template
        self.promptTemp = FewShotPromptTemplate(
            examples=[{"example_html": example_html, "example_output": example_output}],
            example_prompt=example_prompt,
            prefix=prefix,
            suffix=suffix,
            input_variables=["html_script"],
        )
    
    def getSelector(self):
        self.selector = get_pagination_class(self.url)
        print("Classname:" ,self.selector)
    
    #Extracts reviews in the required format from each page    
    def reviewExtractor(self, html_script):
        formatted_prompt=self.promptTemp.format(html_script=html_script)
        client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
        messages = [
                {"role": "system", "content": "You are an assistant that performs tasks exactly as stated by the user."},
                {"role": "user", "content": f"{formatted_prompt}"}
            ]
        completion = client.chat.completions.create(
            model="local_model",
            messages=messages,
            temperature=0.0,  # Set to 0 for most deterministic output
            max_tokens=1000,  # Limit response length since we only need the selector
            presence_penalty=0,
            frequency_penalty=0,
        )
        return completion.choices[0].message.content.strip() 
    
    #Generator which yields a string of reviews from each page            
    def generateReviews(self):
        scraper = ReviewScraper(url=self.url, pag_class=self.selector)
        scraper.start_scraping()
        
        while True:
            item = scraper.review_queue.get()
            if item is None:  # Check for completion signal
                break
            page_num, review_html = item
            # Your LLM processing logic here
            jsoncontent = self.reviewExtractor(review_html)
            yield jsoncontent
        
if __name__=="__main__":
    generator1=OutputGenerator(url="https://lyfefuel.com/products/essentials-nutrition-shake")
    generator2=OutputGenerator(url="https://bhumi.com.au/products/singlet-top")
    generator3=OutputGenerator(url="https://2717recovery.com/products/recovery-cream")
    generator1.getSelector()
    generator2.getSelector()
    generator3.getSelector()
    # generator.selector="jdgm-paginate__page"
    # gen=generator.generateReviews()
    # for val in gen:
    #     print(val)
    
    
    