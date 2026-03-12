import './ResultDisplay.css';

interface TryOnResult {
  image_url: string;
  id: string;
  processing_time?: number;
  [key: string]: unknown;
}

interface ResultDisplayProps {
  result: TryOnResult;
  onRetry: () => void;
}

/**
 * ResultDisplay Component
 * 
 * Shows:
 * - Generated try-on image
 * - Processing time
 * - Action buttons (share, download, add to cart)
 */
export default function ResultDisplay({ result, onRetry }: ResultDisplayProps) {
  const handleDownload = async () => {
    try {
      const response = await fetch(result.image_url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tryon-${result.id}.png`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'Virtual Try-On',
        text: 'Check out how I look in this!',
        url: window.location.href
      });
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(window.location.href);
      alert('Link copied to clipboard');
    }
  };

  return (
    <div className="result-display">
      <h2>Your Try-On Result</h2>

      <div className="result-image-container">
        <img
          src={result.image_url}
          alt="Try-on result"
          className="result-image"
        />
      </div>

      <div className="result-info">
        <p className="processing-time">
          ✓ Generated in {result.processing_time || 0}s
        </p>
      </div>

      <div className="action-buttons">
        <button
          onClick={handleDownload}
          className="btn btn-download"
          title="Download as image"
        >
          📥 Download
        </button>

        <button
          onClick={handleShare}
          className="btn btn-share"
          title="Share with friends"
        >
          📤 Share
        </button>

        <button
          onClick={() => {
            // Add to cart logic
            const event = new CustomEvent('tryon:addToCart', {
              detail: { imageSrc: result.image_url }
            });
            window.dispatchEvent(event);
          }}
          className="btn btn-cart"
          title="Add to cart"
        >
          🛒 Add to Cart
        </button>
      </div>

      <div className="divider"></div>

      <button
        onClick={onRetry}
        className="btn btn-secondary"
      >
        Try Another Item
      </button>

      <div className="result-footer">
        <small>
          Try-On ID: {result.id}
        </small>
      </div>
    </div>
  );
}
