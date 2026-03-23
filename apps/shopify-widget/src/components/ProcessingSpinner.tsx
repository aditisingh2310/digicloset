import './ProcessingSpinner.css';

interface ProcessingSpinnerProps {
  attempt: number;
  statusText: string;
  onCancel: () => void;
}

const STEPS = ['Analyzing fit', 'Balancing fabric detail', 'Finishing render'];

/**
 * ProcessingSpinner Component
 *
 * Shows while trying-on is being generated
 * Displays estimated time and progress
 */
export default function ProcessingSpinner({
  attempt,
  statusText,
  onCancel,
}: ProcessingSpinnerProps) {
  const progress = Math.min(24 + attempt * 11, 94);
  const activeStep = Math.min(Math.floor(attempt / 2), STEPS.length - 1);

  return (
    <div className="processing-spinner">
      <p className="processing-spinner__eyebrow">Step 2</p>
      <div className="spinner">
        <div className="spinner-ring"></div>
      </div>
      <h3>Generating your try-on preview</h3>
      <p>{statusText}. This usually takes 30 to 60 seconds.</p>

      <div className="progress-indicator">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }}></div>
        </div>
        <small>We are keeping you updated while the render finishes.</small>
      </div>

      <div className="processing-spinner__steps">
        {STEPS.map((step, index) => (
          <div
            key={step}
            className={`processing-spinner__step ${
              index <= activeStep ? 'processing-spinner__step--active' : ''
            }`}
          >
            <span>{index + 1}</span>
            <p>{step}</p>
          </div>
        ))}
      </div>

      <button type="button" className="btn btn-secondary" onClick={onCancel}>
        Start over
      </button>
    </div>
  );
}
