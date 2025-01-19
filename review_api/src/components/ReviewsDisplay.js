import React from 'react';

const ReviewsDisplay = ({ reviews }) => {
  return (
    <div>
      <h2>Reviews</h2>
      <p>Total Reviews: {reviews.reviews_count}</p>
      <ul>
        {reviews.reviews.map((review, index) => (
          <li key={index}>{review}</li>
        ))}
      </ul>
    </div>
  );
};

export default ReviewsDisplay;
