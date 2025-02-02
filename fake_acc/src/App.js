import React, { useState } from 'react';
import './App.css';

const App = () => {
  const [username, setUsername] = useState('');
  const [profileData, setProfileData] = useState(null);
  const [error, setError] = useState('');

  const handleDetectProfile = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/detect_profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username }), // Send the username as JSON
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      setProfileData(data);
      setError(''); // Clear any previous error
    } catch (err) {
      console.error('Error fetching profile data:', err);
      setError('Error fetching profile data. Please try again.'); // Set error message
      setProfileData(null); // Clear previous data
    }
  };

  return (
    <div className="App">
      <h1>Fake Social Media Profile Detection</h1>
      <input
        type="text"
        placeholder="Enter the exact Twitter username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <button onClick={handleDetectProfile}>Detect Profile</button>
      {error && <p style={{ color: 'red' }}>{error}</p>} {/* Display error message */}
      {profileData && (
        <div>
          <h2>Profile Data</h2>
          <p>Username: {profileData[0].username}</p>
          <p>Followers Count: {profileData[0].followers_count}</p>
          <p>Following Count: {profileData[0].following_count}</p>
          <p>Subscriptions Count: {profileData[0].subscriptions_count}</p>
          <p>Is Verified: {profileData[0].is_verified ? 'Yes' : 'No'}</p>
          <p>Status: {profileData[0].status}</p>
        </div>
      )}
    </div>
  );
};

export default App;
