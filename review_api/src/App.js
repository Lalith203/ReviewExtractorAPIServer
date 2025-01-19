import React, { useState, useEffect } from 'react';
import "./App.css";
import searchIcon from "./images/search.png";
import { Star } from 'lucide-react';

// ReviewsDisplay component
const ReviewsDisplay = ({ reviews_count = 0, reviews = [] }) => {
  const safeReviews = Array.isArray(reviews) ? reviews : [];
  
  const renderStars = (rating) => {
    return [...Array(5)].map((_, index) => (
      <Star 
        key={index}
        size={16}
        strokeWidth={1.5}
        className={`star-icon ${
          index < rating 
            ? 'filled-star' 
            : 'empty-star'
        }`}
      />
    ));
  };

  if (safeReviews.length === 0) {
    return (
      <div className="reviewsContainer p-6">
        <p className="text-white text-center">No reviews available.</p>
      </div>
    );
  }

  return (
    <div className="reviewsContainer p-6">
      <h2 className="text-2xl font-bold mb-6 text-white">
        Reviews ({reviews_count || safeReviews.length})
      </h2>
      <div className="space-y-4">
        {safeReviews.map((review, index) => (
          <div 
            key={index}
            className="bg-white rounded-lg p-6 shadow-lg transition-all duration-300 hover:shadow-xl"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-lg text-gray-900">
                  {review.title || 'Untitled Review'}
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  Reviewed by {review.reviewer || 'Anonymous'}
                </p>
              </div>
              <div className="flex items-center gap-1">
                {renderStars(review.rating || 0)}
              </div>
            </div>
            
            <p className="text-gray-700 leading-relaxed">
              {review.body || 'No review content'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

// Main App component
const App = () => {
  const [url, setUrl] = useState('');
  const [reviewDict, setReviewDict] = useState({ reviews_count: 0, reviews: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    console.log('reviewDict has been updated:', reviewDict);
  }, [reviewDict]);

  const handleUrlSubmit = (submittedUrl) => {
    setUrl(submittedUrl.trim());
    setReviewDict({ reviews_count: 0, reviews: [] });
    setLoading(true);
    setError('');
  };

  useEffect(() => {
    if (!url) return;

    const eventSource = new EventSource(`http://localhost:5000/api/reviews?page=${encodeURIComponent(url)}`);

    eventSource.onmessage = (event) => {
      console.log('Incoming SSE data:', event.data);
      try {
        const data = JSON.parse(event.data);

        if (data.error) {
          setError(data.error);
          setLoading(false);
          eventSource.close();
        } else if (data.status === 'complete') {
          console.log('Processing complete:', data);
          setLoading(false);
          eventSource.close();
        } else {
          console.log('Update received:', data);
          setReviewDict((prevReviews) => ({
            reviews_count: data.reviews_count || prevReviews.reviews_count,
            reviews: data.reviews || prevReviews.reviews,
          }));
        }
      } catch (e) {
        console.error('Error parsing SSE data:', e, event.data);
        setError('Error processing incoming data.');
        setLoading(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setError('Connection error. Please try again.');
      setLoading(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [url]);

  return (
    <div className="main_page_container">
      <div className="page_title">
        <h1>Review Scraper</h1>
      </div>

      <form className="searchbar"
        onSubmit={(e) => {
          e.preventDefault();
          const inputUrl = e.target.elements.url.value;
          if (inputUrl) handleUrlSubmit(inputUrl);
        }} 
      >
        <input type="text" placeholder="Enter the URL" name="url" autoComplete="off"/>
        <button type="submit">
          <img src={searchIcon} alt="Search"/>
        </button>
      </form>

      {loading && <p className="loading_bar">Loading reviews... Please wait.</p>}
      
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {!error && reviewDict.reviews_count > 0 && (
        <ReviewsDisplay 
          reviews_count={reviewDict.reviews_count} 
          reviews={reviewDict.reviews} 
        />
      )}
    </div>
  );
};

export default App;