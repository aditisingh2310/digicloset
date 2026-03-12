import './ProcessingSpinner.css';

/**
 * ProcessingSpinner Component
 * 
 * Shows while trying-on is being generated
 * Displays estimated time and progress
 */
export default function ProcessingSpinner() {
  return (
    <div className="processing-spinner">
      <div className="spinner">
        <div className="spinner-ring"></div>
      </div>
      <h3>Generating Your Try-On</h3>
      <p>This usually takes 30-60 seconds...</p>
      
      <div className="progress-indicator">
        <div className="progress-bar">
          <div className="progress-fill"></div>
        </div>
        <small>Processing image...</small>
      </div>
    </div>
  );
}
