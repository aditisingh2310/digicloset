# DigiCloset Model Versioning Strategy

## Active Models

| Component | Model | Version | Dimensions | Source |
|-----------|-------|---------|------------|--------|
| Image Embeddings | OpenCLIP ViT-B-32 | `laion2b_s34b_b79k` | 512 | `open_clip_torch>=2.24.0` |
| Background Removal | U-2-Net | `rembg 2.0.53` | N/A | `rembg==2.0.53` |
| Color Extraction | KMeans (scikit-learn) | N/A | 3 channels (LAB) | `scikit-learn>=1.3.0` |
| Vision LLM (Stylist) | Llama 3.2 11B Vision Instruct | `free` tier | N/A | OpenRouter API |
| FAISS Index | Flat L2 | faiss-cpu 1.7.4+ | 512 | `faiss-cpu>=1.7.4` |

## FAISS Index Schema

- **Index type**: `IndexFlatL2` (exact search, no quantization)
- **Dimension**: 512 (must match OpenCLIP output)
- **Storage**: In-memory with optional disk persistence
- **Item mapping**: `item_id (str) → index position (int)` via Python dict

## Migration Guide

### Changing Embedding Model (e.g. ViT-B-32 → ViT-L-14)

1. Update `embedding_service.py`: change `create_model_and_transforms('ViT-B-32', ...)` to new model
2. Update `VectorStore` dimension if output size changes (e.g. 512 → 768)
3. **Re-index all existing items**: old embeddings are incompatible with new model
4. Clear the FAISS index and LRU cache
5. Run the full embedding pipeline on all stored images

### Upgrading rembg / U-2-Net

1. Update `requirements.txt` version pin
2. Clear `.model_cache` directory if model weights changed
3. Test with `test_bg_removal.py`

### Switching Vision LLM

1. Update `stylist_service.py`: change `model=` parameter
2. Adjust prompt if new model has different formatting requirements
3. Test with `test_cross_sell.py`

## Version History

| Date | Change | Impact |
|------|--------|--------|
| 2026-02-22 | Initial model stack deployed | Baseline |
