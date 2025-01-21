from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import json
from threading import Thread, Event
import time
from queue import Queue
import logging
from llm_summarizer import *
from html_extractor import *
from page_scraper import *

app = Flask(__name__, static_folder="../review_api/build", static_url_path = "/")
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "supports_credentials": True
    }
})
logging.basicConfig(level=logging.INFO)

# Store active review managers and their results
active_processes = {}

class ProcessManager:
    def __init__(self, url, review_manager, queue):
        self.url = url
        self.manager = review_manager
        self.queue = queue
        self.stop_event = Event()
        self.thread = None

    def start(self):
        """Start the background processor thread."""
        self.thread = Thread(target=self.background_processor)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the background processor thread and the scraping process."""
        logging.info(f"Stopping processing for {self.url}")

        # Signal the stop event
        self.stop_event.set()

        # Call stop_scraping to stop the scraping thread
        try:
            self.manager.stop_scraping()
            logging.info(f"Scraping process for {self.url} stopped successfully.")
        except Exception as e:
            logging.error(f"Error stopping the scraping process: {e}")

        # Wait for the background thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            logging.info(f"Stopped process for {self.url}")

        # Ensure the generator has stopped
        try:
            self.manager.finalize_generator()
        except Exception as e:
            logging.error(f"Error finalizing generator: {e}")

    def background_processor(self):
        """Background thread to process reviews."""
        try:
            logging.info(f"Starting review processing for {self.url}")
            success = self.manager.add_reviews(stop_event=self.stop_event)
            if success and not self.stop_event.is_set():
                self.queue.put(("complete", None))
            else:
                self.queue.put(("error", "Failed to process reviews"))
        except Exception as e:
            logging.error(f"Error processing reviews: {str(e)}")
            self.queue.put(("error", str(e)))


def generate_updates(url, process_manager):
    """Generator for SSE events"""
    last_result = None
    
    while not process_manager.stop_event.is_set():
        if not process_manager.queue.empty():
            status, error = process_manager.queue.get()
            if status == "error":
                yield f"data: {json.dumps({'error': error})}\n\n"
                break
            elif status == "complete":
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                break

        current_result = process_manager.manager.get_reviews()
        if current_result and current_result != last_result:
            yield f"data: {json.dumps(current_result)}\n\n"
            last_result = current_result.copy()
            
        time.sleep(1)

class ReviewManager(OutputGenerator):
    def __init__(self, url):
        super().__init__(url=url)
        self.result = {
            "reviews_count": 0,
            "reviews": []
        }
        self.generator_running = False
        
    def initialize_selector(self):
        """Initialize the selector before processing reviews"""
        try:
            logging.info("Getting selector...")
            self.getSelector()
            if not self.selector:
                logging.error("Failed to get selector")
                return False
            logging.info(f"Successfully got selector: {self.selector}")
            return True
        except Exception as e:
            logging.error(f"Error getting selector: {e}")
            return False

    def stop_scraping(self):
        """Stop the scraping process."""
        logging.info("Stopping the scraping process...")
        super().stop_scraping()  # Assumes stop_scraping is implemented in page_scraper.py

    def finalize_generator(self):
        """Ensure the generator is fully consumed and stopped."""
        if self.generator_running:
            logging.info("Waiting for the review generator to finish...")
            while self.generator_running:
                time.sleep(0.5)
            logging.info("Review generator has stopped.")

    def add_reviews(self, stop_event=None):
        """Process reviews and add them to the result."""
        try:
            if not self.initialize_selector():
                return False

            logging.info("Starting review generation...")
            gen = self.generateReviews()

            if not gen:
                logging.error("Review generator is None")
                return False

            self.generator_running = True
            reviews_processed = False

            for val in gen:
                if stop_event and stop_event.is_set():
                    logging.info("Stop event received. Halting generator processing.")
                    break
                if not val:
                    logging.warning("Empty value from generator, skipping...")
                    continue

                try:
                    new_reviews = json.loads(val)
                    formatted_reviews = [
                        {
                            "title": review.get("title", "No Title"),
                            "body": review.get("body", "No Body"),
                            "rating": review.get("rating", 0),
                            "reviewer": review.get("reviewer", "Anonymous")
                        }
                        for review in new_reviews if isinstance(review, dict)
                    ]
                    if formatted_reviews:
                        self.result["reviews"].extend(formatted_reviews)
                        self.result["reviews_count"] += len(formatted_reviews)
                        reviews_processed = True
                        logging.info(f"Added {len(formatted_reviews)} reviews. Total: {self.result['reviews_count']}")
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decode error: {e}")
                    continue
                except Exception as e:
                    logging.error(f"Error processing review: {e}")
                    continue

            self.generator_running = False
            return reviews_processed

        except Exception as e:
            logging.error(f"Error in add_reviews: {e}")
            self.generator_running = False
            return False

    def get_reviews(self):
        return self.result


@app.route('/api/reviews', methods=['GET'])
def reviews():
    url = request.args.get('page')
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400
    
    if "https://" not in url:
        url="https://"+url

    # Stop any existing processes before starting a new one
    for existing_url, process in list(active_processes.items()):
        if existing_url != url:
            logging.info(f"Stopping existing process for {existing_url}")
            process.stop()
            del active_processes[existing_url]

    # Create new process if it doesn't exist
    if url not in active_processes:
        try:
            review_manager = ReviewManager(url=url)
            queue = Queue()
            
            process_manager = ProcessManager(url, review_manager, queue)
            active_processes[url] = process_manager
            process_manager.start()
            
            logging.info(f"Started processing for {url}")
        except Exception as e:
            logging.error(f"Error initializing review manager: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return Response(
        generate_updates(url, active_processes[url]),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )
    
@app.route('/')
def homepage():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == '__main__':
    app.run(debug=True)