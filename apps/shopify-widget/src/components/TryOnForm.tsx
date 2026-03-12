import { useState } from 'react';
import './TryOnForm.css';

interface FormData {
  category: string;
  size: string;
  includeBackground: boolean;
}

interface TryOnFormProps {
  onSubmit: (data: FormData) => void;
}

/**
 * TryOnForm Component
 * 
 * Optional form for:
 * - Garment category selection
 * - Size preferences
 * - Additional parameters
 */
export default function TryOnForm({ onSubmit }: TryOnFormProps) {
  const [category, setCategory] = useState('upper_body');
  const [size, setSize] = useState('M');
  const [includeBackground, setIncludeBackground] = useState(true);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    onSubmit({
      category,
      size,
      includeBackground
    });
  };

  return (
    <form className="tryon-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="category">Garment Category</label>
        <select
          id="category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="upper_body">Upper Body (Shirt, Dress, etc.)</option>
          <option value="lower_body">Lower Body (Pants, Skirt, etc.)</option>
          <option value="full_body">Full Body Outfit</option>
          <option value="accessories">Accessories</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="size">Preferred Size</label>
        <select
          id="size"
          value={size}
          onChange={(e) => setSize(e.target.value)}
        >
          <option value="XS">Extra Small</option>
          <option value="S">Small</option>
          <option value="M">Medium</option>
          <option value="L">Large</option>
          <option value="XL">Extra Large</option>
          <option value="2XL">2XL</option>
        </select>
      </div>

      <div className="form-group checkbox">
        <input
          type="checkbox"
          id="background"
          checked={includeBackground}
          onChange={(e) => setIncludeBackground(e.target.checked)}
        />
        <label htmlFor="background">Keep background</label>
      </div>

      <button type="submit" className="submit-btn">
        Next Step
      </button>
    </form>
  );
}
